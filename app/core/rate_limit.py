"""
Rate limiting for /explain (Issues #27 and #30).

Three rolling windows are checked on every request:

- per client IP, per minute   (settings.explain_rate_per_minute)
- per client IP, per day      (settings.explain_rate_per_day)
- all clients, per day        (settings.explain_global_per_day)

The global cap is what actually protects the Groq budget: a per-IP limit alone
can be dodged by changing IPs, and many legitimate visitors add up.

Where the counters live
-----------------------
- **Redis** when settings.redis_url is set (Vercel injects REDIS_URL from the
  Upstash integration). Required on Vercel: the API runs on several instances
  that scale up and down, so per-process counters would each count on their
  own. The check-and-record is a single Lua script, so it is atomic: two
  simultaneous requests can't both take the last slot.
- **Process memory** otherwise (local development, Docker, tests).

If Redis can't be reached, /explain fails closed with a 503: without a working
limit it would be open to unlimited, paid AI calls.

Local block cache
-----------------
After an IP (or the global cap) is rejected, this instance remembers until when
it is blocked and rejects further attempts without asking the store. A client
hammering the endpoint then costs almost no Redis commands, which keeps the
Upstash free-plan quota safe.

Client IP
---------
request.client.host. Behind a reverse proxy uvicorn rewrites it from
X-Forwarded-For when the proxy is trusted via FORWARDED_ALLOW_IPS (set in the
Dockerfile).
"""
import logging
import math
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, Dict, List, Optional, Sequence

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import RateLimiterUnavailableError, RateLimitError

logger = logging.getLogger(__name__)

MINUTE = 60
DAY = 24 * 60 * 60
PURGE_EVERY = 1000          # checks between sweeps of expired in-memory entries
MAX_BLOCK_CACHE = 10_000    # cap on remembered blocked IPs per instance
KEY_PREFIX = "{json-intelligence}:explain"  # hash tag: all keys in one cluster slot


@dataclass(frozen=True)
class Window:
    """One limit to check: `limit` events per `seconds` under `key`. limit <= 0 disables it."""
    key: str
    limit: int
    seconds: int


# ---------------------------------------------------------------------------
# Stores
# ---------------------------------------------------------------------------

class SlidingWindowCounter:
    """Timestamps of past events per key, over a rolling window (in memory)."""

    def __init__(self, window_seconds: float):
        self.window = window_seconds
        self._events: Dict[str, Deque[float]] = {}

    def _expire(self, key: str, now: float) -> Optional[Deque[float]]:
        events = self._events.get(key)
        if events is None:
            return None
        cutoff = now - self.window
        while events and events[0] <= cutoff:
            events.popleft()
        if not events:
            del self._events[key]
            return None
        return events

    def retry_after(self, key: str, limit: int, now: float) -> Optional[float]:
        """Seconds until one more event fits under `limit`, or None if it fits now."""
        if limit <= 0:  # limit disabled
            return None
        events = self._expire(key, now)
        if events is None or len(events) < limit:
            return None
        # A new event fits once the oldest of the last `limit` events expires.
        return events[len(events) - limit] + self.window - now

    def add(self, key: str, now: float) -> None:
        self._events.setdefault(key, deque()).append(now)

    def purge(self, now: float) -> None:
        for key in list(self._events):
            self._expire(key, now)

    def clear(self) -> None:
        self._events.clear()

    def __len__(self) -> int:
        return len(self._events)


class MemoryStore:
    """Counters in process memory. Correct only for a single instance."""

    name = "memory"

    def __init__(self) -> None:
        self._counters: Dict[int, SlidingWindowCounter] = {}
        self._checks = 0

    def _counter(self, seconds: int) -> SlidingWindowCounter:
        if seconds not in self._counters:
            self._counters[seconds] = SlidingWindowCounter(seconds)
        return self._counters[seconds]

    def hit(self, windows: Sequence[Window], now: float, member: str) -> List[Optional[float]]:
        """Per-window wait (None = room). If every window has room, the event is
        recorded in all enabled windows; otherwise nothing is recorded."""
        self._checks += 1
        if self._checks % PURGE_EVERY == 0:
            for counter in self._counters.values():
                counter.purge(now)

        waits = [self._counter(w.seconds).retry_after(w.key, w.limit, now) for w in windows]
        if all(wait is None for wait in waits):
            for w in windows:
                if w.limit > 0:
                    self._counter(w.seconds).add(w.key, now)
        return waits

    def reset(self) -> None:
        for counter in self._counters.values():
            counter.clear()
        self._checks = 0

    @property
    def tracked_keys(self) -> int:
        return sum(len(counter) for counter in self._counters.values())


# Atomic check-and-record over N windows. Times in integer milliseconds: Redis
# converts Lua numbers to integers, so fractional seconds would be truncated.
# KEYS[i]               sorted set of event timestamps for window i
# ARGV[1]               now (ms)
# ARGV[2]               unique member for this event
# ARGV[1+2i], ARGV[2+2i] limit and window length (ms) of window i
# Returns, per window, the wait in ms until there is room, or -1 if there is.
SLIDING_WINDOW_LUA = """
local now = tonumber(ARGV[1])
local member = ARGV[2]
local waits = {}
local blocked = false

for i = 1, #KEYS do
  local limit = tonumber(ARGV[1 + 2 * i])
  local window = tonumber(ARGV[2 + 2 * i])
  waits[i] = -1
  if limit > 0 then
    redis.call('ZREMRANGEBYSCORE', KEYS[i], '-inf', now - window)
    local count = redis.call('ZCARD', KEYS[i])
    if count >= limit then
      local oldest = redis.call('ZRANGE', KEYS[i], count - limit, count - limit, 'WITHSCORES')
      waits[i] = tonumber(oldest[2]) + window - now
      blocked = true
    end
  end
end

if not blocked then
  for i = 1, #KEYS do
    local limit = tonumber(ARGV[1 + 2 * i])
    local window = tonumber(ARGV[2 + 2 * i])
    if limit > 0 then
      redis.call('ZADD', KEYS[i], now, member)
      redis.call('PEXPIRE', KEYS[i], window)
    end
  end
end

return waits
"""


class RedisStore:
    """Counters in Redis, shared by every instance. One round trip per check."""

    name = "redis"

    def __init__(self, client) -> None:
        self._client = client
        self._script = client.register_script(SLIDING_WINDOW_LUA)

    def hit(self, windows: Sequence[Window], now: float, member: str) -> List[Optional[float]]:
        now_ms = int(now * 1000)
        args: list = [now_ms, member]
        for w in windows:
            args += [w.limit, w.seconds * 1000]
        raw = self._script(keys=[f"{KEY_PREFIX}:{w.key}" for w in windows], args=args)
        return [None if int(ms) < 0 else int(ms) / 1000 for ms in raw]

    def reset(self) -> None:
        for key in self._client.scan_iter(match=f"{KEY_PREFIX}:*"):
            self._client.delete(key)

    @property
    def tracked_keys(self) -> int:
        return sum(1 for _ in self._client.scan_iter(match=f"{KEY_PREFIX}:*"))


def make_redis_client(url: str, timeout: float = 2.0):
    """Redis client tuned to fail fast.

    redis-py retries failed connections several times by default, which would
    leave /explain hanging for seconds during a Redis outage before the 503.
    One quick retry covers a dropped connection without that wait.
    """
    import redis  # imported here so runs without Redis don't need to load it
    from redis.backoff import ExponentialBackoff
    from redis.retry import Retry

    return redis.Redis.from_url(
        url,
        socket_timeout=timeout,
        socket_connect_timeout=timeout,
        health_check_interval=30,
        retry=Retry(ExponentialBackoff(cap=0.1, base=0.02), retries=1),
    )


def build_store():
    """Redis when REDIS_URL is configured, memory otherwise."""
    if settings.redis_configured:
        return RedisStore(make_redis_client(settings.redis_url.get_secret_value()))
    return MemoryStore()


# ---------------------------------------------------------------------------
# Limiter
# ---------------------------------------------------------------------------

class ExplainRateLimiter:
    """Applies the per-IP and global limits. Limits are read from settings on
    every call, so they can be changed (or patched in tests) at runtime."""

    GLOBAL_KEY = "global:day"

    def __init__(self, store=None, clock: Callable[[], float] = time.time):
        # Wall-clock time: with Redis, several instances must agree on "now".
        self.store = store if store is not None else MemoryStore()
        self._clock = clock
        self._lock = threading.Lock()
        self._blocked_ips: Dict[str, float] = {}  # ip -> blocked until (local cache)
        self._global_blocked_until = 0.0

    def check(self, client_ip: str) -> None:
        """Record one request from `client_ip`, or raise.

        - RateLimitError (429) when a limit is reached. A rejected request is
          not recorded: it doesn't eat into the quota.
        - RateLimiterUnavailableError (503) when the store can't be reached.
        """
        now = self._clock()
        with self._lock:
            self._check_local_cache(client_ip, now)

            windows = [
                Window(self.GLOBAL_KEY, settings.explain_global_per_day, DAY),
                Window(f"ip:{client_ip}:minute", settings.explain_rate_per_minute, MINUTE),
                Window(f"ip:{client_ip}:day", settings.explain_rate_per_day, DAY),
            ]
            try:
                global_wait, minute_wait, day_wait = self.store.hit(windows, now, uuid.uuid4().hex)
            except Exception as exc:
                logger.error(
                    f"Rate-limit store ({self.store.name}) unavailable: "
                    f"{type(exc).__name__}: {exc}"
                )
                raise RateLimiterUnavailableError() from exc

            if global_wait is not None:
                self._global_blocked_until = now + global_wait
                logger.warning("Global daily /explain limit reached")
                raise self._global_error(global_wait)

            ip_waits = [w for w in (minute_wait, day_wait) if w is not None]
            if ip_waits:
                wait = max(ip_waits)
                self._remember_block(client_ip, now + wait, now)
                logger.warning(f"/explain rate limit reached for {client_ip}")
                raise self._ip_error(wait)

    # -- local block cache ----------------------------------------------------

    def _check_local_cache(self, client_ip: str, now: float) -> None:
        if self._global_blocked_until > now:
            raise self._global_error(self._global_blocked_until - now)
        until = self._blocked_ips.get(client_ip)
        if until is not None:
            if until > now:
                raise self._ip_error(until - now)
            del self._blocked_ips[client_ip]

    def _remember_block(self, client_ip: str, until: float, now: float) -> None:
        if len(self._blocked_ips) >= MAX_BLOCK_CACHE:
            self._blocked_ips = {ip: t for ip, t in self._blocked_ips.items() if t > now}
            if len(self._blocked_ips) >= MAX_BLOCK_CACHE:
                return  # still full of live blocks: rely on the store
        self._blocked_ips[client_ip] = until

    # -- errors ---------------------------------------------------------------

    @staticmethod
    def _global_error(wait: float) -> RateLimitError:
        return RateLimitError(
            "Se alcanzó el límite diario de la demo para /explain. "
            "Intenta de nuevo más tarde.",
            retry_after=wait,
        )

    @staticmethod
    def _ip_error(wait: float) -> RateLimitError:
        seconds = max(1, math.ceil(wait))
        return RateLimitError(
            f"Demasiadas solicitudes a /explain. Intenta de nuevo en {seconds} segundos.",
            retry_after=seconds,
        )

    # -- maintenance ----------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self.store.reset()
            self._blocked_ips.clear()
            self._global_blocked_until = 0.0

    @property
    def tracked_keys(self) -> int:
        """Keys currently held by the store (for tests and diagnostics)."""
        return self.store.tracked_keys

    @property
    def blocked_ips_cached(self) -> int:
        return len(self._blocked_ips)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


explain_rate_limiter = ExplainRateLimiter(store=build_store())

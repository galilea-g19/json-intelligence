"""
In-memory rate limiting for /explain (Issue #27).

Three rolling windows are checked on every request:

- per client IP, per minute   (settings.explain_rate_per_minute)
- per client IP, per day      (settings.explain_rate_per_day)
- all clients, per day        (settings.explain_global_per_day)

The global cap is what actually protects the Groq budget: a per-IP limit alone
can be dodged by changing IPs, and many legitimate visitors add up.

Counters live in process memory, which is correct for a single instance (the
demo). With several instances each would count separately; the fix then is to
move the counters to a shared store such as Redis.

The client IP is request.client.host. Behind a reverse proxy (Render, Fly.io,
Railway) uvicorn rewrites it from X-Forwarded-For, as long as the proxy is
trusted via FORWARDED_ALLOW_IPS (set in the Dockerfile).
"""
import logging
import math
import threading
import time
from collections import deque
from typing import Callable, Deque, Dict, Optional

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import RateLimitError

logger = logging.getLogger(__name__)

MINUTE = 60
DAY = 24 * 60 * 60
PURGE_EVERY = 1000  # checks between sweeps of expired keys (bounds memory)


class SlidingWindowCounter:
    """Timestamps of past events per key, over a rolling window."""

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


class ExplainRateLimiter:
    """Applies the per-IP and global limits. Limits are read from settings on
    every call, so they can be changed (or patched in tests) at runtime."""

    GLOBAL_KEY = "*"

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._per_minute = SlidingWindowCounter(MINUTE)
        self._per_day = SlidingWindowCounter(DAY)
        self._global = SlidingWindowCounter(DAY)
        self._checks = 0

    def check(self, client_ip: str) -> None:
        """Record one request from `client_ip`, or raise RateLimitError.

        A rejected request is not recorded: it doesn't eat into the quota.
        """
        now = self._clock()
        with self._lock:
            self._maybe_purge(now)

            wait = self._global.retry_after(self.GLOBAL_KEY, settings.explain_global_per_day, now)
            if wait is not None:
                logger.warning("Global daily /explain limit reached")
                raise RateLimitError(
                    "Se alcanzó el límite diario de la demo para /explain. "
                    "Intenta de nuevo más tarde.",
                    retry_after=wait,
                )

            waits = [
                w
                for w in (
                    self._per_minute.retry_after(client_ip, settings.explain_rate_per_minute, now),
                    self._per_day.retry_after(client_ip, settings.explain_rate_per_day, now),
                )
                if w is not None
            ]
            if waits:
                seconds = max(1, math.ceil(max(waits)))
                logger.warning(f"/explain rate limit reached for {client_ip}")
                raise RateLimitError(
                    f"Demasiadas solicitudes a /explain. Intenta de nuevo en {seconds} segundos.",
                    retry_after=seconds,
                )

            self._per_minute.add(client_ip, now)
            self._per_day.add(client_ip, now)
            self._global.add(self.GLOBAL_KEY, now)

    def _maybe_purge(self, now: float) -> None:
        self._checks += 1
        if self._checks % PURGE_EVERY == 0:
            for counter in (self._per_minute, self._per_day, self._global):
                counter.purge(now)

    def reset(self) -> None:
        with self._lock:
            for counter in (self._per_minute, self._per_day, self._global):
                counter.clear()
            self._checks = 0

    @property
    def tracked_keys(self) -> int:
        """Keys currently held in memory (for tests and diagnostics)."""
        return len(self._per_minute) + len(self._per_day) + len(self._global)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


explain_rate_limiter = ExplainRateLimiter()

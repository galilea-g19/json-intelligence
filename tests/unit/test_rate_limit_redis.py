"""Tests del almacén Redis, la caché local de bloqueos y el modo fail-closed (issue #30).

Redis se simula con fakeredis (incluye el intérprete Lua): sin red y sin gastar
comandos de Upstash.
"""
import time

import fakeredis
import pytest
from pydantic import SecretStr

import app.core.rate_limit as rate_limit
from app.core.config import settings
from app.core.exceptions import RateLimiterUnavailableError, RateLimitError
from app.core.rate_limit import (
    DAY,
    KEY_PREFIX,
    MINUTE,
    ExplainRateLimiter,
    MemoryStore,
    RedisStore,
    build_store,
    make_redis_client,
)


class FakeClock:
    def __init__(self, start: float = 1_800_000_000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class CountingStore:
    """Envuelve un almacén y cuenta cuántas veces se le consulta."""

    def __init__(self, inner):
        self.inner = inner
        self.name = inner.name
        self.calls = 0

    def hit(self, windows, now, member):
        self.calls += 1
        return self.inner.hit(windows, now, member)

    def reset(self):
        self.inner.reset()

    @property
    def tracked_keys(self):
        return self.inner.tracked_keys


class BrokenStore:
    name = "redis"

    def hit(self, windows, now, member):
        raise ConnectionError("redis down")

    def reset(self):
        pass


@pytest.fixture(autouse=True)
def project_limits(monkeypatch):
    monkeypatch.setattr(settings, "explain_rate_per_minute", 4)
    monkeypatch.setattr(settings, "explain_rate_per_day", 40)
    monkeypatch.setattr(settings, "explain_global_per_day", 500)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def server():
    return fakeredis.FakeServer()


def instance(server, clock):
    """Una 'instancia' de la API: su propio cliente y su propia caché local,
    pero el mismo servidor Redis que las demás."""
    return ExplainRateLimiter(store=RedisStore(fakeredis.FakeRedis(server=server)), clock=clock)


# --- Varias instancias: el motivo del issue #30 -------------------------------

def test_instances_share_the_per_ip_limit(server, clock):
    a, b = instance(server, clock), instance(server, clock)

    a.check("1.1.1.1")
    b.check("1.1.1.1")
    a.check("1.1.1.1")
    b.check("1.1.1.1")  # 4 en total, repartidas entre dos instancias

    with pytest.raises(RateLimitError):
        a.check("1.1.1.1")
    with pytest.raises(RateLimitError):
        b.check("1.1.1.1")


def test_memory_store_would_not_share_the_limit(clock):
    # Por contraste: con memoria, cada instancia cuenta por su cuenta (8 > 4)
    a = ExplainRateLimiter(store=MemoryStore(), clock=clock)
    b = ExplainRateLimiter(store=MemoryStore(), clock=clock)

    for _ in range(4):
        a.check("1.1.1.1")
        b.check("1.1.1.1")


def test_instances_share_the_global_cap(server, clock, monkeypatch):
    monkeypatch.setattr(settings, "explain_global_per_day", 3)
    a, b, c = instance(server, clock), instance(server, clock), instance(server, clock)

    a.check("1.1.1.1")
    b.check("2.2.2.2")
    c.check("3.3.3.3")

    with pytest.raises(RateLimitError, match="límite diario de la demo"):
        a.check("4.4.4.4")


def test_counters_survive_a_new_instance(server, clock):
    # En Vercel las instancias se apagan y se crean: los contadores siguen en Redis
    instance(server, clock).check("1.1.1.1")
    for _ in range(3):
        instance(server, clock).check("1.1.1.1")

    with pytest.raises(RateLimitError):
        instance(server, clock).check("1.1.1.1")


# --- Detalles de Redis --------------------------------------------------------

def test_redis_keys_use_prefix_and_expire(clock):
    client = fakeredis.FakeRedis()
    limiter = ExplainRateLimiter(store=RedisStore(client), clock=clock)

    limiter.check("1.1.1.1")

    keys = sorted(k.decode() for k in client.keys("*"))
    assert keys == sorted([
        f"{KEY_PREFIX}:global:day",
        f"{KEY_PREFIX}:ip:1.1.1.1:minute",
        f"{KEY_PREFIX}:ip:1.1.1.1:day",
    ])
    assert 0 < client.pttl(f"{KEY_PREFIX}:ip:1.1.1.1:minute") <= MINUTE * 1000
    assert MINUTE * 1000 < client.pttl(f"{KEY_PREFIX}:global:day") <= DAY * 1000


def test_rejected_requests_are_not_written(clock):
    client = fakeredis.FakeRedis()
    limiter = ExplainRateLimiter(store=RedisStore(client), clock=clock)
    for _ in range(4):
        limiter.check("1.1.1.1")

    with pytest.raises(RateLimitError):
        limiter.check("1.1.1.1")

    assert client.zcard(f"{KEY_PREFIX}:ip:1.1.1.1:minute") == 4
    assert client.zcard(f"{KEY_PREFIX}:global:day") == 4


def test_simultaneous_requests_get_distinct_entries(clock):
    # Mismo milisegundo, misma IP: el miembro único evita que se pisen en el sorted set
    client = fakeredis.FakeRedis()
    limiter = ExplainRateLimiter(store=RedisStore(client), clock=clock)

    limiter.check("1.1.1.1")
    limiter.check("1.1.1.1")

    assert client.zcard(f"{KEY_PREFIX}:ip:1.1.1.1:minute") == 2


def test_disabled_limits_are_not_written(clock, monkeypatch):
    monkeypatch.setattr(settings, "explain_rate_per_day", 0)
    client = fakeredis.FakeRedis()

    ExplainRateLimiter(store=RedisStore(client), clock=clock).check("1.1.1.1")

    assert not client.exists(f"{KEY_PREFIX}:ip:1.1.1.1:day")


def test_reset_only_deletes_rate_limit_keys(clock):
    client = fakeredis.FakeRedis()
    client.set("otra-app:clave", "1")
    limiter = ExplainRateLimiter(store=RedisStore(client), clock=clock)
    limiter.check("1.1.1.1")

    limiter.reset()

    assert limiter.tracked_keys == 0
    assert client.get("otra-app:clave") == b"1"


# --- Fail-closed ----------------------------------------------------------------

def test_store_failure_raises_503(clock, caplog):
    limiter = ExplainRateLimiter(store=BrokenStore(), clock=clock)

    with pytest.raises(RateLimiterUnavailableError) as excinfo:
        limiter.check("1.1.1.1")

    assert excinfo.value.status_code == 503
    assert "redis down" not in excinfo.value.message  # el detalle solo va al log
    assert any("Rate-limit store (redis) unavailable: ConnectionError" in m for m in caplog.messages)


def test_real_redis_client_failure_raises_503_quickly(clock):
    # Cliente de verdad, con la misma configuración que producción (solo un
    # timeout más corto), apuntando a un puerto sin servidor.
    client = make_redis_client("redis://127.0.0.1:1/0", timeout=0.2)
    limiter = ExplainRateLimiter(store=RedisStore(client), clock=clock)

    start = time.perf_counter()
    with pytest.raises(RateLimiterUnavailableError):
        limiter.check("1.1.1.1")

    # 1 reintento como máximo: sin él, redis-py reintentaría varias veces y
    # /explain quedaría colgado segundos antes de responder 503.
    assert time.perf_counter() - start < 3


def test_client_retries_only_once():
    client = make_redis_client("rediss://default:x@example.upstash.io:6379")

    retry = client.get_retry()
    assert retry.get_retries() == 1


# --- Caché local de bloqueos ---------------------------------------------------

def test_blocked_ip_is_rejected_without_asking_the_store(clock):
    store = CountingStore(RedisStore(fakeredis.FakeRedis()))
    limiter = ExplainRateLimiter(store=store, clock=clock)
    for _ in range(4):
        limiter.check("1.1.1.1")
    with pytest.raises(RateLimitError):
        limiter.check("1.1.1.1")
    calls_after_first_rejection = store.calls

    for _ in range(50):  # un cliente insistiendo
        with pytest.raises(RateLimitError) as excinfo:
            limiter.check("1.1.1.1")

    assert store.calls == calls_after_first_rejection  # 0 consultas extra a Redis
    assert excinfo.value.retry_after == 60


def test_cached_block_counts_down_and_expires(clock):
    store = CountingStore(MemoryStore())
    limiter = ExplainRateLimiter(store=store, clock=clock)
    for _ in range(4):
        limiter.check("1.1.1.1")
    with pytest.raises(RateLimitError):
        limiter.check("1.1.1.1")

    clock.advance(45)
    with pytest.raises(RateLimitError) as excinfo:
        limiter.check("1.1.1.1")
    assert excinfo.value.retry_after == 15

    clock.advance(15)
    limiter.check("1.1.1.1")  # bloqueo vencido: vuelve a consultar al almacén
    assert limiter.blocked_ips_cached == 0


def test_cached_block_does_not_affect_other_ips(clock):
    limiter = ExplainRateLimiter(store=MemoryStore(), clock=clock)
    for _ in range(4):
        limiter.check("1.1.1.1")
    with pytest.raises(RateLimitError):
        limiter.check("1.1.1.1")

    limiter.check("2.2.2.2")


def test_global_block_is_cached(clock, monkeypatch):
    monkeypatch.setattr(settings, "explain_global_per_day", 1)
    store = CountingStore(MemoryStore())
    limiter = ExplainRateLimiter(store=store, clock=clock)
    limiter.check("1.1.1.1")
    with pytest.raises(RateLimitError):
        limiter.check("2.2.2.2")
    calls = store.calls

    with pytest.raises(RateLimitError, match="límite diario de la demo"):
        limiter.check("3.3.3.3")

    assert store.calls == calls


def test_block_cache_is_bounded(clock, monkeypatch):
    monkeypatch.setattr(rate_limit, "MAX_BLOCK_CACHE", 2)
    monkeypatch.setattr(settings, "explain_rate_per_minute", 1)
    limiter = ExplainRateLimiter(store=MemoryStore(), clock=clock)

    for ip in ("1.1.1.1", "2.2.2.2", "3.3.3.3"):
        limiter.check(ip)
        with pytest.raises(RateLimitError):
            limiter.check(ip)

    assert limiter.blocked_ips_cached == 2  # lleno de bloqueos vigentes: no crece
    with pytest.raises(RateLimitError):
        limiter.check("3.3.3.3")  # sin caché, el almacén sigue rechazando

    clock.advance(MINUTE)
    limiter.check("4.4.4.4")
    with pytest.raises(RateLimitError):
        limiter.check("4.4.4.4")  # caché llena de bloqueos vencidos: se limpia y entra

    assert limiter.blocked_ips_cached == 1


# --- Selección del almacén ------------------------------------------------------

@pytest.mark.parametrize("url", [None, "", "   "])
def test_memory_store_without_redis_url(monkeypatch, url):
    monkeypatch.setattr(settings, "redis_url", SecretStr(url) if url is not None else None)

    assert isinstance(build_store(), MemoryStore)


def test_redis_store_with_redis_url(monkeypatch):
    # from_url no se conecta al crear el cliente: no hace falta un servidor
    monkeypatch.setattr(settings, "redis_url", SecretStr("rediss://default:secreto@example.upstash.io:6379"))

    store = build_store()

    assert isinstance(store, RedisStore)


def test_test_suite_never_uses_real_redis():
    from app.core.rate_limit import explain_rate_limiter

    assert explain_rate_limiter.store.name == "memory"

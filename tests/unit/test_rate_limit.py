"""Tests unitarios de app.core.rate_limit (issues #27 y #30).

Reloj simulado: sin esperas reales. Cada test de comportamiento corre contra
los DOS almacenes (memoria y Redis simulado con fakeredis): deben comportarse
exactamente igual.
"""
from types import SimpleNamespace

import fakeredis
import pytest

import app.core.rate_limit as rate_limit
from app.core.config import settings
from app.core.exceptions import RateLimitError
from app.core.rate_limit import (
    DAY,
    MINUTE,
    ExplainRateLimiter,
    MemoryStore,
    RedisStore,
    SlidingWindowCounter,
    client_ip,
)


class FakeClock:
    def __init__(self, start: float = 1_000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture(params=["memory", "redis"])
def store(request):
    if request.param == "memory":
        return MemoryStore()
    return RedisStore(fakeredis.FakeRedis())


@pytest.fixture
def limiter(clock, store, monkeypatch):
    # Los valores decididos para el proyecto, explícitos para no depender del .env
    monkeypatch.setattr(settings, "explain_rate_per_minute", 4)
    monkeypatch.setattr(settings, "explain_rate_per_day", 40)
    monkeypatch.setattr(settings, "explain_global_per_day", 500)
    return ExplainRateLimiter(store=store, clock=clock)


def hit(limiter, ip="1.1.1.1", times=1):
    for _ in range(times):
        limiter.check(ip)


# --- Límite por minuto -------------------------------------------------------

def test_allows_four_per_minute(limiter):
    hit(limiter, times=4)


def test_fifth_request_in_a_minute_is_rejected(limiter):
    hit(limiter, times=4)

    with pytest.raises(RateLimitError) as excinfo:
        limiter.check("1.1.1.1")

    assert excinfo.value.status_code == 429
    assert excinfo.value.retry_after == 60
    assert "Demasiadas solicitudes" in excinfo.value.message
    assert "60 segundos" in excinfo.value.message


def test_window_is_rolling_not_fixed(limiter, clock):
    hit(limiter)            # t=0
    clock.advance(30)
    hit(limiter, times=3)   # t=30

    with pytest.raises(RateLimitError) as excinfo:
        limiter.check("1.1.1.1")
    assert excinfo.value.retry_after == 30  # libera cuando expira la de t=0

    clock.advance(30)       # t=60: expira la de t=0, las de t=30 siguen
    hit(limiter)
    with pytest.raises(RateLimitError):
        limiter.check("1.1.1.1")


def test_quota_comes_back_after_a_minute(limiter, clock):
    hit(limiter, times=4)
    clock.advance(MINUTE)

    hit(limiter, times=4)


# --- Límite diario por IP ----------------------------------------------------

def test_daily_limit_per_ip(limiter, monkeypatch):
    monkeypatch.setattr(settings, "explain_rate_per_minute", 0)  # aislar el diario
    hit(limiter, times=40)

    with pytest.raises(RateLimitError) as excinfo:
        limiter.check("1.1.1.1")

    assert excinfo.value.retry_after == DAY


def test_daily_limit_with_requests_spread_over_the_day(limiter, clock):
    for _ in range(40):
        limiter.check("1.1.1.1")
        clock.advance(MINUTE)  # nunca toca el límite por minuto

    with pytest.raises(RateLimitError) as excinfo:
        limiter.check("1.1.1.1")

    # La primera petición fue hace 40 minutos: libera en 24 h - 40 min
    assert excinfo.value.retry_after == DAY - 40 * MINUTE


def test_retry_after_is_the_longest_wait(limiter, clock, monkeypatch):
    monkeypatch.setattr(settings, "explain_rate_per_day", 4)
    hit(limiter, times=4)  # agota a la vez el minuto y el día

    with pytest.raises(RateLimitError) as excinfo:
        limiter.check("1.1.1.1")

    assert excinfo.value.retry_after == DAY


# --- Por IP y global ---------------------------------------------------------

def test_limits_are_per_ip(limiter):
    hit(limiter, "1.1.1.1", times=4)

    hit(limiter, "2.2.2.2", times=4)  # otra IP, cuota propia

    with pytest.raises(RateLimitError):
        limiter.check("1.1.1.1")


def test_global_daily_cap_applies_across_ips(limiter, monkeypatch):
    monkeypatch.setattr(settings, "explain_global_per_day", 3)

    for ip in ("1.1.1.1", "2.2.2.2", "3.3.3.3"):
        limiter.check(ip)

    with pytest.raises(RateLimitError) as excinfo:
        limiter.check("4.4.4.4")  # IP nueva, pero el tope global ya se alcanzó

    assert "límite diario de la demo" in excinfo.value.message
    assert excinfo.value.retry_after == DAY


def test_global_cap_comes_back_after_a_day(limiter, clock, monkeypatch):
    monkeypatch.setattr(settings, "explain_global_per_day", 2)
    hit(limiter, "1.1.1.1")
    hit(limiter, "2.2.2.2")

    clock.advance(DAY)

    hit(limiter, "3.3.3.3")


# --- Comportamiento ----------------------------------------------------------

def test_rejected_requests_do_not_consume_quota(limiter, clock):
    hit(limiter, times=4)
    for _ in range(10):
        with pytest.raises(RateLimitError):
            limiter.check("1.1.1.1")

    clock.advance(MINUTE)

    hit(limiter, times=4)  # si los rechazos contaran, esto fallaría


def test_rejection_by_ip_limit_does_not_consume_global_quota(limiter, monkeypatch):
    monkeypatch.setattr(settings, "explain_global_per_day", 5)
    hit(limiter, "1.1.1.1", times=4)
    for _ in range(10):
        with pytest.raises(RateLimitError):
            limiter.check("1.1.1.1")

    limiter.check("2.2.2.2")  # 5.ª petición aceptada en total


@pytest.mark.parametrize("setting", ["explain_rate_per_minute", "explain_rate_per_day", "explain_global_per_day"])
def test_zero_disables_a_limit(limiter, monkeypatch, setting):
    monkeypatch.setattr(settings, "explain_rate_per_minute", 0)
    monkeypatch.setattr(settings, "explain_rate_per_day", 0)
    monkeypatch.setattr(settings, "explain_global_per_day", 0)
    monkeypatch.setattr(settings, setting, 0)

    hit(limiter, times=200)


def test_limits_are_read_at_runtime(limiter, monkeypatch):
    hit(limiter, times=4)
    monkeypatch.setattr(settings, "explain_rate_per_minute", 10)

    hit(limiter, times=6)


def test_expired_keys_are_purged(limiter, clock, monkeypatch):
    if limiter.store.name != "memory":
        pytest.skip("Redis caduca las claves con PEXPIRE (ver test_redis_keys_use_prefix_and_expire)")
    monkeypatch.setattr(rate_limit, "PURGE_EVERY", 5)
    for i in range(4):
        limiter.check(f"10.0.0.{i}")
    assert limiter.tracked_keys > 0

    clock.advance(DAY + 1)
    limiter.check("10.0.0.99")  # 5.º check: dispara la limpieza

    # Solo queda la IP nueva (minuto + día) y la clave global
    assert limiter.tracked_keys == 3


def test_reset_clears_everything(limiter):
    hit(limiter, times=4)

    limiter.reset()

    assert limiter.tracked_keys == 0
    hit(limiter, times=4)


# --- Piezas sueltas ----------------------------------------------------------

def test_counter_reports_none_when_there_is_room():
    counter = SlidingWindowCounter(60)
    counter.add("k", 0)

    assert counter.retry_after("k", 2, now=1) is None
    assert counter.retry_after("otra", 1, now=1) is None


@pytest.mark.parametrize("raw, expected", [(0.2, 1), (0, 1), (59.1, 60), (60, 60)])
def test_retry_after_is_rounded_up_to_whole_seconds(raw, expected):
    error = RateLimitError("x", retry_after=raw)

    assert error.retry_after == expected
    assert error.headers == {"Retry-After": str(expected)}


def test_client_ip_falls_back_when_unknown():
    assert client_ip(SimpleNamespace(client=None)) == "unknown"
    assert client_ip(SimpleNamespace(client=SimpleNamespace(host="9.9.9.9"))) == "9.9.9.9"

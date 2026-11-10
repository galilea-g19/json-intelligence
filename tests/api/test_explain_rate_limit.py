"""Rate limiting de POST /api/v1/json/explain a través de la API (issue #27)."""
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rate_limit import explain_rate_limiter
from app.main import app

URL = "/api/v1/json/explain"
BODY = {"data": {"a": 1}}


@pytest.fixture(autouse=True)
def project_limits(monkeypatch):
    monkeypatch.setattr(settings, "explain_rate_per_minute", 4)
    monkeypatch.setattr(settings, "explain_rate_per_day", 40)
    monkeypatch.setattr(settings, "explain_global_per_day", 500)


def client_from(ip: str) -> TestClient:
    return TestClient(app, raise_server_exceptions=False, client=(ip, 50000))


def test_fifth_call_in_a_minute_is_429(client, fake_groq, valid_explanation):
    create = fake_groq(valid_explanation)

    for _ in range(4):
        assert client.post(URL, json=BODY).status_code == 200

    r = client.post(URL, json=BODY)

    assert r.status_code == 429
    assert r.headers["retry-after"] == "60"
    body = r.json()
    assert body["status_code"] == 429
    assert body["path"] == URL
    assert "Demasiadas solicitudes" in body["error"]
    assert create.call_count == 4  # la 5.ª nunca llegó a Groq


def test_failed_ai_calls_still_count(client, fake_groq):
    # Cada intento válido cuenta, aunque Groq falle: protege igual el presupuesto
    fake_groq(raises=RuntimeError("down"))

    for _ in range(4):
        assert client.post(URL, json=BODY).status_code == 502

    assert client.post(URL, json=BODY).status_code == 429


def test_invalid_requests_do_not_use_quota(client, fake_groq, valid_explanation):
    fake_groq(valid_explanation)

    for _ in range(10):
        assert client.post(URL, json={"data": "no soy objeto"}).status_code == 422

    for _ in range(4):
        assert client.post(URL, json=BODY).status_code == 200


def test_each_client_ip_has_its_own_quota(fake_groq, valid_explanation):
    fake_groq(valid_explanation)
    alice, bob = client_from("203.0.113.1"), client_from("203.0.113.2")

    for _ in range(4):
        alice.post(URL, json=BODY)

    assert alice.post(URL, json=BODY).status_code == 429
    assert bob.post(URL, json=BODY).status_code == 200


def test_global_cap_blocks_new_ips(fake_groq, valid_explanation, monkeypatch):
    monkeypatch.setattr(settings, "explain_global_per_day", 2)
    fake_groq(valid_explanation)

    assert client_from("198.51.100.1").post(URL, json=BODY).status_code == 200
    assert client_from("198.51.100.2").post(URL, json=BODY).status_code == 200

    r = client_from("198.51.100.3").post(URL, json=BODY)

    assert r.status_code == 429
    assert "límite diario de la demo" in r.json()["error"]


@pytest.mark.parametrize("route", ["analyze", "schema"])
def test_free_endpoints_are_not_limited(client, route):
    for _ in range(20):
        assert client.post(f"/api/v1/json/{route}", json=BODY).status_code == 200


def test_openapi_documents_429_and_503(client):
    responses = client.get("/openapi.json").json()["paths"][URL]["post"]["responses"]

    assert {"429", "503"} <= set(responses)


def test_unreachable_store_is_503_and_never_calls_ai(client, fake_groq, valid_explanation, monkeypatch):
    class BrokenStore:
        name = "redis"

        def hit(self, *args):
            raise ConnectionError("redis down")

        def reset(self):
            pass

    monkeypatch.setattr(explain_rate_limiter, "store", BrokenStore())
    create = fake_groq(valid_explanation)

    r = client.post(URL, json=BODY)

    assert r.status_code == 503
    body = r.json()
    assert body["status_code"] == 503
    assert "no está disponible temporalmente" in body["error"]
    assert "redis down" not in r.text
    create.assert_not_called()

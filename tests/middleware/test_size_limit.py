"""BodySizeLimitMiddleware y RequestLoggingMiddleware (casos MW-01..MW-07)."""
import json
import logging

import pytest

import app.routes.json_routes as routes
from app.core.config import settings

URL = "/api/v1/json/analyze"
LIMIT = 100


@pytest.fixture
def small_limit(monkeypatch):
    # MW-05: el límite se lee de settings en cada request, así que se puede bajar.
    monkeypatch.setattr(settings, "max_body_bytes", LIMIT)
    return LIMIT


def body_of_size(size: int) -> bytes:
    """Body JSON válido de exactamente `size` bytes."""
    empty = json.dumps({"data": {"a": ""}}).encode()
    body = json.dumps({"data": {"a": "x" * (size - len(empty))}}).encode()
    assert len(body) == size
    return body


def post_raw(client, body, **kwargs):
    return client.post(URL, content=body, headers={"content-type": "application/json"}, **kwargs)


# MW-01
def test_body_over_default_limit_is_413(client):
    r = client.post(URL, json={"data": {"a": "x" * (settings.max_body_bytes + 1)}})

    assert r.status_code == 413
    body = r.json()
    assert body["status_code"] == 413
    assert body["path"] == URL
    assert str(settings.max_body_bytes) in body["error"]


# MW-02
def test_chunked_body_without_content_length_is_413(client, small_limit):
    def chunks():
        yield body_of_size(LIMIT + 50)

    r = post_raw(client, chunks())

    assert "content-length" not in r.request.headers
    assert r.status_code == 413


# MW-03
def test_body_exactly_at_limit_passes(client, small_limit):
    assert post_raw(client, body_of_size(LIMIT)).status_code == 200


def test_body_one_byte_over_limit_is_413(client, small_limit):
    assert post_raw(client, body_of_size(LIMIT + 1)).status_code == 413


# MW-04: después de leerlo, el middleware se lo devuelve intacto al endpoint.
def test_body_reaches_endpoint_intact(client):
    r = client.post(URL, json={"data": {"ciudad": "Guadalajara", "cp": 44100}})

    assert r.status_code == 200
    assert r.json()["types"] == {"ciudad": "string", "cp": "integer"}


def test_get_without_body_is_not_blocked(client, small_limit):
    assert client.get("/").status_code == 200


# MW-06
def test_request_log_includes_rejected_requests(client, small_limit, caplog):
    with caplog.at_level(logging.INFO, logger="app.request"):
        post_raw(client, body_of_size(LIMIT + 1))

    assert any(f"POST {URL} -> 413" in m for m in caplog.messages)


def test_request_log_format(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/")

    assert any(m.startswith("GET / -> 200 (") and m.endswith(" ms)") for m in caplog.messages)


# MW-07: un 500 no controlado también queda en el log de requests
def test_request_log_includes_500(client, monkeypatch, caplog):
    def boom(_):
        raise RuntimeError("x")

    # /explain no envuelve el servicio en try/except, así que el error llega como 500
    monkeypatch.setattr(routes, "explain_json", boom)

    with caplog.at_level(logging.INFO, logger="app.request"):
        r = client.post("/api/v1/json/explain", json={"data": {"a": 1}})

    assert r.status_code == 500

    records = [r for r in caplog.records if "-> 500" in r.getMessage()]
    assert len(records) == 1
    assert records[0].levelno == logging.ERROR
    assert records[0].getMessage().startswith("POST /api/v1/json/explain -> 500 (")
    assert records[0].getMessage().endswith("[RuntimeError]")

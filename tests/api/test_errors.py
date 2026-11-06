"""Formato único de error y handlers globales (casos ER-01..ER-03, ER-05)."""
import pytest

import app.routes.json_routes as routes

ENVELOPE = {"error", "status_code", "path"}


# ER-01
@pytest.mark.parametrize(
    "method, url, kwargs, expected",
    [
        ("get", "/no-existe", {}, 404),
        ("get", "/api/v1/json/analyze", {}, 405),
        ("post", "/api/v1/json/explain", {"json": {"data": {"a": "x" * 6000}}}, 413),
        ("post", "/api/v1/json/explain", {"json": {"data": {"a": 1}}}, 502),  # sin API key
    ],
)
def test_error_envelope_is_uniform(client, method, url, kwargs, expected):
    r = getattr(client, method)(url, **kwargs)

    assert r.status_code == expected
    body = r.json()
    assert set(body) == ENVELOPE
    assert body["status_code"] == expected
    assert body["path"] == url


# ER-02
def test_validation_error_shape(client):
    r = client.post("/api/v1/json/analyze", json={"data": "no soy objeto"})

    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "Invalid request"
    assert isinstance(body["details"], list)
    assert body["details"][0]["loc"] == ["body", "data"]


# ER-03
def test_unhandled_exception_is_generic_500(client, monkeypatch):
    def boom(_):
        raise RuntimeError("detalle interno secreto")

    monkeypatch.setattr(routes, "explain_json", boom)

    r = client.post("/api/v1/json/explain", json={"data": {"a": 1}})

    assert r.status_code == 500
    body = r.json()
    assert body["error"] == "Internal server error"
    assert "detalle interno secreto" not in r.text
    assert "Traceback" not in r.text


# ER-05: el README promete {error, status_code, path} para TODO error.
def test_422_includes_status_code(client):
    r = client.post("/api/v1/json/analyze", json={})

    body = r.json()
    assert body["status_code"] == 422
    assert ENVELOPE <= set(body)  # 422 agrega "details"


def test_500_includes_status_code(client, monkeypatch):
    def boom(_):
        raise RuntimeError("x")

    monkeypatch.setattr(routes, "explain_json", boom)

    r = client.post("/api/v1/json/explain", json={"data": {"a": 1}})

    body = r.json()
    assert body["status_code"] == 500
    assert ENVELOPE <= set(body)  # 500 agrega "message"

"""Rutas meta: /, /test-env, /ui, /openapi.json (casos EP-11..EP-14)."""
from pydantic import SecretStr

from app.core.config import settings


# EP-11
def test_root_health_check(client):
    r = client.get("/")

    assert r.status_code == 200
    assert r.json()["ui"] == "/ui"
    assert r.json()["docs"] == "/docs"


# EP-12
def test_ui_redirects_to_trailing_slash(client):
    r = client.get("/ui", follow_redirects=False)

    assert r.status_code == 307
    assert r.headers["location"] == "/ui/"


def test_ui_serves_html(client):
    r = client.get("/ui/")

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")


def test_ui_serves_static_assets(client):
    assert client.get("/ui/app.js").status_code == 200
    assert client.get("/ui/styles.css").status_code == 200


# EP-13 (seguridad)
def test_test_env_never_returns_full_key(client, monkeypatch):
    secret = "gsk_super_secret_value_123456"
    monkeypatch.setattr(settings, "groq_api_key", SecretStr(secret))
    monkeypatch.setattr(settings, "openai_api_key", None)

    r = client.get("/test-env")

    assert r.status_code == 200
    assert secret not in r.text
    assert r.json()["groq_api_key"] == {"status": "Configurada", "preview": "gsk_s..."}
    assert r.json()["openai_api_key"] == {"status": "No encontrada", "preview": None}


# EP-14
def test_openapi_documents_routes_and_errors(client):
    spec = client.get("/openapi.json").json()

    paths = spec["paths"]
    for route in ("analyze", "schema", "explain"):
        assert f"/api/v1/json/{route}" in paths

    explain_responses = paths["/api/v1/json/explain"]["post"]["responses"]
    assert {"200", "413", "422", "502"} <= set(explain_responses)

"""Rutas meta: /, /test-env, /ui, /openapi.json y lifespan (casos EP-11..EP-14)."""
import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings, settings
from app.main import app


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


@pytest.mark.parametrize("environment", ["production", "Production", " PRODUCTION "])
def test_test_env_is_disabled_in_production(client, monkeypatch, environment):
    monkeypatch.setattr(settings, "groq_api_key", SecretStr("gsk_super_secret_value_123456"))
    monkeypatch.setattr(settings, "environment", environment)

    r = client.get("/test-env")

    assert r.status_code == 404
    assert r.json() == {"error": "Not Found", "status_code": 404, "path": "/test-env"}
    assert "gsk_" not in r.text


def test_test_env_is_enabled_by_default():
    # Se revisa el default de la clase, no la instancia: el .env local no debe influir
    assert Settings.model_fields["environment"].default == "development"
    assert Settings(_env_file=None, environment="development").is_production is False


def test_lifespan_logs_startup_and_shutdown(caplog):
    with caplog.at_level(logging.INFO, logger="app.main"):
        with TestClient(app):  # el context manager ejecuta el lifespan
            pass

    assert "Application startup complete. Ready to accept requests." in caplog.messages
    assert "/explain rate-limit store: memory" in caplog.messages
    assert "Application shutting down." in caplog.messages


def test_openapi_contact_has_no_email(client):
    contact = client.get("/openapi.json").json()["info"]["contact"]

    assert "email" not in contact
    assert contact["url"] == "https://github.com/galilea-g19"


# EP-14
def test_openapi_documents_routes_and_errors(client):
    spec = client.get("/openapi.json").json()

    paths = spec["paths"]
    for route in ("analyze", "schema", "explain"):
        assert f"/api/v1/json/{route}" in paths

    explain_responses = paths["/api/v1/json/explain"]["post"]["responses"]
    assert {"200", "413", "422", "502"} <= set(explain_responses)

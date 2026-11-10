import json
import logging
import os

# Los tests nunca deben usar un Redis real (ni gastar comandos de Upstash),
# aunque el .env local tenga REDIS_URL: una variable de entorno vacía tiene
# prioridad sobre el .env y deja el limitador en memoria. Va antes de importar
# la app, que construye el limitador al importarse.
os.environ["REDIS_URL"] = ""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import app.services.ai as ai
from app.core.rate_limit import explain_rate_limiter
from app.core.config import settings
from app.main import app

# app.main llama a setup_logging() al importarse y abre logs/app.log, que está
# versionado. Se quita el FileHandler para que correr los tests no ensucie el
# log real; caplog sigue funcionando porque agrega su propio handler.
_root = logging.getLogger()
for _handler in list(_root.handlers):
    if isinstance(_handler, logging.FileHandler):
        _root.removeHandler(_handler)
        _handler.close()


@pytest.fixture
def client():
    # raise_server_exceptions=False: deja que el handler genérico produzca el 500
    # en lugar de propagar la excepción al test.
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Cada test empieza con los contadores de /explain en cero."""
    explain_rate_limiter.reset()
    yield
    explain_rate_limiter.reset()


@pytest.fixture(autouse=True)
def no_real_groq(monkeypatch):
    """Ningún test puede llegar a Groq por accidente: sin cliente y sin API key."""
    monkeypatch.setattr(ai, "_client", None)
    monkeypatch.setattr(settings, "groq_api_key", None)


@pytest.fixture
def fake_groq(monkeypatch):
    """Configura lo que 'responde' el modelo. Devuelve el mock de create()."""

    def _set(content: str | None = None, *, raises: Exception | None = None):
        fake = MagicMock()
        create = fake.chat.completions.create
        if raises:
            create.side_effect = raises
        else:
            create.return_value.choices = [MagicMock(message=MagicMock(content=content))]
        monkeypatch.setattr(ai, "get_client", lambda: fake)
        return create

    return _set


@pytest.fixture
def valid_explanation() -> str:
    return json.dumps({
        "summary": "Un objeto con datos de usuario.",
        "nesting_levels": 2,
        "data_types": ["object", "string"],
        "important_fields": ["user.name"],
    })

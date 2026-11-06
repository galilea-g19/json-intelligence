import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import app.services.ai as ai
from app.core.config import settings
from app.main import app


@pytest.fixture
def client():
    # raise_server_exceptions=False: deja que el handler genérico produzca el 500
    # en lugar de propagar la excepción al test.
    return TestClient(app, raise_server_exceptions=False)


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

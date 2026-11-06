"""Tests unitarios de app.services.ai (casos AI-* de docs/TESTING.md). Groq siempre simulado."""
import json
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

import app.services.ai as ai
from app.core.config import settings
from app.core.exceptions import AIResponseError, PayloadTooLargeError
from app.models.response_models import JsonExplanation


# AI-01
def test_valid_response_returns_explanation(fake_groq, valid_explanation):
    fake_groq(valid_explanation)

    result = ai.explain_json({"user": {"name": "Galilea"}})

    assert isinstance(result, JsonExplanation)
    assert result.summary == "Un objeto con datos de usuario."
    assert result.nesting_levels == 2
    assert result.data_types == ["object", "string"]
    assert result.important_fields == ["user.name"]


def test_optional_lists_default_to_empty(fake_groq):
    fake_groq(json.dumps({"summary": "s", "nesting_levels": 0}))

    result = ai.explain_json({"a": 1})

    assert result.data_types == []
    assert result.important_fields == []


# AI-02
def test_payload_over_byte_limit_never_calls_ai(fake_groq):
    create = fake_groq("{}")

    with pytest.raises(PayloadTooLargeError):
        ai.explain_json({"a": "x" * (settings.max_ai_json_bytes + 1)})

    create.assert_not_called()


# AI-03
def test_payload_over_char_limit(fake_groq, monkeypatch):
    monkeypatch.setattr(settings, "max_ai_json_bytes", 1_000_000)
    monkeypatch.setattr(settings, "max_ai_json_chars", 10)
    create = fake_groq("{}")

    with pytest.raises(PayloadTooLargeError, match="caracteres"):
        ai.explain_json({"a": "x" * 20})

    create.assert_not_called()


# AI-04
def test_byte_limit_counts_utf8_bytes_not_chars(fake_groq):
    fake_groq("{}")
    # ~2600 caracteres (< 10000) pero ~5200 bytes en UTF-8 (> 5000)
    data = {"a": "ñ" * 2600}

    with pytest.raises(PayloadTooLargeError, match="bytes"):
        ai.explain_json(data)


def test_payload_just_under_limit_is_sent(fake_groq, valid_explanation):
    create = fake_groq(valid_explanation)

    ai.explain_json({"a": "x" * 100})

    create.assert_called_once()


# AI-05
def test_non_json_response_raises(fake_groq):
    fake_groq("Claro, aquí tienes la explicación...")

    with pytest.raises(AIResponseError, match="formato esperado"):
        ai.explain_json({"a": 1})


# AI-06
@pytest.mark.parametrize("content", ["", "   \n ", None])
def test_empty_response_raises(fake_groq, content):
    fake_groq(content)

    with pytest.raises(AIResponseError, match="vacía"):
        ai.explain_json({"a": 1})


# AI-07
@pytest.mark.parametrize(
    "payload",
    [
        {"summary": "s", "nesting_levels": -1},           # ge=0
        {"nesting_levels": 1},                            # falta summary
        {"summary": "s"},                                 # falta nesting_levels
        {"summary": "s", "nesting_levels": "muchos"},     # tipo incorrecto
        {"summary": "s", "nesting_levels": 1, "data_types": "string"},  # no es lista
        ["no", "es", "objeto"],
    ],
)
def test_wrong_shape_raises(fake_groq, payload):
    fake_groq(json.dumps(payload))

    with pytest.raises(AIResponseError, match="formato esperado"):
        ai.explain_json({"a": 1})


# AI-08
def test_sdk_exception_is_wrapped(fake_groq):
    fake_groq(raises=RuntimeError("connection reset"))

    with pytest.raises(AIResponseError, match="Error al llamar a la IA"):
        ai.explain_json({"a": 1})


# AI-09
def test_missing_api_key_raises_on_client_creation():
    # no_real_groq (autouse) ya dejó _client=None y groq_api_key=None
    with pytest.raises(AIResponseError, match="GROQ_API_KEY"):
        ai.get_client()


def test_missing_api_key_surfaces_through_explain():
    with pytest.raises(AIResponseError, match="GROQ_API_KEY"):
        ai.explain_json({"a": 1})


# AI-10
def test_call_parameters(fake_groq, valid_explanation):
    create = fake_groq(valid_explanation)

    ai.explain_json({"ciudad": "Guadalajara"})

    kwargs = create.call_args.kwargs
    assert kwargs["model"] == "llama-3.3-70b-versatile"
    assert kwargs["temperature"] == 0.3
    assert kwargs["max_tokens"] == 500
    assert kwargs["response_format"] == {"type": "json_object"}

    roles = [m["role"] for m in kwargs["messages"]]
    assert roles == ["system", "user"]
    # El JSON va en el prompt sin escapar los caracteres no ASCII
    assert '"ciudad": "Guadalajara"' in kwargs["messages"][1]["content"]


def test_prompt_keeps_non_ascii(fake_groq, valid_explanation):
    create = fake_groq(valid_explanation)

    ai.explain_json({"año": "señal"})

    assert '"año": "señal"' in create.call_args.kwargs["messages"][1]["content"]


# AI-11
def test_client_is_created_once(monkeypatch):
    groq_cls = MagicMock()
    monkeypatch.setattr(ai, "Groq", groq_cls)
    monkeypatch.setattr(settings, "groq_api_key", SecretStr("gsk_test_key"))

    first = ai.get_client()
    second = ai.get_client()

    assert first is second
    groq_cls.assert_called_once_with(api_key="gsk_test_key")

"""POST /api/v1/json/explain con Groq simulado (casos EP-03..EP-05, EP-15)."""
import json

import pytest

URL = "/api/v1/json/explain"
ENVELOPE = {"error", "status_code", "path"}


# EP-03
def test_explain_returns_validated_explanation(client, fake_groq, valid_explanation):
    create = fake_groq(valid_explanation)

    r = client.post(URL, json={"data": {"user": {"name": "Galilea"}}})

    assert r.status_code == 200
    assert r.json() == {"explanation": json.loads(valid_explanation)}
    assert create.call_args.kwargs["response_format"] == {"type": "json_object"}


# EP-04
@pytest.mark.parametrize(
    "content",
    ["no es json", "", '{"summary": "x", "nesting_levels": -1}'],
)
def test_malformed_ai_output_is_502(client, fake_groq, content):
    fake_groq(content)

    r = client.post(URL, json={"data": {"a": 1}})

    assert r.status_code == 502
    assert set(r.json()) == ENVELOPE
    assert r.json()["path"] == URL


def test_sdk_failure_is_502(client, fake_groq):
    fake_groq(raises=RuntimeError("timeout"))

    r = client.post(URL, json={"data": {"a": 1}})

    assert r.status_code == 502
    assert set(r.json()) == ENVELOPE


def test_missing_api_key_is_502(client):
    r = client.post(URL, json={"data": {"a": 1}})

    assert r.status_code == 502
    assert "GROQ_API_KEY" in r.json()["error"]


# EP-05
def test_payload_over_ai_limit_is_413_and_never_calls_ai(client, fake_groq):
    create = fake_groq("{}")

    r = client.post(URL, json={"data": {"a": "x" * 6000}})

    assert r.status_code == 413
    assert set(r.json()) == ENVELOPE
    create.assert_not_called()


def test_explain_missing_data_is_422(client):
    assert client.post(URL, json={}).status_code == 422


# EP-15: el cliente recibe un mensaje genérico; el detalle solo va al log.
def test_502_does_not_leak_validation_details(client, fake_groq):
    fake_groq('{"summary": "x", "nesting_levels": -1}')

    r = client.post(URL, json={"data": {"a": 1}})

    assert r.status_code == 502
    assert r.json()["error"] == "La respuesta de la IA no cumple el formato esperado."
    assert "validation error" not in r.text
    assert "pydantic" not in r.text
    assert "nesting_levels" not in r.text


def test_502_does_not_leak_provider_error(client, fake_groq):
    fake_groq(raises=RuntimeError("401 invalid api key gsk_abc123 for org-xyz"))

    r = client.post(URL, json={"data": {"a": 1}})

    assert r.status_code == 502
    assert r.json()["error"] == "Error al llamar a la IA. Intenta de nuevo más tarde."
    assert "gsk_abc123" not in r.text
    assert "RuntimeError" not in r.text

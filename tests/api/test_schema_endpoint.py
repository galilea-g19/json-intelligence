"""POST /api/v1/json/schema (casos EP-02, ER-04)."""
import jsonschema

import app.routes.json_routes as routes

URL = "/api/v1/json/schema"


# EP-02
def test_schema_uses_alias_and_title(client):
    data = {"user": {"name": "Galilea"}, "skills": ["Python"]}

    r = client.post(URL, json={"data": data})

    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"schema"}  # alias "schema", nunca "json_schema"
    schema = body["schema"]
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert schema["title"] == "JSONData"
    assert schema["required"] == ["user", "skills"]
    jsonschema.validate(instance=data, schema=schema)


def test_schema_missing_data_is_422(client):
    assert client.post(URL, json={"datos": {}}).status_code == 422


# ER-04
def test_schema_service_failure_becomes_400(client, monkeypatch):
    def boom(*_args, **_kwargs):
        raise ValueError("no se pudo generar")

    monkeypatch.setattr(routes, "generate_schema", boom)

    r = client.post(URL, json={"data": {"a": 1}})

    assert r.status_code == 400
    assert r.json()["error"] == "no se pudo generar"

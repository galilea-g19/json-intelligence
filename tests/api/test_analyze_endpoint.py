"""POST /api/v1/json/analyze (casos EP-01, EP-06..EP-09, ER-04)."""
import pytest

import app.routes.json_routes as routes

URL = "/api/v1/json/analyze"


# EP-01
def test_analyze_returns_expected_shape(client):
    r = client.post(URL, json={"data": {"user": {"name": "Galilea", "age": 30}, "skills": ["Python"]}})

    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"key_count", "types", "nested_structure"}
    assert body["key_count"] == 4
    assert body["types"] == {
        "user": "object",
        "user.name": "string",
        "user.age": "integer",
        "skills": "array",
    }
    assert body["nested_structure"] == {
        "user": {"name": "string", "age": "integer"},
        "skills": ["string"],
    }


def test_analyze_merges_every_object_in_arrays(client):
    data = {"usuarios": [{"nombre": "Ana", "email": None}, {"nombre": "Luis", "email": "l@x.com", "edad": 30}]}

    r = client.post(URL, json={"data": data})

    assert r.status_code == 200
    body = r.json()
    assert body["key_count"] == 4
    assert body["types"] == {
        "usuarios": "array",
        "usuarios[].nombre": "string",
        "usuarios[].email": "null | string",
        "usuarios[].edad": "integer",
    }
    assert body["nested_structure"] == {
        "usuarios": [{"nombre": "string", "email": "null | string", "edad": "integer"}]
    }


def test_analyze_empty_object(client):
    r = client.post(URL, json={"data": {}})

    assert r.status_code == 200
    assert r.json() == {"key_count": 0, "types": {}, "nested_structure": {}}


# EP-06
def test_missing_data_is_422(client):
    r = client.post(URL, json={})

    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "Invalid request"
    assert isinstance(body["details"], list) and body["details"]
    assert body["path"] == URL


# EP-07
@pytest.mark.parametrize("data", [[1, 2], "texto", 42, None, True])
def test_data_must_be_an_object(client, data):
    r = client.post(URL, json={"data": data})

    assert r.status_code == 422


# EP-08
def test_malformed_json_body_is_422(client):
    r = client.post(URL, content="{esto no es json", headers={"content-type": "application/json"})

    assert r.status_code == 422


# EP-09
def test_get_on_post_route_is_405(client):
    r = client.get(URL)

    assert r.status_code == 405
    assert r.json() == {"error": "Method Not Allowed", "status_code": 405, "path": URL}


# ER-04
def test_service_failure_becomes_400(client, monkeypatch):
    def boom(_):
        raise ValueError("estructura no soportada")

    monkeypatch.setattr(routes, "analyze_json", boom)

    r = client.post(URL, json={"data": {"a": 1}})

    assert r.status_code == 400
    assert r.json() == {"error": "estructura no soportada", "status_code": 400, "path": URL}

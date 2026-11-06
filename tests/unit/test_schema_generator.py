"""Tests unitarios de app.services.schema_generator.generate_schema (casos SC-* de docs/TESTING.md)."""
import jsonschema
import pytest

from app.services.schema_generator import generate_schema

DRAFT_07 = "http://json-schema.org/draft-07/schema#"


def prop(data, key):
    return generate_schema(data)["properties"][key]


# SC-01
def test_header():
    schema = generate_schema({}, name="JSONData")

    assert schema["$schema"] == DRAFT_07
    assert schema["title"] == "JSONData"
    assert schema["type"] == "object"
    assert schema["properties"] == {}
    assert schema["required"] == []


def test_default_title_is_root():
    assert generate_schema({})["title"] == "Root"


# SC-02 / SC-03
@pytest.mark.parametrize(
    "value, expected_type",
    [
        (1, "integer"),
        (1.5, "number"),
        (True, "boolean"),  # SC-03: bool hereda de int, no debe salir "integer"
        (False, "boolean"),
        (None, "null"),
        ("x", "string"),
    ],
)
def test_primitive_types(value, expected_type):
    assert prop({"k": value}, "k") == {"type": expected_type}


# SC-04
def test_required_lists_every_key_in_order():
    schema = generate_schema({"b": 1, "a": 2, "c": 3})

    assert schema["required"] == ["b", "a", "c"]


# SC-05
def test_nested_object_is_recursive():
    data = {"user": {"name": "Galilea", "address": {"city": "GDL"}}}

    assert prop(data, "user") == {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "address": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
        "required": ["name", "address"],
    }


# SC-06
def test_homogeneous_array_collapses_to_items():
    assert prop({"l": ["a", "b", "c"]}, "l") == {
        "type": "array",
        "items": {"type": "string"},
    }


def test_homogeneous_array_of_objects():
    data = {"l": [{"n": 1}, {"n": 2}]}

    assert prop(data, "l") == {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {"n": {"type": "integer"}},
            "required": ["n"],
        },
    }


# SC-07
def test_mixed_array_uses_anyof_without_duplicates():
    data = {"l": [1, "a", None, 2, "b"]}

    assert prop(data, "l") == {
        "type": "array",
        "items": {
            "anyOf": [
                {"type": "integer"},
                {"type": "string"},
                {"type": "null"},
            ]
        },
    }


# SC-08
def test_empty_array_accepts_any_items():
    assert prop({"l": []}, "l") == {"type": "array", "items": {}}


# SC-09: el schema inferido debe validar el mismo JSON del que salió.
SAMPLES = [
    {},
    {"a": 1, "b": 1.5, "c": True, "d": None, "e": "x"},
    {"user": {"name": "Galilea", "skills": ["Python", "FastAPI"]}},
    {"l": [1, "a", None, 2.5, False]},
    {"l": [{"n": 1}, {"n": 2, "m": True}]},
    {"m": [[1, 2], [3]], "e": []},
    {"deep": {"a": {"b": {"c": [{"d": [1]}]}}}},
]


@pytest.mark.parametrize("data", SAMPLES)
def test_generated_schema_is_valid_draft07(data):
    schema = generate_schema(data)

    jsonschema.Draft7Validator.check_schema(schema)


@pytest.mark.parametrize("data", SAMPLES)
def test_generated_schema_validates_its_own_input(data):
    schema = generate_schema(data)

    jsonschema.validate(instance=data, schema=schema)


def test_schema_rejects_missing_required_key():
    schema = generate_schema({"a": 1, "b": "x"})

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance={"a": 1}, schema=schema)


def test_schema_rejects_wrong_type():
    schema = generate_schema({"a": 1})

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance={"a": "uno"}, schema=schema)


def test_does_not_mutate_input():
    data = {"a": {"b": [{"c": 1}]}}
    snapshot = {"a": {"b": [{"c": 1}]}}

    generate_schema(data)

    assert data == snapshot


# ---------------------------------------------------------------------------
# Bug / decisión de diseño conocida
# ---------------------------------------------------------------------------

# SC-11
@pytest.mark.xfail(reason="SC-11: objetos con distinta forma generan entradas separadas en anyOf en vez de unirse")
def test_objects_with_different_shapes_are_merged():
    data = {"l": [{"n": 1}, {"n": 2, "m": True}]}

    assert prop(data, "l")["items"] == {
        "type": "object",
        "properties": {"n": {"type": "integer"}, "m": {"type": "boolean"}},
        "required": ["n"],
    }

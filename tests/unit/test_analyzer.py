"""Tests unitarios de app.services.analyzer (casos AN-* de docs/TESTING.md)."""
import pytest

from app.services.analyzer import analyze_json, json_type


def key_types(data):
    return analyze_json(data)["summary"]["key_types"]


def total_keys(data):
    return analyze_json(data)["summary"]["total_keys_recursive"]


def structure(data):
    return analyze_json(data)["structure"]


# AN-01
def test_flat_object_counts_keys_and_types():
    data = {"a": 1, "b": "x"}

    assert total_keys(data) == 2
    assert key_types(data) == {"a": "integer", "b": "string"}
    assert structure(data) == {"a": "integer", "b": "string"}


# AN-02
def test_empty_object():
    result = analyze_json({})

    assert result["summary"]["total_keys_recursive"] == 0
    assert result["summary"]["key_types"] == {}
    assert result["structure"] == {}


# AN-03
def test_nested_object_uses_dotted_paths():
    data = {"b": {"c": "x"}}

    assert key_types(data) == {"b": "object", "b.c": "string"}
    assert total_keys(data) == 2  # la clave padre y la anidada
    assert structure(data) == {"b": {"c": "string"}}


# AN-04
def test_deep_nesting_builds_full_path():
    data = {"a": {"b": {"c": {"d": True}}}}

    assert key_types(data) == {
        "a": "object",
        "a.b": "object",
        "a.b.c": "object",
        "a.b.c.d": "boolean",
    }
    assert total_keys(data) == 4
    assert structure(data) == {"a": {"b": {"c": {"d": "boolean"}}}}


# AN-05
def test_array_of_objects_uses_bracket_path():
    data = {"l": [{"n": 1}]}

    assert key_types(data) == {"l": "array", "l[].n": "integer"}
    assert total_keys(data) == 2
    assert structure(data) == {"l": [{"n": "integer"}]}


# AN-06
def test_array_of_primitives_lists_each_item_type():
    data = {"l": [1, "a", 2.5]}

    assert structure(data) == {"l": ["integer", "string", "number"]}
    assert key_types(data) == {"l": "array"}


def test_array_of_primitives_lists_each_type_once():
    # La estructura describe la FORMA del arreglo, no su tamaño
    assert structure({"l": [1, 2, 3, "a", "b"]}) == {"l": ["integer", "string"]}


# AN-07
def test_empty_array():
    data = {"l": []}

    assert structure(data) == {"l": []}
    assert key_types(data) == {"l": "array"}
    assert total_keys(data) == 1


# AN-08 / AN-11: vocabulario de tipos JSON (el mismo que usan /schema y /explain)
@pytest.mark.parametrize(
    "value, expected",
    [
        (True, "boolean"),  # bool hereda de int: no debe reportarse como integer
        (False, "boolean"),
        (None, "null"),
        (1.5, "number"),
        (0, "integer"),
        ("", "string"),
        ({}, "object"),
        ([], "array"),
    ],
)
def test_primitive_types(value, expected):
    assert key_types({"k": value}) == {"k": expected}
    assert json_type(value) == expected


def test_never_returns_python_type_names():
    data = {"o": {"x": None}, "l": [True, 1.0], "s": "x", "i": 1}
    python_names = {"dict", "list", "str", "int", "float", "bool", "NoneType"}

    reported = set(key_types(data).values()) | set(structure(data)["l"])

    assert reported.isdisjoint(python_names)


# AN-09: arreglos dentro de arreglos no se recorren; se reportan como "array" (una vez).
def test_nested_arrays_do_not_crash():
    data = {"m": [[1, 2], [3]]}

    assert structure(data) == {"m": ["array"]}
    assert key_types(data) == {"m": "array"}


def test_mixed_object_counts_every_level():
    data = {
        "user": {"name": "Galilea", "age": 30},
        "skills": ["Python", "FastAPI"],
        "projects": [{"name": "json-intelligence", "stars": 5}],
    }

    assert total_keys(data) == 7
    assert key_types(data) == {
        "user": "object",
        "user.name": "string",
        "user.age": "integer",
        "skills": "array",
        "projects": "array",
        "projects[].name": "string",
        "projects[].stars": "integer",
    }


def test_returns_summary_and_structure():
    result = analyze_json({"a": 1})

    assert set(result) == {"summary", "structure"}
    assert set(result["summary"]) == {"total_keys_recursive", "key_types"}


def test_does_not_mutate_input():
    data = {"a": {"b": [{"c": 1}]}}
    snapshot = {"a": {"b": [{"c": 1}]}}

    analyze_json(data)

    assert data == snapshot


def test_total_keys_equals_number_of_unique_paths():
    data = {"a": {"b": 1}, "l": [{"x": 1}, {"x": 2, "y": {"z": None}}], "p": [1, "a"]}

    result = analyze_json(data)["summary"]

    assert result["total_keys_recursive"] == len(result["key_types"])


# ---------------------------------------------------------------------------
# AN-10: se analizan TODOS los elementos del arreglo, no solo el primero
# ---------------------------------------------------------------------------

def test_array_of_objects_merges_keys_from_all_items():
    data = {"l": [{"n": 1}, {"n": 2, "m": True}]}

    assert key_types(data) == {"l": "array", "l[].n": "integer", "l[].m": "boolean"}
    assert structure(data) == {"l": [{"n": "integer", "m": "boolean"}]}


# Decisión 1: rutas únicas
def test_key_count_uses_unique_paths_not_occurrences():
    data = {"usuarios": [{"nombre": f"u{i}"} for i in range(100)]}

    assert total_keys(data) == 2  # "usuarios" + "usuarios[].nombre"
    assert key_types(data) == {"usuarios": "array", "usuarios[].nombre": "string"}


# Decisión 2: tipos que varían entre objetos -> "a | b" (orden alfabético)
def test_varying_types_are_reported_as_union():
    data = {"usuarios": [{"email": None}, {"email": "l@x.com"}]}

    assert key_types(data)["usuarios[].email"] == "null | string"
    assert structure(data) == {"usuarios": [{"email": "null | string"}]}


def test_union_does_not_depend_on_item_order():
    forward = {"l": [{"e": None}, {"e": "x"}, {"e": 1}]}
    backward = {"l": [{"e": 1}, {"e": "x"}, {"e": None}]}

    assert key_types(forward) == key_types(backward)
    assert key_types(forward)["l[].e"] == "integer | null | string"


# Decisión 3: arreglos mezclados conservan todos los tipos
def test_mixed_array_keeps_object_and_other_types():
    data = {"items": [{"a": 1}, "texto", 3]}

    assert structure(data) == {"items": [{"a": "integer"}, "string", "integer"]}
    assert key_types(data) == {"items": "array", "items[].a": "integer"}


def test_objects_are_analyzed_even_if_not_first():
    data = {"items": [1, {"a": 1}, "x", {"b": True}]}

    assert key_types(data) == {"items": "array", "items[].a": "integer", "items[].b": "boolean"}
    assert structure(data) == {"items": ["integer", {"a": "integer", "b": "boolean"}, "string"]}


def test_nested_objects_inside_array_are_merged_recursively():
    data = {"l": [{"u": {"name": "a"}}, {"u": {"name": "b", "age": 3}}]}

    assert key_types(data) == {
        "l": "array",
        "l[].u": "object",
        "l[].u.name": "string",
        "l[].u.age": "integer",
    }
    assert structure(data) == {"l": [{"u": {"name": "string", "age": "integer"}}]}


def test_object_and_null_for_same_key():
    data = {"l": [{"u": {"n": 1}}, {"u": None}]}

    assert key_types(data) == {"l": "array", "l[].u": "null | object", "l[].u.n": "integer"}
    # La estructura guarda solo la unión; las rutas anidadas siguen en key_types
    assert structure(data) == {"l": [{"u": "null | object"}]}


def test_arrays_inside_array_objects_are_merged():
    data = {"l": [{"tags": ["a"]}, {"tags": [1, "b"]}]}

    assert key_types(data) == {"l": "array", "l[].tags": "array"}
    assert structure(data) == {"l": [{"tags": ["string", "integer"]}]}


def test_objects_in_nested_arrays_of_array_objects_are_merged():
    data = {"l": [{"x": [{"a": 1}]}, {"x": [{"b": None}]}]}

    assert key_types(data) == {
        "l": "array",
        "l[].x": "array",
        "l[].x[].a": "integer",
        "l[].x[].b": "null",
    }
    assert structure(data) == {"l": [{"x": [{"a": "integer", "b": "null"}]}]}


def test_array_with_empty_objects():
    assert structure({"l": [{}, {}]}) == {"l": [{}]}
    assert key_types({"l": [{}, {"a": 1}]}) == {"l": "array", "l[].a": "integer"}


def test_array_and_null_for_same_key():
    data = {"l": [{"x": [1]}, {"x": None}]}

    assert key_types(data)["l[].x"] == "array | null"
    assert structure(data) == {"l": [{"x": "array | null"}]}


def test_nested_array_gains_an_object_from_a_later_item():
    data = {"l": [{"x": [1]}, {"x": [{"a": 1}]}]}

    assert structure(data) == {"l": [{"x": ["integer", {"a": "integer"}]}]}
    assert key_types(data)["l[].x[].a"] == "integer"

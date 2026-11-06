"""Tests unitarios de app.services.analyzer.analyze_json (casos AN-* de docs/TESTING.md)."""
import pytest

from app.services.analyzer import analyze_json


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
    assert key_types(data) == {"a": "int", "b": "str"}
    assert structure(data) == {"a": "int", "b": "str"}


# AN-02
def test_empty_object():
    result = analyze_json({})

    assert result["summary"]["total_keys_recursive"] == 0
    assert result["summary"]["key_types"] == {}
    assert result["structure"] == {}


# AN-03
def test_nested_object_uses_dotted_paths():
    data = {"b": {"c": "x"}}

    assert key_types(data) == {"b": "dict", "b.c": "str"}
    assert total_keys(data) == 2  # la clave padre y la anidada
    assert structure(data) == {"b": {"c": "str"}}


# AN-04
def test_deep_nesting_builds_full_path():
    data = {"a": {"b": {"c": {"d": True}}}}

    assert key_types(data) == {
        "a": "dict",
        "a.b": "dict",
        "a.b.c": "dict",
        "a.b.c.d": "bool",
    }
    assert total_keys(data) == 4
    assert structure(data) == {"a": {"b": {"c": {"d": "bool"}}}}


# AN-05
def test_array_of_objects_uses_bracket_path():
    data = {"l": [{"n": 1}]}

    assert key_types(data) == {"l": "list", "l[].n": "int"}
    assert total_keys(data) == 2
    assert structure(data) == {"l": [{"n": "int"}]}


# AN-06
def test_array_of_primitives_lists_each_item_type():
    data = {"l": [1, "a", 2.5]}

    assert structure(data) == {"l": ["int", "str", "float"]}
    assert key_types(data) == {"l": "list"}


# AN-07
def test_empty_array():
    data = {"l": []}

    assert structure(data) == {"l": []}
    assert key_types(data) == {"l": "list"}
    assert total_keys(data) == 1


# AN-08
@pytest.mark.parametrize(
    "value, expected",
    [
        (True, "bool"),  # bool hereda de int: no debe reportarse como int
        (None, "NoneType"),
        (1.5, "float"),
        (0, "int"),
        ("", "str"),
    ],
)
def test_primitive_types(value, expected):
    assert key_types({"k": value}) == {"k": expected}


# AN-09: documenta el comportamiento actual con arreglos anidados.
def test_nested_arrays_do_not_crash():
    data = {"m": [[1, 2], [3]]}

    assert structure(data) == {"m": ["list", "list"]}
    assert key_types(data) == {"m": "list"}


def test_mixed_object_counts_every_level():
    data = {
        "user": {"name": "Galilea", "age": 30},
        "skills": ["Python", "FastAPI"],
        "projects": [{"name": "json-intelligence", "stars": 5}],
    }

    assert total_keys(data) == 7
    assert key_types(data) == {
        "user": "dict",
        "user.name": "str",
        "user.age": "int",
        "skills": "list",
        "projects": "list",
        "projects[].name": "str",
        "projects[].stars": "int",
    }


def test_returns_summary_and_structure():
    result = analyze_json({"a": 1})

    assert set(result) == {"summary", "structure"}


def test_does_not_mutate_input():
    data = {"a": {"b": [{"c": 1}]}}
    snapshot = {"a": {"b": [{"c": 1}]}}

    analyze_json(data)

    assert data == snapshot


# ---------------------------------------------------------------------------
# Bugs conocidos (xfail estricto: si se arreglan, el test "pasa" y pytest avisa)
# ---------------------------------------------------------------------------

# AN-10
@pytest.mark.xfail(reason="BUG AN-10: solo analiza el primer elemento de un arreglo de objetos")
def test_array_of_objects_merges_keys_from_all_items():
    data = {"l": [{"n": 1}, {"n": 2, "m": True}]}

    assert "l[].m" in key_types(data)


# AN-11
@pytest.mark.xfail(reason="BUG AN-11: usa nombres de tipo de Python en vez de JSON (pendiente de decisión)")
def test_uses_json_type_names():
    data = {"o": {}, "s": "x", "l": [], "n": None}

    assert key_types(data) == {"o": "object", "s": "string", "l": "array", "n": "null"}

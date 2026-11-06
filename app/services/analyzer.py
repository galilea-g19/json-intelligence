from typing import Any, Dict, List, Optional, Tuple

TYPE_SEPARATOR = " | "


def json_type(value: Any) -> str:
    """
    Return the JSON type name of a decoded JSON value.

    Uses the same vocabulary as JSON Schema (and as /schema and /explain), not
    Python's: "object" instead of "dict", "null" instead of "NoneType", etc.
    bool is checked before int because bool is a subclass of int in Python.
    """
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if value is None:
        return "null"
    # Not reachable with input decoded from JSON; kept as a safe fallback.
    return type(value).__name__


def _union(existing: Optional[str], new: str) -> str:
    """
    Combine two type descriptions into "a | b".

    Sorted alphabetically so the result doesn't depend on the order of the
    items: [{"e": null}, {"e": "x"}] and the reverse both give "null | string".
    """
    if existing is None or existing == new:
        return new
    parts = set(existing.split(TYPE_SEPARATOR)) | set(new.split(TYPE_SEPARATOR))
    return TYPE_SEPARATOR.join(sorted(parts))


def _describe(shape: Any) -> str:
    """Type name of a structure node: a dict is an object, a list an array."""
    if isinstance(shape, dict):
        return "object"
    if isinstance(shape, list):
        return "array"
    return shape  # already a type name (possibly a union)


def _merge_shape_lists(a: List[Any], b: List[Any]) -> List[Any]:
    """Merge two array structures: one merged object at most, other shapes unique."""
    result = list(a)
    for shape in b:
        if isinstance(shape, dict):
            index = next((i for i, s in enumerate(result) if isinstance(s, dict)), None)
            if index is None:
                result.append(shape)
            else:
                result[index] = _merge_structures(result[index], shape)
        elif shape not in result:
            result.append(shape)
    return result


def _merge_values(a: Any, b: Any) -> Any:
    if a == b:
        return a
    if isinstance(a, dict) and isinstance(b, dict):
        return _merge_structures(a, b)
    if isinstance(a, list) and isinstance(b, list):
        return _merge_shape_lists(a, b)
    # Different kinds (e.g. an object in one item and null in another): the
    # structure keeps only the type union; the nested paths are still listed
    # in key_types.
    return _union(_describe(a), _describe(b))


def _merge_structures(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two object structures key by key, keeping first-appearance order."""
    result = dict(a)
    for key, value in b.items():
        result[key] = _merge_values(result[key], value) if key in result else value
    return result


def _analyze_array(items: List[Any], path: str) -> Tuple[Dict[str, str], List[Any]]:
    """
    Analyze EVERY item of an array, not just the first one.

    - key_types: the keys of all the objects in the array, under "<path>[]".
      Each path appears once (unique paths); if its type varies between
      objects it is reported as a union, e.g. "null | string".
    - structure: one merged object (at the position of the first object) plus
      every other distinct item type, in order of first appearance.
    """
    key_types: Dict[str, str] = {}
    shapes: List[Any] = []
    object_index: Optional[int] = None  # position of the merged object in shapes

    for item in items:
        if isinstance(item, dict):
            nested = analyze_json(item, path + "[]")
            for nested_path, nested_type in nested["summary"]["key_types"].items():
                key_types[nested_path] = _union(key_types.get(nested_path), nested_type)

            if object_index is None:
                object_index = len(shapes)
                shapes.append(nested["structure"])
            else:
                shapes[object_index] = _merge_structures(shapes[object_index], nested["structure"])
        else:
            item_type = json_type(item)
            if item_type not in shapes:
                shapes.append(item_type)

    return key_types, shapes


def analyze_json(data: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
    """
    Recursively analyze a JSON object, including nested objects and the
    objects inside arrays.

    total_keys_recursive counts UNIQUE paths: "users[].name" counts once no
    matter how many users the array holds. It describes the shape of the JSON,
    not its size.
    """
    key_types: Dict[str, str] = {}
    structure: Dict[str, Any] = {}

    for key, value in data.items():
        current_path = f"{parent_key}.{key}" if parent_key else key
        key_types[current_path] = json_type(value)

        if isinstance(value, dict):
            nested = analyze_json(value, current_path)
            key_types.update(nested["summary"]["key_types"])
            structure[key] = nested["structure"]

        elif isinstance(value, list):
            array_types, array_structure = _analyze_array(value, current_path)
            key_types.update(array_types)
            structure[key] = array_structure

        else:
            structure[key] = key_types[current_path]

    summary = {
        "total_keys_recursive": len(key_types),
        "max_depth": 0,
        "array_count": 0,
        "list_count": 0,
        "key_types": key_types,
    }

    return {
        "summary": summary,
        "structure": structure
    }

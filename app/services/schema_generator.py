import json
from typing import Any, Dict, List


def _merge_schemas(schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Combine the schemas observed at the same position (array items, or the
    same property across several objects) into a single schema.

    - Identical schemas are deduplicated.
    - Every object schema is merged into ONE object (see _merge_objects), so an
      array of records with optional fields yields one item schema instead of
      one anyOf branch per shape.
    - Whatever is still different ends up in anyOf, in order of first appearance.
    """
    unique: List[Dict[str, Any]] = []
    seen = set()
    for schema in schemas:
        key = json.dumps(schema, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(schema)

    objects = [s for s in unique if s.get("type") == "object"]

    result: List[Dict[str, Any]] = []
    object_added = False
    for schema in unique:
        if schema.get("type") == "object":
            if not object_added:
                result.append(objects[0] if len(objects) == 1 else _merge_objects(objects))
                object_added = True
        else:
            result.append(schema)

    if len(result) == 1:
        return result[0]
    return {"anyOf": result}


def _merge_objects(objects: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge several object schemas:
    - properties: union of every key seen (in order of first appearance); a key
      whose type differs between objects becomes an anyOf of those types.
    - required: only the keys present in ALL of the objects.
    """
    per_key: Dict[str, List[Dict[str, Any]]] = {}
    for obj in objects:
        for key, prop_schema in obj["properties"].items():
            per_key.setdefault(key, []).append(prop_schema)

    return {
        "type": "object",
        "properties": {key: _merge_schemas(found) for key, found in per_key.items()},
        "required": [key for key in per_key if all(key in obj["required"] for obj in objects)],
    }


def _get_type_schema(value: Any, field_name: str) -> Dict[str, Any]:
    """Return the schema fragment for a given value."""
    value_type = type(value).__name__

    if isinstance(value, dict):
        # Nested object: recursion
        return {
            "type": "object",
            "properties": {k: _get_type_schema(v, k) for k, v in value.items()},
            "required": list(value.keys())
        }
    elif isinstance(value, list):
        if len(value) == 0:
            return {"type": "array", "items": {}}
        return {
            "type": "array",
            "items": _merge_schemas([_get_type_schema(item, "item") for item in value]),
        }

    elif value_type == "int":
        return {"type": "integer"}
    elif value_type == "float":
        return {"type": "number"}
    elif value_type == "bool":
        return {"type": "boolean"}
    elif value_type == "NoneType":
        return {"type": "null"}
    else:  # str, etc.
        return {"type": "string"}


def generate_schema(data: Dict[str, Any], name: str = "Root") -> Dict[str, Any]:
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": name,
        "type": "object",
        "properties": {},
        "required": []
    }

    for key, value in data.items():
        prop_schema = _get_type_schema(value, key)
        schema["properties"][key] = prop_schema
        schema["required"].append(key)

    return schema

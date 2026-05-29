from typing import Any, Dict

def _get_unique_types(values: list) -> list:
    schemas = []
    seen = set()
    for v in values:
        schema = _get_type_schema(v, "item")
        key = frozenset(schema.items())
        if key not in seen:
            seen.add(key)
            schemas.append(schema)


    return schemas

def _get_type_schema(value: Any, field_name: str) -> Dict[str, Any]:
    """Retorna el fragmento de schema para un valor dado."""
    value_type = type(value).__name__

    if isinstance(value, dict):
        # Objeto anidado: recursión
        return {
            "type": "object",
            "properties": {k: _get_type_schema(v, k) for k, v in value.items()},
            "required": list(value.keys())
        }
    elif isinstance(value, list):
       if len(value) == 0:
           return {"type": "array", "items": {}}
       unique_types = _get_unique_types(value)

       if len(unique_types) == 1:
           return {"type": "array", "items": unique_types[0]}
       else:
           return {"type": "array", "items": {"anyOf": unique_types}}

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
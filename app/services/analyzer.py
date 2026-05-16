from typing import Dict, Any, Union

def analyze_json(data: Dict[str, Any]) -> Dict[str, Any]:
    summary = {
        "total_keys": 0,
        "key_types": {}
    }
    structure = {}

    for key, value in data.items():
        summary["total_keys"] += 1
        summary["key_types"][key] = type(data[key]).__name__

        if isinstance(value, dict):
            nested_analysis = analyze_json(value)
            summary["total_keys"] += 1

            structure[key] = {
                "type": "Object",
                "properties": nested_analysis["structure"]
            }
        
        if isinstance(value, list):
            summary["total_keys"] += 1
            item_types = list(set([type(item).__name__ for item in value]))
            structure[key] = item_types
            
        else:
            structure[key] = type(value).__name__

    return {
        "summary": summary,
        "structure": structure
    }
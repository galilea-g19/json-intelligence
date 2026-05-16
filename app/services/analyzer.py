from typing import Dict, Any, Union

def analyze_json(data: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
    summary = {
        "total_keys_recursive": 0,
        "max_depth": 0,
        "array_count": 0,
        "list_count": 0,
        "key_types": {}
    }
    structure = {}

    for key, value in data.items():
        current_path = f"{parent_key}.{key}" if parent_key else key
        value_type = type(value).__name__
        summary["total_keys_recursive"] += 1
        summary["key_types"][current_path] = value_type

        print("current_path -->",current_path)
        if isinstance(value, dict):
            nested_result = analyze_json(value, current_path)
            summary["total_keys_recursive"] += nested_result["summary"]["total_keys_recursive"]
            summary["key_types"].update(nested_result["summary"]["key_types"])
            structure[key] = nested_result["structure"]
        
        elif isinstance(value, list):
            if value and isinstance(value[0], dict):
                nested_result = analyze_json(value, current_path + "[]")
                summary["total_keys_recursive"] += nested_result["summary"]["total_keys_recursive"]
                summary["key_types"].update(nested_result["summary"]["key_types"])
                structure[key] = [summary[structure]]
            else:                
                structure[key] = list([type(item).__name__ for item in value])

        else:
            structure[key] = value_type

    return {
        "summary": summary,
        "structure": structure
    }
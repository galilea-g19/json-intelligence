from typing import Dict, Any, Union
from app.models.request_models import JsonInput

def analyze_json (data: Dict[str, any]) -> Dict[str, any]:
    summary = {
        "total_keys": 0,
        "key_types": {},
        "structure": {}
    }


    return summary
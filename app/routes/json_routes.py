from fastapi import APIRouter, HTTPException
from app.models.request_models import JsonInput
from app.models.response_models import AnalysisResponse, ErrorResponse


router = APIRouter()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_json(payload: JsonInput):
    try:
        data = payload.data
        types_dict = {k: type(v).__name__ for k, v in data.items()},
        result = {
            "key_count": len(data),
            "types": {k: type(v).__name__ for k, v in data.items()},
            "nested_structure": {"info": {"Example": "valir"}}
        }

        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
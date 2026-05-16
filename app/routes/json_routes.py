from fastapi import APIRouter, HTTPException
from app.models.request_models import JsonInput
from app.models.response_models import AnalysisResponse, ErrorResponse
from app.services.analyzer import analyze_json

router = APIRouter()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_json_endpoint(payload: JsonInput):
    try:
        result = analyze_json(payload.data)

        return {
            "key_count": result["summary"]["total_keys"],
            "types": result["summary"]["key_types"],
            "nested_structure": result["structure"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
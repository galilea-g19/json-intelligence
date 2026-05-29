from fastapi import APIRouter, HTTPException
from app.models.request_models import JsonInput
from app.models.response_models import AnalysisResponse, ErrorResponse, SchemaResponse
from app.services.analyzer import analyze_json
from app.services.schema_generator import generate_schema

router = APIRouter()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_json_endpoint(payload: JsonInput):
    try:
        result = analyze_json(payload.data)

        return {
            "key_count": result["summary"]["total_keys_recursive"],
            "types": result["summary"]["key_types"],
            "nested_structure": result["structure"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/schema", response_model=SchemaResponse)
async def generate_json_schema(payload: JsonInput):
    try:
        data = payload.data 
        schema = generate_schema(data, name="JSONData")
        return {"schema": schema}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
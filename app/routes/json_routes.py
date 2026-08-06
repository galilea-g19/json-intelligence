from fastapi import APIRouter, HTTPException
from app.models.request_models import JsonInput
from app.models.response_models import AnalysisResponse, ErrorResponse, SchemaResponse, ExplainResponse
from app.services.analyzer import analyze_json
from app.services.schema_generator import generate_schema
from app.services.ai import explain_json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_json_endpoint(payload: JsonInput):
    try:
        result = analyze_json(payload.data)
        logger.info(f"Analysis successful. Total keys: {result['summary']['total_keys_recursive']}")

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
    

@router.post("/explain", response_model=ExplainResponse)
async def explain_json_endpoint(payload: JsonInput):
    """
    Receive a JSON, send it to Groq and return a structured explanation.

    Errors (PayloadTooLargeError -> 413, AIResponseError -> 502) are handled by
    the global exception handlers registered in app.core.exceptions.
    """
    data = payload.data
    explanation = explain_json(data)

    logger.info(f"Explanation successful. Nesting levels: {explanation.nesting_levels}")
    return ExplainResponse(explanation=explanation)
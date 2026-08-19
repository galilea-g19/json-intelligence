from fastapi import APIRouter, HTTPException
from app.models.request_models import JsonInput
from app.models.response_models import AnalysisResponse, ErrorResponse, SchemaResponse, ExplainResponse
from app.services.analyzer import analyze_json
from app.services.schema_generator import generate_schema
from app.services.ai import explain_json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Error responses shared by every endpoint, so Swagger documents the real
# envelope produced by app.core.exceptions instead of FastAPI's default.
COMMON_ERRORS = {
    413: {"model": ErrorResponse, "description": "Request body over the configured limit"},
    422: {"model": ErrorResponse, "description": "`data` is missing or is not a JSON object"},
}


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="Analyze a JSON structure",
    description=(
        "Walks the object recursively and reports how many keys it holds, the "
        "type of every key (dotted paths for nested keys, `[]` for objects inside "
        "arrays) and a type-only mirror of the structure."
    ),
    responses={
        **COMMON_ERRORS,
        400: {"model": ErrorResponse, "description": "The payload could not be analyzed"},
    },
)
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

@router.post(
    "/schema",
    response_model=SchemaResponse,
    summary="Generate a JSON Schema",
    description=(
        "Infers a draft-07 JSON Schema from the payload. Every key present in the "
        "sample is treated as required, and arrays collapse to `items` when their "
        "elements share a shape (`anyOf` when they don't)."
    ),
    responses={
        **COMMON_ERRORS,
        400: {"model": ErrorResponse, "description": "The payload could not be converted to a schema"},
    },
)
async def generate_json_schema(payload: JsonInput):
    try:
        data = payload.data
        schema = generate_schema(data, name="JSONData")
        return {"schema": schema}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/explain",
    response_model=ExplainResponse,
    summary="Explain a JSON structure with AI",
    description=(
        "Sends the payload to the LLM provider and returns a **structured** "
        "explanation — summary, nesting depth, data types and the fields that "
        "look relevant. The model's answer is validated against "
        "`JsonExplanation` before being returned, so malformed AI output surfaces "
        "as a 502 instead of leaking to the client."
    ),
    responses={
        **COMMON_ERRORS,
        502: {"model": ErrorResponse, "description": "The AI failed or returned an unexpected format"},
    },
)
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

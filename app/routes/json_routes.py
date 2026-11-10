from fastapi import APIRouter, HTTPException, Request
from app.core.rate_limit import client_ip, explain_rate_limiter
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
        "Walks the object recursively and reports how many unique key paths it "
        "holds, the type of every path (dotted paths for nested keys, `[]` for "
        "objects inside arrays) and a type-only mirror of the structure. Every "
        "item of an array is inspected and its objects are merged; a path whose "
        "type varies is reported as a union such as `null | string`. Types use "
        "JSON names: `object`, `array`, `string`, `integer`, `number`, `boolean`, `null`."
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
        "Infers a draft-07 JSON Schema from the payload. Every top-level key is "
        "required. Objects inside an array are merged into a single item schema "
        "(keys missing from some objects become optional); other differing item "
        "types are listed in `anyOf`."
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
        "as a 502 instead of leaking to the client. "
        "**Rate limited** (it is the only endpoint that costs money): by default "
        "4 requests per minute and 40 per day per client IP, and 500 per day in "
        "total. Over the limit it returns 429 with a `Retry-After` header."
    ),
    responses={
        **COMMON_ERRORS,
        429: {"model": ErrorResponse, "description": "Rate limit reached; see the `Retry-After` header"},
        503: {"model": ErrorResponse, "description": "The rate-limit store (Redis) is unreachable; /explain fails closed"},
        502: {"model": ErrorResponse, "description": "The AI failed or returned an unexpected format"},
    },
)
async def explain_json_endpoint(payload: JsonInput, request: Request):
    """
    Receive a JSON, send it to Groq and return a structured explanation.

    Errors (RateLimitError -> 429, PayloadTooLargeError -> 413,
    AIResponseError -> 502) are handled by the global exception handlers
    registered in app.core.exceptions.
    """
    # Checked here, after the body has been validated: a malformed request
    # (422) doesn't use quota, and a rejected one never reaches Groq.
    explain_rate_limiter.check(client_ip(request))

    data = payload.data
    explanation = explain_json(data)

    logger.info(f"Explanation successful. Nesting levels: {explanation.nesting_levels}")
    return ExplainResponse(explanation=explanation)

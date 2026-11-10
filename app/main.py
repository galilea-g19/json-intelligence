import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.rate_limit import explain_rate_limiter
from app.routes.json_routes import router
from app.core.exceptions import register_error_handlers
from app.core.logging import setup_logging
from app.middleware.size_limit import BodySizeLimitMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware

# No load_dotenv(): pydantic-settings already reads .env (app.core.config).
setup_logging()
logger = logging.getLogger(__name__)


API_DESCRIPTION = """
Analyze, describe and transform JSON structures through a single API.

Deterministic logic handles what can be computed (**key counting, type detection,
JSON Schema generation**); an LLM handles what needs language
(**human-readable explanations**), and its output is validated with Pydantic
before it ever reaches the client.

### Quick start

1. Try any endpoint below with **Try it out**.
2. Or open the interactive demo UI at [`/ui/`](/ui/).

All endpoints take the same envelope — a top-level `data` object:

```json
{ "data": { "name": "Galilea", "skills": ["Python", "FastAPI"] } }
```
"""

TAGS_METADATA = [
    {
        "name": "json",
        "description": "Analyze, generate schemas from, and explain JSON payloads.",
    },
    {
        "name": "meta",
        "description": "Health and environment checks used by the demo UI and by deployments.",
    },
]

@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info(f"/explain rate-limit store: {explain_rate_limiter.store.name}")
    logger.info("Application startup complete. Ready to accept requests.")
    yield
    logger.info("Application shutting down.")


app = FastAPI(
    title="JSON Intelligence API",
    description=API_DESCRIPTION,
    version="2.0.0",
    contact={
        "name": "Galilea Granados",
        "url": "https://github.com/galilea-g19",
    },
    license_info={"name": "MIT"},
    openapi_tags=TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Global error handlers
register_error_handlers(app)
# Middleware to limit the request body size
app.add_middleware(BodySizeLimitMiddleware)
# Request logging (added last -> outermost middleware, logs everything)
app.add_middleware(RequestLoggingMiddleware)


@app.get(
    "/",
    tags=["meta"],
    summary="Health check",
    description="Liveness probe. Also points to the demo UI and the docs.",
)
def read_root():
    return {
        "message": "¡Hola, FastAPI está funcionando!",
        "ui": "/ui",
        "docs": "/docs",
    }


@app.get("/ui", include_in_schema=False)
def ui_index():
    """Convenience redirect so /ui resolves the demo UI with its relative assets."""
    return RedirectResponse(url="/ui/")


@app.get(
    "/test-env",
    tags=["meta"],
    summary="Environment check",
    description=(
        "Reports whether the AI provider keys are present, without ever "
        "returning the key itself. Disabled (404) when `ENVIRONMENT=production`."
    ),
    include_in_schema=not settings.is_production,
)
def test_env():
    # Even a 5-character preview is more than a public deployment should expose.
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not Found")

    def preview(secret) -> dict:
        if secret is None:
            return {"status": "No encontrada", "preview": None}
        value = secret.get_secret_value()
        return {"status": "Configurada", "preview": f"{value[:5]}..."}

    return {
        "groq_api_key": preview(settings.groq_api_key),
        "openai_api_key": preview(settings.openai_api_key),
    }


app.include_router(router, prefix="/api/v1/json", tags=["json"])

# Minimal demo UI (EPIC 5). Served by the API itself so the fetch calls
# in app/static/app.js are same-origin and need no CORS configuration.
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/ui", StaticFiles(directory=STATIC_DIR, html=True), name="ui")

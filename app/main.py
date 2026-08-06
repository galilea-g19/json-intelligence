import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from app.core.config import settings
from app.routes.json_routes import router
from app.core.exceptions import register_error_handlers
from app.core.logging import setup_logging
from app.middleware.size_limit import BodySizeLimitMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware

load_dotenv()
setup_logging()
logger = logging.getLogger(__name__)


app = FastAPI()
# Global error handlers
register_error_handlers(app)
# Middleware to limit the request body size
app.add_middleware(BodySizeLimitMiddleware)
# Request logging (added last -> outermost middleware, logs everything)
app.add_middleware(RequestLoggingMiddleware)

print(f"Valor de la key: {os.getenv('OPENAI_API_KEY')}")

@app.get("/")
def read_root():
    return {"message": "¡Hola, FastAPI está funcionando!"}

@app.get("/test-env")
def test_env():
    key_exists = bool(settings.openai_api_key.get_secret_value())
    key = os.getenv("OPENAI_API_KEY")
    if key_exists:
        return {"status": "Configurada", "preview": f"{key[:5]}..."}
    return {"status": "No encontrada", "preview": None}

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup complete. Ready to accept requests.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down.")

app.include_router(router, prefix="/api/v1/json")
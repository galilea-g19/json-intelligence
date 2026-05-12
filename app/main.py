import os
from dotenv import load_dotenv
from fastapi import FastAPI
from app.core.config import settings
from app.routes.json_routes import router

load_dotenv()
app = FastAPI()

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


app.include_router(router, prefix="/api/v1")
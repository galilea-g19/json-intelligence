import os
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()
app = FastAPI()

print(f"Valor de la key: {os.getenv('OPENAI_API_KEY')}")

@app.get("/")
def read_root():
    return {"message": "¡Hola, FastAPI está funcionando!"}

@app.get("/test-env")
def test_env():
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return {"status": "Configurada", "preview": f"{key[:5]}..."}
    return {"status": "No encontrada", "preview": None}
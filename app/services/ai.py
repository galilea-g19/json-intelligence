import os
import json
#from openai import OpenAI
from groq import Groq
from app.core.config import settings

MAX_JSON_SIZE_BYTES = 5000
MAX_JSON_SIZE_CHARS = 10000

_client: Groq | None = None

def get_client() -> Groq:
    """
    Crea el cliente de Groq la primera vez que se necesita (lazy).        
    """
    global _client
    if _client is None:
        if settings.groq_api_key is None:
            raise ValueError("GROQ_API_KEY no está configurada en el entorno (.env)")
        _client = Groq(api_key=settings.groq_api_key.get_secret_value())
    return _client

def explain_json(data: dict) -> str:
    json_str = json.dumps(data, indent=2, ensure_ascii=False)  

    if len(json_str.encode('utf-8')) > MAX_JSON_SIZE_BYTES:
        raise ValueError(f"El JSON excede el límite de {MAX_JSON_SIZE_BYTES} bytes. Resuma o reduzca los datos.")
    if len(json_str) > MAX_JSON_SIZE_CHARS:
        raise ValueError(f"El JSON excede el límite de {MAX_JSON_SIZE_CHARS} caracteres.")

    prompt = f"""
Eres un asistente experto en explicar estructuras de datos JSON.

A continuación se muestra un objeto JSON. Por favor, explica de forma clara y concisa:
- Cuál es la estructura general (objeto principal, anidaciones).
- Qué tipo de datos contiene (cadenas, números, booleanos, arreglos, objetos anidados).
- Si hay arreglos, indica qué tipo de elementos contienen.
- Si hay campos que parecen importantes, menciónalos.

Devuelve la respuesta en texto plano, con viñetas o párrafos cortos. No incluyas código JSON en la respuesta.

JSON:
{json_str}
"""
    try:
        client = get_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Eres un asisten técnico especializado en JSON"},
                {"role": "user", "content": prompt}
            ],
            temperature = 0.3,
            max_tokens = 500
        )
        explanation = response.choices[0].message.content.strip()

        if not explanation or len(explanation.strip()) == 0:
            raise ValueError("La AI devolvió una respuesta vacía")

        return explanation
    except Exception as e:
        raise Exception(f"Error to call AI groq: {str(e)}")

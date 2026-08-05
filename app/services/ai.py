import json
#from openai import OpenAI
from groq import Groq
from pydantic import ValidationError
from app.core.config import settings
from app.models.response_models import JsonExplanation

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

def explain_json(data: dict) -> JsonExplanation:
    json_str = json.dumps(data, indent=2, ensure_ascii=False)

    if len(json_str.encode('utf-8')) > MAX_JSON_SIZE_BYTES:
        raise ValueError(f"El JSON excede el límite de {MAX_JSON_SIZE_BYTES} bytes. Resuma o reduzca los datos.")
    if len(json_str) > MAX_JSON_SIZE_CHARS:
        raise ValueError(f"El JSON excede el límite de {MAX_JSON_SIZE_CHARS} caracteres.")

    prompt = f"""
Eres un asistente experto en explicar estructuras de datos JSON.

Analiza el siguiente objeto JSON y responde EXCLUSIVAMENTE con un objeto JSON
válido (sin texto adicional, sin markdown) que tenga exactamente estas claves:

- "summary": string. Explicación legible en lenguaje natural (2 a 4 frases) sobre
  la estructura general, los tipos de datos y qué contienen los arreglos.
- "nesting_levels": integer. Número de niveles de anidación del objeto.
- "data_types": array de strings. Tipos de datos presentes (ej: "string", "integer",
  "boolean", "array", "object", "null").
- "important_fields": array de strings. Nombres de los campos que parecen relevantes.

JSON a analizar:
{json_str}
"""
    try:
        client = get_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Eres un asistente técnico especializado en JSON que responde siempre en JSON válido."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        raw = response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Error to call AI groq: {str(e)}")

    if not raw or not raw.strip():
        raise Exception("La AI devolvió una respuesta vacía")

    # Validación del output de la IA con Pydantic (Issue #10)
    try:
        parsed = json.loads(raw)
        return JsonExplanation.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as e:
        raise Exception(f"La respuesta de la IA no cumple el formato esperado: {e}")

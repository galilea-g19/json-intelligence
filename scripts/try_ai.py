"""
Prueba manual de explain_json() contra la API REAL de Groq (consume créditos).

No es un test automatizado: vive fuera de tests/ para que pytest no lo recoja.
Ejecutar desde la raíz del proyecto:

    python -m scripts.try_ai
"""
from app.services.ai import explain_json

test_data = {
    "usuario": "Galilea",
    "edad": 30,
    "direccion": {
        "ciudad": "Guadajalara",
        "cp": 4100
    }
}

explanation = explain_json(test_data)
print("Explicacion: \n", explanation)

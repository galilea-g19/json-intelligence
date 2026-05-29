import asyncio
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
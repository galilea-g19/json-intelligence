# Propuesta: tests automatizados

Plan para cubrir con tests automatizados la API, los servicios y el manejo de
errores. Hoy el proyecto no tiene ninguno: `test_ai.py` es un script manual
que llama a Groq de verdad.

**Estado:** se implementa como **EPIC 7** (issues #19-#24, al final).

- ✅ **#19** Infraestructura: `pytest.ini`, `requirements-dev.txt`, `tests/conftest.py`,
  `test_ai.py` movido a `scripts/try_ai.py`.
- ✅ **#20** Unitarios de analyzer y schema generator: 47 tests + 3 `xfail`
  (AN-10, AN-11, SC-11), cobertura 100 % en ambos módulos.
- ⏳ #21-#24 pendientes.

---

## 1. Objetivos

1. **Proteger el contrato de la API:** forma de las respuestas, códigos HTTP y
   el formato único de error `{error, status_code, path}`.
2. **Verificar la lógica determinista** (`analyzer`, `schema_generator`) caso por
   caso, incluidos los bordes.
3. **Probar `/explain` sin llamar a Groq:** la respuesta del modelo se simula, así
   que los tests son gratis, rápidos y siempre dan el mismo resultado.
4. **Dejar documentados los bugs conocidos** como `xfail` para que no se olviden
   y para que avisen en cuanto se arreglen.
5. **Correr en CI** en cada push y en cada PR.

Fuera de alcance por ahora: tests de la interfaz (`app/static/`), carga y rendimiento.

---

## 2. Herramientas

| Herramienta | Para qué | Estado |
| --- | --- | --- |
| `pytest` | Ejecutor de tests | **Falta instalar** |
| `pytest-cov` | Cobertura | **Falta instalar** |
| `fastapi.testclient.TestClient` | Llamar a la API en memoria, sin servidor | Ya disponible |
| `httpx` | Lo usa `TestClient` por debajo | Ya instalado (0.28.1) |
| `unittest.mock` | Simular el cliente de Groq | Viene con Python |

Nuevo archivo `requirements-dev.txt`, para no mezclarlo con las dependencias de ejecución:

```txt
-r requirements.txt
pytest==8.*
pytest-cov==6.*
```

Configuración en `pytest.ini` (o en `pyproject.toml`):

```ini
[pytest]
testpaths = tests
addopts = -ra --strict-markers
markers =
    live: llama a la API real de Groq (requiere GROQ_API_KEY; no corre en CI)
```

> `testpaths = tests` es importante: sin esa línea, pytest recogería el
> `test_ai.py` de la raíz, que **llama a Groq en cuanto se importa**. Se propone
> además moverlo a `scripts/try_ai.py`.

---

## 3. Estructura

```
tests/
├── conftest.py                  # client, fake_groq, aislamiento de settings
├── unit/
│   ├── test_analyzer.py         # analyze_json()
│   ├── test_schema_generator.py # generate_schema()
│   └── test_ai_service.py       # explain_json() con Groq simulado
├── api/
│   ├── test_analyze_endpoint.py
│   ├── test_schema_endpoint.py
│   ├── test_explain_endpoint.py
│   ├── test_meta_endpoints.py   # /, /test-env, /ui
│   └── test_errors.py           # formato único de error, 404, 422, 500
├── middleware/
│   └── test_size_limit.py       # 413 por content-length y por body real
└── live/
    └── test_groq_live.py        # @pytest.mark.live — manual, opcional
```

Tres capas:

- **Unitarios:** funciones puras, sin FastAPI. Son la mayoría y los más rápidos.
- **API:** `TestClient` contra la app real, con el formato HTTP completo.
- **Live:** un solo test con Groq real, marcado `live` y excluido por defecto
  (`pytest -m live` para correrlo a mano).

---

## 4. Fixtures (`tests/conftest.py`)

```python
import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import app.services.ai as ai
from app.core.config import settings
from app.main import app


@pytest.fixture
def client():
    # raise_server_exceptions=False: deja que el handler genérico produzca el 500
    # en lugar de propagar la excepción al test.
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def no_real_groq(monkeypatch):
    """Ningún test puede llegar a Groq por accidente."""
    monkeypatch.setattr(ai, "_client", None)
    monkeypatch.setattr(settings, "groq_api_key", None)


@pytest.fixture
def fake_groq(monkeypatch):
    """Devuelve una función que configura lo que 'responde' el modelo."""
    def _set(content: str | None = None, *, raises: Exception | None = None):
        fake = MagicMock()
        create = fake.chat.completions.create
        if raises:
            create.side_effect = raises
        else:
            create.return_value.choices = [MagicMock(message=MagicMock(content=content))]
        monkeypatch.setattr(ai, "get_client", lambda: fake)
        return create  # para inspeccionar con qué se llamó
    return _set


@pytest.fixture
def valid_explanation() -> str:
    return json.dumps({
        "summary": "Un objeto con datos de usuario.",
        "nesting_levels": 2,
        "data_types": ["object", "string"],
        "important_fields": ["user.name"],
    })
```

**Aislamiento de logs:** `app/core/logging.py` crea `logs/` y abre
`logs/app.log` en el directorio actual **al importarse**, así que los tests
escriben en el log real. Para el primer paso basta con aceptarlo (está en
`.gitignore`). Mejora sugerida: leer la ruta del log desde `Settings` y
apuntarla a `tmp_path` en los tests.

---

## 5. Catálogo de casos

Prioridad: **P0** = imprescindible para el MVP de tests · **P1** = deseable · **P2** = extra.
Los casos marcados con 🐞 documentan un bug conocido y van como `xfail(strict=True)`.

### 5.1 `analyze_json()`: unitarios

| ID | Caso | Esperado | Prioridad |
| --- | --- | --- | --- |
| AN-01 | Objeto plano `{a:1, b:"x"}` | `total_keys_recursive=2`, tipos `int`/`str` | P0 |
| AN-02 | Objeto vacío `{}` | 0 claves, `key_types={}`, `structure={}` | P0 |
| AN-03 | Anidado `{b:{c:"x"}}` | ruta `b.c`, conteo incluye la clave anidada | P0 |
| AN-04 | Anidado en 3+ niveles | rutas `a.b.c.d` correctas | P1 |
| AN-05 | Arreglo de objetos `{l:[{n:1}]}` | ruta `l[].n`, `structure.l == [{n:"int"}]` | P0 |
| AN-06 | Arreglo de primitivos `[1,"a"]` | `structure == ["int","str"]` | P0 |
| AN-07 | Arreglo vacío | `structure.l == []`, sin error | P1 |
| AN-08 | `bool`, `None`, `float` | `bool`, `NoneType`, `float` (no confundir `bool` con `int`) | P1 |
| AN-09 | Arreglos dentro de arreglos `[[1,2]]` | no truena; documentar la salida actual | P2 |
| 🐞 AN-10 | `[{n:1},{n:2,m:true}]` | debería detectar `l[].m`; **hoy solo mira el primer elemento** | P0 |
| 🐞 AN-11 | Nombres de tipo | debería usar nombres JSON (`object`, `string`…) como `/schema`; **hoy usa los de Python** | P1 (requiere decisión) |

### 5.2 `generate_schema()`: unitarios

| ID | Caso | Esperado | Prioridad |
| --- | --- | --- | --- |
| SC-01 | Cabecera | `$schema` draft-07, `title`, `type:"object"` | P0 |
| SC-02 | Primitivos | `integer`, `number`, `boolean`, `null`, `string` | P0 |
| SC-03 | `True` es `boolean`, no `integer` | (`bool` hereda de `int` en Python) | P0 |
| SC-04 | `required` | todas las claves presentes, en orden | P0 |
| SC-05 | Objeto anidado | `properties` + `required` recursivos | P0 |
| SC-06 | Arreglo homogéneo | `items` con un único schema | P0 |
| SC-07 | Arreglo mixto `[1,"a",None]` | `items.anyOf` con 3 tipos, sin duplicados | P0 |
| SC-08 | Arreglo vacío | `items: {}` | P1 |
| SC-09 | **El schema generado valida el propio input** | `jsonschema.validate(data, schema)` pasa | P1 (añade `jsonschema` como dependencia de desarrollo) |
| SC-10 | Test con muchos datos generados (`hypothesis`): cualquier objeto JSON produce un schema que lo valida | sin excepciones | P2 |
| 🐞 SC-11 | `[{n:1},{n:2,m:true}]` | idealmente un solo objeto con `n` requerido y `m` opcional; **hoy son dos entradas en `anyOf`** | P2 (decisión de diseño) |

### 5.3 `explain_json()`: unitarios con Groq simulado

| ID | Caso | Esperado | Prioridad |
| --- | --- | --- | --- |
| AI-01 | Respuesta válida | devuelve `JsonExplanation` con los campos correctos | P0 |
| AI-02 | JSON > `max_ai_json_bytes` | `PayloadTooLargeError`, **sin llamar a Groq** | P0 |
| AI-03 | JSON > `max_ai_json_chars` (bajando el límite con `monkeypatch`) | `PayloadTooLargeError` | P1 |
| AI-04 | Límite en bytes con caracteres de varios bytes (`"ñ"*2600`) | cuenta bytes, no caracteres | P1 |
| AI-05 | La IA responde algo que no es JSON | `AIResponseError` | P0 |
| AI-06 | Respuesta vacía, `None` o solo espacios | `AIResponseError("...vacía")` | P0 |
| AI-07 | JSON con forma incorrecta (`nesting_levels:-1`, falta `summary`) | `AIResponseError` | P0 |
| AI-08 | El SDK lanza una excepción | `AIResponseError("Error al llamar a la IA...")` | P0 |
| AI-09 | Sin `GROQ_API_KEY` | `AIResponseError` al crear el cliente | P0 |
| AI-10 | Parámetros de la llamada | `model`, `temperature=0.3`, `max_tokens=500`, `response_format=json_object` y el JSON incluido en el prompt | P1 |
| AI-11 | El cliente se crea una sola vez | dos llamadas a `get_client()` devuelven el mismo objeto (parchando `Groq`) | P2 |

### 5.4 Endpoints

| ID | Caso | Esperado | Prioridad |
| --- | --- | --- | --- |
| EP-01 | `POST /analyze` válido | 200, claves `key_count`, `types`, `nested_structure` | P0 |
| EP-02 | `POST /schema` válido | 200, `{"schema": {...}}` (alias, no `json_schema`) | P0 |
| EP-03 | `POST /explain` con Groq simulado | 200, `{"explanation": {...}}` | P0 |
| EP-04 | `/explain` con salida inválida de la IA | 502 con el formato de error | P0 |
| EP-05 | `/explain` con JSON > 5 KB | 413 con el formato de error | P0 |
| EP-06 | Falta `data` (`{}`) | 422 con `error`, `details`, `path` | P0 |
| EP-07 | `data` es un arreglo / string / número | 422 | P0 |
| EP-08 | Body que no es JSON | 422 | P1 |
| EP-09 | `GET` en una ruta POST | 405 con el formato de error | P1 |
| EP-10 | Ruta inexistente | 404 `{error:"Not Found", status_code, path}` | P1 |
| EP-11 | `GET /` | 200, contiene `ui` y `docs` | P1 |
| EP-12 | `GET /ui` | 307 hacia `/ui/`; `GET /ui/` devuelve HTML | P1 |
| EP-13 | `GET /test-env` | **nunca** devuelve la clave completa, solo `preview` de 5 caracteres + `...` | P0 (seguridad) |
| EP-14 | `GET /openapi.json` | 200, contiene las 3 rutas y las respuestas 413/422/502 documentadas | P2 |
| 🐞 EP-15 | 502 por salida inválida de la IA | **hoy el mensaje incluye el error interno de Pydantic o del SDK**; debería ser genérico y dejar el detalle en el log | P1 |

### 5.5 Formato de error y handlers

| ID | Caso | Esperado | Prioridad |
| --- | --- | --- | --- |
| ER-01 | Para cada 404/405/413/502 | el body tiene exactamente `error`, `status_code`, `path` | P0 (test parametrizado) |
| ER-02 | 422 | `error="Invalid request"`, `details` es una lista | P0 |
| ER-03 | Excepción no controlada (ruta de prueba añadida solo en el test) | 500 con mensaje genérico, sin traza | P1 |
| ER-04 | El servicio lanza una excepción dentro de `/analyze` | 400 con `detail` | P2 |

### 5.6 Middleware

| ID | Caso | Esperado | Prioridad |
| --- | --- | --- | --- |
| MW-01 | `content-length` > 1 MB | 413 sin leer el body | P0 |
| MW-02 | Body > límite sin `content-length` (enviado por partes, con un generador) | 413 | P1 |
| MW-03 | Body justo en el límite | pasa (no 413) | P1 |
| MW-04 | Después del middleware el endpoint sigue pudiendo leer el body | 200 normal | P0 (lo cubren EP-01/02) |
| MW-05 | Límite configurable: `monkeypatch` de `settings.max_body_bytes=100` | 413 con un body de 101 bytes | P1 |
| MW-06 | El logging registra también los 413 (`caplog`) | aparece `POST ... -> 413` | P2 |

**Total:** unos 55 casos (26 P0). Por las pruebas manuales que hice, el MVP de
tests (P0) se puede escribir en 1 o 2 días.

---

## 6. Ejemplos

```python
# tests/unit/test_analyzer.py
import pytest
from app.services.analyzer import analyze_json


def test_nested_object_uses_dotted_paths():
    result = analyze_json({"b": {"c": "x"}})
    assert result["summary"]["key_types"] == {"b": "dict", "b.c": "str"}
    assert result["summary"]["total_keys_recursive"] == 2


@pytest.mark.xfail(strict=True, reason="BUG AN-10: solo analiza el primer elemento del arreglo")
def test_array_of_objects_merges_all_keys():
    result = analyze_json({"l": [{"n": 1}, {"n": 2, "m": True}]})
    assert "l[].m" in result["summary"]["key_types"]
```

```python
# tests/api/test_explain_endpoint.py
URL = "/api/v1/json/explain"


def test_explain_returns_validated_explanation(client, fake_groq, valid_explanation):
    create = fake_groq(valid_explanation)
    r = client.post(URL, json={"data": {"user": {"name": "Galilea"}}})
    assert r.status_code == 200
    assert r.json()["explanation"]["nesting_levels"] == 2
    assert create.call_args.kwargs["response_format"] == {"type": "json_object"}


def test_explain_rejects_malformed_ai_output(client, fake_groq):
    fake_groq('{"summary": "x", "nesting_levels": -1}')
    r = client.post(URL, json={"data": {"a": 1}})
    assert r.status_code == 502
    assert set(r.json()) == {"error", "status_code", "path"}


def test_explain_payload_too_large_never_calls_ai(client, fake_groq):
    create = fake_groq("{}")
    r = client.post(URL, json={"data": {"a": "x" * 6000}})
    assert r.status_code == 413
    create.assert_not_called()
```

```python
# tests/api/test_errors.py
import pytest


@pytest.mark.parametrize("method, url, expected", [
    ("get", "/no-existe", 404),
    ("get", "/api/v1/json/analyze", 405),
])
def test_error_envelope_is_uniform(client, method, url, expected):
    r = getattr(client, method)(url)
    assert r.status_code == expected
    assert set(r.json()) == {"error", "status_code", "path"}
    assert r.json()["path"] == url
```

---

## 7. CI

`.github/workflows/tests.yml`:

```yaml
name: Tests

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.14"]   # mínimo del README + versión de desarrollo
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - run: pip install -r requirements-dev.txt
      - run: pytest -m "not live" --cov=app --cov-report=term-missing --cov-fail-under=85
```

No necesita ningún secreto: Groq siempre está simulado. Se añade al README una
insignia con el estado de los tests.

### Objetivos de cobertura

| Módulo | Objetivo |
| --- | --- |
| `app/services/*` | ≥ 95 % |
| `app/core/exceptions.py`, `app/middleware/*` | ≥ 90 % |
| Total `app/` | ≥ 85 % (`--cov-fail-under`) |

---

## 8. EPIC 7: Tests automatizados

## Issue #19 — Infraestructura de tests

**Tareas**

- `requirements-dev.txt`, `pytest.ini`
- `tests/conftest.py` con `client`, `no_real_groq` y `fake_groq`
- Mover `test_ai.py` a `scripts/try_ai.py`

**DoD**

- `pytest` corre (con 0 tests) sin llamar a Groq

## Issue #20 — Tests unitarios de analyzer y schema generator

**Tareas**

- Casos AN-* y SC-* P0/P1
- Bugs AN-10 y AN-11 como `xfail(strict=True)`

**DoD**

- Cobertura de `app/services/analyzer.py` y `schema_generator.py` ≥ 95 %

## Issue #21 — Tests del servicio de IA (simulado)

**Tareas**

- Casos AI-01 a AI-10

**DoD**

- Ningún test necesita red ni `GROQ_API_KEY`

## Issue #22 — Tests de endpoints, errores y middleware

**Tareas**

- Casos EP-*, ER-*, MW-* P0/P1
- Test parametrizado del formato de error

**DoD**

- Todos los códigos documentados en el README (400, 413, 422, 502, 500) tienen al menos un test

## Issue #23 — CI con GitHub Actions

**Tareas**

- `tests.yml` con matriz 3.11 / 3.14 y `--cov-fail-under=85`
- Insignia en el README; quitar "Automated test suite" del roadmap

**DoD**

- Los PR muestran el check verde o rojo

## Issue #24 — Corregir los bugs detectados

**Tareas**

- AN-10: recorrer todos los elementos del arreglo y unir las claves
- EP-15: mensaje 502 genérico; el detalle va solo al log
- Decidir AN-11 (nombres de tipos) y SC-11 (unir objetos en `anyOf`)

**DoD**

- Los `xfail` correspondientes pasan a tests normales en verde

### Orden recomendado

1. #19 → infraestructura
2. #20 → lógica determinista (lo más valioso con menos esfuerzo)
3. #21 + #22 → IA y API
4. #23 → CI
5. #24 → bugs, ya con red de seguridad

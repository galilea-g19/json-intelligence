# Backlog

Original planning board for the project: epics, issues and the recommended
order in which they were tackled. Kept out of the README so the README can
stay a product/usage document.

**Status:** EPIC 1-7 done (EPIC 7, automated tests: see [TESTING.md](./TESTING.md)). EPIC 8 (production readiness) in progress.

---

# 📌 EPIC 1 — Setup backend (FastAPI)

## Issue #1 — Initialize FastAPI project

**Descripción**

Crear base del proyecto en Python

**Tareas**

- Crear entorno virtual
- Instalar:
  - fastapi
  - uvicorn
- Crear estructura:

```
/app
  main.py
  /routes
  /services
  /models
```

**DoD**

- Server corre con:

```
uvicorn app.main:app--reload
```

## Issue #2 — Environment configuration

**Descripción**

Manejo de variables de entorno

**Tareas**

- Instalar `python-dotenv`
- Crear `.env`
- Variables:
  - OPENAI_API_KEY
- Cargar config en app

**DoD**

- App lee variables correctamente

## Issue #3 — Request validation with Pydantic

**Descripción**

Validar inputs de la API

**Tareas**

- Crear modelo base:

```
classJsonInput(BaseModel):json:dict
```

**DoD**

- Requests inválidos fallan correctamente

# 📌 EPIC 2 — Core JSON Logic

## Issue #4 — Implement JSON analyzer service

**Descripción**

Analizar estructura del JSON

**Tareas**

- Contar keys
- Detectar tipos
- Soportar nested objects

**DoD**

- Función devuelve:
  - resumen
  - estructura

## Issue #5 — Create `/analyze` endpoint

**Descripción**

```
POST /api/v1/json/analyze
```

**DoD**

- Endpoint funcional con respuesta clara

## Issue #6 — Implement schema generator

**Descripción**

Generar JSON Schema

**Tareas**

- Mapear tipos
- Detectar required fields
- Soportar nested

## Issue #7 — Create `/schema` endpoint

**DoD**

- Endpoint responde correctamente

# 📌 EPIC 3 — AI Integration

## Issue #8 — Setup AI service

**Descripción**

Servicio para llamadas a AI

**Tareas**

- Crear `ai_service.py`
- Función:
  - recibe JSON
  - retorna explicación estructurada

## Issue #9 — Implement `/explain` endpoint

```
POST /api/v1/json/explain
```

**Tareas**

- Prompt estructurado
- Limitar tamaño JSON

**DoD**

- Output consistente

## Issue #10 — Validate AI response

**Descripción**

- Validar output con Pydantic

# 📌 EPIC 4 — Backend quality (nivel entrevista)

## Issue #11 — Error handling

Manejo global de errores

## Issue #12 — Logging

Logs básicos

## Issue #13 — Input size limits

Evitar JSON enormes

# 📌 EPIC 5 — Minimal UI (solo demo)

> **Implementado.** UI en `app/static/` (`index.html` + `styles.css` + `app.js`),
> servida por la propia API en **http://127.0.0.1:8000/ui/**.
>
> Al servirse desde el mismo origen que la API, los `fetch` no necesitan CORS.
>
> ```bash
> uvicorn app.main:app --reload   # UI: /ui/   ·   Swagger: /docs
> ```

## Issue #14 — Create simple UI page

**Descripción**

UI básica (puede ser HTML simple)

**Tareas**

- Textarea
- Botones:
  - Analyze
  - Schema
  - Explain

## Issue #15 — Connect UI to API

**Tareas**

- fetch a endpoints
- mostrar resultados

## Issue #16 — Basic styling

**Descripción**

- Layout limpio
- readable JSON output

# 📌 EPIC 6 — Developer Experience

## Issue #17 — Swagger docs

👉 FastAPI ya lo da (`/docs`)

## Issue #18 — README profesional

**Descripción**

- Problem
- Solution
- API endpoints
- Tech decisions
- endpoints
- decisiones técnicas
- cómo correr proyecto

# 📌 EPIC 7 — Tests automatizados

> **Completada.** Plan, catálogo de casos e issues #19-#24 en
> [TESTING.md](./TESTING.md). 148 tests, 99 % de cobertura, CI en GitHub Actions.

# 📌 EPIC 8 — Production readiness

**Objetivo:** pasar de "funciona en mi máquina" a "se puede probar en esta URL",
sin que una demo pública ponga en riesgo los créditos de Groq.

## Issue #25 — Deuda técnica ✅

**Descripción**

Pendientes detectados en la revisión del código que no son bugs funcionales.

**Tareas**

- Sacar `logs/app.log` del repo (`git rm --cached`); `logs/` ya está en `.gitignore`
- Reemplazar APIs obsoletas (los 6 warnings de pytest):
  - `@app.on_event` → `lifespan`
  - `class Config` (Pydantic v1) → `model_config`
  - `HTTP_422_UNPROCESSABLE_ENTITY` → `HTTP_422_UNPROCESSABLE_CONTENT`
- `/test-env`: devolver 404 cuando `ENVIRONMENT=production`
- OpenAPI `contact`: GitHub en lugar del email personal
- Quitar campos que nunca se rellenan en `analyze_json` (`max_depth`, `array_count`, `list_count`)
- Quitar `load_dotenv()` redundante (pydantic-settings ya lee `.env`)
- README: URL real del repo en lugar de `<repo-url>`

**DoD**

- `pytest` corre sin warnings
- Tests nuevos para `/test-env` en producción y para el `lifespan`
- Cobertura ≥ 95 % (CI en verde)

**Resultado:** hecho. 154 tests, 0 warnings en Python 3.11 y 3.14, cobertura 99 %.
Extra: se fijaron `starlette` y `anyio` en `requirements.txt` — FastAPI solo
declara un rango, y una instalación limpia (como la del CI) traía versiones más
nuevas que generaban warnings de deprecación.

## Issue #26 — Docker image ✅

**Tareas**

- `Dockerfile` multi-stage, imagen `python:3.x-slim`, usuario no-root
- `.dockerignore` (`.venv`, `.env`, `logs/`, `tests/`, `.git`)
- `HEALTHCHECK` contra `/`
- Documentar `docker build` / `docker run --env-file .env -p 8000:8000`

**DoD**

- `docker run` levanta la API y la UI en `http://localhost:8000/ui/`

**Resultado:** `Dockerfile` (multi-stage, `python:3.14-slim`, usuario no-root,
`HEALTHCHECK`, `$PORT`), `.dockerignore`, `compose.yaml` y documentación en el
README. Extra: job `docker` en el CI que construye la imagen, espera a que esté
`healthy` y hace un smoke test (`/`, `/ui/`, `/analyze`, `/schema`, `/test-env`
→ 404, usuario no-root). Todas las dependencias tienen wheel para Linux/3.14,
así que la imagen no necesita compilador (`--only-binary=:all:`).

## Issue #27 — Rate limiting en `/explain`

**Descripción**

`/explain` es el único endpoint con costo (Groq). En una demo pública hay que
limitarlo por IP para que nadie agote los créditos.

**Tareas**

- Límite por IP configurable desde `Settings` (ej. `5/minuto`, `50/día`)
- Respuesta `429` con el mismo envelope de error y header `Retry-After`
- `/analyze` y `/schema` sin límite estricto (son deterministas y gratis)
- Tests del 429

**DoD**

- Superar el límite devuelve 429 sin llamar a Groq

## Issue #28 — Deploy de la demo

**Tareas**

- Elegir plataforma (Render / Fly.io / Railway) a partir de la imagen de #26
- `GROQ_API_KEY` y `ENVIRONMENT=production` como secretos de la plataforma
- Logs a stdout en producción (el filesystem del contenedor es efímero)
- URL de la demo en el README (UI + `/docs`)

**DoD**

- La UI y Swagger responden en una URL pública
- `/test-env` devuelve 404 en esa URL

## Orden EPIC 8

1. ✅ #25 → deuda técnica (base limpia)
2. ✅ #26 → Docker
3. #27 → rate limiting (**antes** de publicar)
4. #28 → deploy

# 🔧 Mantenimiento planificado

Actualizaciones que **no son deuda técnica**: lo que hay hoy es correcto y
tiene soporte. Se hacen cuando se cumple su condición de inicio, no antes.

## Issue #29 — Actualizar a Python 3.15

**Contexto**

El proyecto usa **Python 3.14** (desarrollo, CI e imagen Docker), con soporte
hasta octubre de 2030. **3.15** salió el 9 de octubre de 2026.

Hoy (noviembre 2026) no es viable: `pydantic==2.13.4` exige
`pydantic-core==2.46.4`, que **no tiene wheel para 3.15** (empiezan en 2.48).
Con `--only-binary=:all:` en el `Dockerfile`, la imagen no se construiría.

**Condición de inicio**

- Pydantic, FastAPI y el resto de dependencias tienen wheels Linux para 3.15
  en versiones estables, y
- 3.15 tiene al menos un par de parches (≥ 3.15.3) sin regresiones conocidas
  en el ecosistema.

**Tareas**

- Actualizar `pydantic` / `pydantic-core` (y `fastapi`, `starlette`, `anyio`
  si hace falta) en `requirements.txt`
- Verificar wheels para Linux / cp315:
  `pip download -r requirements.txt --platform manylinux2014_x86_64 --python-version 3.15 --only-binary=:all:`
- Añadir 3.15 a la matriz del CI (mantener 3.11 como mínimo soportado)
- `Dockerfile`: `ARG PYTHON_VERSION=3.15`
- Actualizar el README (requisitos, tabla de Docker)

**DoD**

- 154+ tests en verde en 3.11 y 3.15, sin warnings
- El job `docker` del CI construye la imagen 3.15 y pasa el smoke test

# 🧠 Orden recomendado (muy importante)

NO los hagas en orden lineal.

👉 IMPORTANTE:

1. #1–3 → setup
2. #4–5 → `/analyze` 💥
3. #6–7 → schema
4. #8–9 → AI
5. #14–15 → UI
6. resto → mejoras

# 🔥 MVP real

Con esto ya puedes aplicar:

- `/analyze`
- `/schema`
- `/explain`
- UI simple

# 🚀 Cómo presentarlo

- demo con UI
- explicar endpoints
- mencionar decisiones técnicas

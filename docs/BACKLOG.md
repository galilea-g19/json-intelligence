# Backlog

Original planning board for the project: epics, issues and the recommended
order in which they were tackled. Kept out of the README so the README can
stay a product/usage document.

**Status:** EPIC 1-6 done.

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

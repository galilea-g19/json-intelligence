# json-intelligence

API to parse and transform JSON, combining deterministic logic with AI to generate structured explanations and schemas.

- OpenAI API _(or compatible LLM provider)_

### Frontend (minimal demo UI)

- HTML/CSS/JavaScript or lightweight frontend layer

# Example Features

### Analyze JSON

Returns:

- key count
- type detection
- nested structure analysis

### Generate Schema

Creates a valid JSON Schema automatically from input data.

### Explain JSON (AI)

Uses AI to generate human-readable explanations of structured data.

# Long-Term Vision

Potential future improvements include:

- authentication
- saved analyses
- schema export
- advanced transformations
- AI-powered recommendations
- SDK/package integration
- SaaS version for teams and developers

### Dev mood

> uvicorn app.main:app --reload

**JSON Intelligence API** is a backend-focused developer tool designed to analyze, explain, and transform JSON structures through a combination of deterministic logic and AI-assisted processing.

The project was created as part of a personal initiative to build practical tools for developers while strengthening backend engineering and AI integration skills.

# What does it do?

The system allows developers to:

- Analyze JSON structures dynamically
- Detect data types and nested relationships
- Generate JSON Schema automatically
- Explain JSON structures using AI
- Validate and process structured data through a clean API

A lightweight interactive UI is included for demonstration purposes, but the core of the project is the backend architecture and API design.

# Main Goals

- Practice backend-focused architecture using Python and FastAPI
- Explore AI integration in real-world developer tooling
- Design scalable and structured APIs
- Build a portfolio project that demonstrates:
  - data processing
  - API design
  - validation
  - AI-assisted workflows
  - clean backend organization

# Tech Stack

### Backend

- Python
- FastAPI
- Pydantic
- Uvicorn

### AI Integration

- OpenAI API _(or compatible LLM provider)_

### Frontend (minimal demo UI)

- HTML/CSS/JavaScript or lightweight frontend layer

# Example Features

### Analyze JSON

Returns:

- key count
- type detection
- nested structure analysis

### Generate Schema

Creates a valid JSON Schema automatically from input data.

### Explain JSON (AI)

Uses AI to generate human-readable explanations of structured data.

# Why this project matters

This project is not intended to be just another JSON viewer.

It is designed to demonstrate:

- backend problem-solving
- API-first thinking
- structured AI integration
- developer tooling concepts
- scalable service design

---

# Long-Term Vision

Potential future improvements include:

- authentication
- saved analyses
- schema export
- advanced transformations
- AI-powered recommendations
- SDK/package integration
- SaaS version for teams and developers

# 📌 EPIC 1 — Setup backend (FastAPI)

## 🟢 Issue #1 — Initialize FastAPI project

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

## 🟢 Issue #2 — Environment configuration

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

## 🟢 Issue #3 — Request validation with Pydantic

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

## 🟢 Issue #4 — Implement JSON analyzer service

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

## 🟢 Issue #5 — Create `/analyze` endpoint

**Descripción**

```
POST /api/v1/json/analyze
```

**DoD**

- Endpoint funcional con respuesta clara

## 🟢 Issue #6 — Implement schema generator

**Descripción**

Generar JSON Schema

**Tareas**

- Mapear tipos
- Detectar required fields
- Soportar nested

## 🟢 Issue #7 — Create `/schema` endpoint

**DoD**

- Endpoint responde correctamente

# 📌 EPIC 3 — AI Integration

## 🟢 Issue #8 — Setup AI service

**Descripción**

Servicio para llamadas a AI

**Tareas**

- Crear `ai_service.py`
- Función:
  - recibe JSON
  - retorna explicación estructurada

## 🟢 Issue #9 — Implement `/explain` endpoint

```
POST /api/v1/json/explain
```

**Tareas**

- Prompt estructurado
- Limitar tamaño JSON

**DoD**

- Output consistente

## 🟢 Issue #10 — Validate AI response

**Descripción**

- Validar output con Pydantic

# 📌 EPIC 4 — Backend quality (nivel entrevista)

## 🟢 Issue #11 — Error handling

Manejo global de errores

## 🟢 Issue #12 — Logging

Logs básicos

## 🟢 Issue #13 — Input size limits

Evitar JSON enormes

# 📌 EPIC 5 — Minimal UI (solo demo)

## 🟡 Issue #14 — Create simple UI page

**Descripción**

UI básica (puede ser HTML simple)

**Tareas**

- Textarea
- Botones:
  - Analyze
  - Schema
  - Explain

## 🟡 Issue #15 — Connect UI to API

**Tareas**

- fetch a endpoints
- mostrar resultados

## 🟡 Issue #16 — Basic styling

**Descripción**

- Layout limpio
- readable JSON output

# 📌 EPIC 6 — Developer Experience

## 🟡 Issue #17 — Swagger docs

👉 FastAPI ya lo da (`/docs`)

## 🟡 Issue #18 — README profesional

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

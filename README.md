# JSON Intelligence API

**A backend-focused developer tool that analyzes, explains and transforms JSON structures — combining deterministic logic with AI-assisted processing.**

FastAPI · Pydantic · Groq (LLM) · vanilla JS demo UI

---

## The problem

JSON is the format every backend speaks, but understanding an unfamiliar payload is still manual work: counting keys, tracing nested paths, writing a schema by hand, and explaining the shape to whoever consumes the API.

Generic online JSON viewers pretty-print the data and stop there. They don't tell you *what the structure is*, and pasting production-shaped payloads into a random website isn't something you want to make a habit of.

## The solution

One API that answers three different questions about the same payload:

| Question | Endpoint | How it's answered |
| --- | --- | --- |
| *What's in here?* | `POST /api/v1/json/analyze` | Deterministic recursive walk |
| *What contract does it follow?* | `POST /api/v1/json/schema` | Deterministic draft-07 inference |
| *What does it mean?* | `POST /api/v1/json/explain` | LLM, with the answer validated by Pydantic |

The split is the point: **anything that can be computed is computed.** The model is only asked for the part that genuinely needs language, and even then its output has to satisfy a Pydantic model before it reaches the client.

A minimal UI is bundled for demos, but the core of the project is the API design.

![Endpoints](https://img.shields.io/badge/endpoints-3-4fa3ff) ![Python](https://img.shields.io/badge/python-3.11%2B-4fa3ff) ![License](https://img.shields.io/badge/license-MIT-4fa3ff)

---

## Features

### Analyze JSON

Recursive walk over the object. Returns the total key count, the type of every key using **dotted paths** (`user.address.city`, `projects[].name` for objects inside arrays) and a type-only mirror of the structure.

### Generate Schema

Infers a valid **JSON Schema draft-07** from a sample payload: nested objects, arrays with a single item shape (`items`) or mixed shapes (`anyOf`), and `required` derived from the keys present.

### Explain JSON (AI)

Sends the payload to the LLM and returns a **structured** explanation — not a blob of prose: `summary`, `nesting_levels`, `data_types[]` and `important_fields[]`, validated with Pydantic before returning.

### Demo UI

Split-pane page at `/ui/`: editor on the left with live JSON validation and a byte counter, tabbed results on the right, one button per endpoint.

---

## Running locally (development)

### Requirements

- **Python 3.11+** (developed on 3.14)
- A **Groq API key** — free at [console.groq.com](https://console.groq.com/keys). Only needed for `/explain`; `/analyze` and `/schema` run offline.

### 1. Clone and enter the project

```bash
git clone <repo-url>
cd json-intelligence
```

### 2. Create the virtual environment

```bash
python -m venv .venv
```

Activate it:

| Shell | Command |
| --- | --- |
| PowerShell | `.venv\Scripts\Activate.ps1` |
| CMD | `.venv\Scripts\activate.bat` |
| Git Bash / WSL / macOS / Linux | `source .venv/bin/activate` (Windows: `source .venv/Scripts/activate`) |

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the environment

Create a `.env` file in the project root:

```env
GROQ_API_KEY=gsk_your_key_here
```

Optional overrides (defaults shown):

```env
MAX_BODY_BYTES=1048576      # 1 MB — max size of any request body
MAX_AI_JSON_BYTES=5000      # max size of the JSON forwarded to the LLM
MAX_AI_JSON_CHARS=10000     # same limit, counted in characters
```

`.env` is git-ignored. Nothing else needs configuring — there is no database.

### 5. Run the server

```bash
uvicorn app.main:app --reload
```

`--reload` restarts the server on every file change; drop it for a production-like run.

### 6. Open it

| What | URL |
| --- | --- |
| **Demo UI** | <http://127.0.0.1:8000/ui/> |
| **Swagger UI** | <http://127.0.0.1:8000/docs> |
| **ReDoc** | <http://127.0.0.1:8000/redoc> |
| **OpenAPI schema** | <http://127.0.0.1:8000/openapi.json> |
| Health check | <http://127.0.0.1:8000/> |
| Key check | <http://127.0.0.1:8000/test-env> |

### 7. Smoke-test from the terminal

```bash
curl -X POST http://127.0.0.1:8000/api/v1/json/analyze \
  -H "Content-Type: application/json" \
  -d '{"data":{"name":"Galilea","skills":["Python","FastAPI"]}}'
```

Requests and responses are logged to stdout and to `logs/app.log`:

```
2026-08-18 19:22:31 - app.request - INFO - POST /api/v1/json/analyze -> 200 (4 ms)
```

### Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `ModuleNotFoundError: No module named 'app'` | Run `uvicorn` from the project root, not from `app/` |
| UI shows **API offline** | The server isn't running, or you opened `index.html` from disk instead of `/ui/` |
| `/explain` returns **502** | `GROQ_API_KEY` missing/invalid, or the configured model is unavailable for your account (`app/services/ai.py`) |
| `/explain` returns **413** | The payload is over `MAX_AI_JSON_BYTES` — the LLM limit is deliberately stricter than the HTTP one |
| Port already in use | `uvicorn app.main:app --port 8001` |

---

## API reference

Base URL: `http://127.0.0.1:8000/api/v1/json`

Every endpoint takes the same envelope — a top-level `data` **object** (not an array):

```json
{ "data": { "user": { "name": "Galilea", "age": 30 }, "skills": ["Python"] } }
```

### `POST /analyze`

```json
{
  "key_count": 4,
  "types": {
    "user": "dict",
    "user.name": "str",
    "user.age": "int",
    "skills": "list"
  },
  "nested_structure": {
    "user": { "name": "str", "age": "int" },
    "skills": ["str"]
  }
}
```

### `POST /schema`

```json
{
  "schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "JSONData",
    "type": "object",
    "properties": {
      "user": {
        "type": "object",
        "properties": {
          "name": { "type": "string" },
          "age": { "type": "integer" }
        },
        "required": ["name", "age"]
      },
      "skills": { "type": "array", "items": { "type": "string" } }
    },
    "required": ["user", "skills"]
  }
}
```

### `POST /explain`

```json
{
  "explanation": {
    "summary": "An object describing a user and their skills…",
    "nesting_levels": 2,
    "data_types": ["object", "string", "integer", "array"],
    "important_fields": ["user.name", "skills"]
  }
}
```

### Errors

Every failure returns the same envelope:

```json
{ "error": "Payload too large", "status_code": 413, "path": "/api/v1/json/explain" }
```

| Status | When |
| --- | --- |
| `400` | The payload couldn't be processed by the analyzer/generator |
| `413` | Body over `MAX_BODY_BYTES`, or JSON over the stricter AI limit |
| `422` | `data` missing, or not a JSON object — includes a `details` array |
| `502` | The AI call failed or returned a shape that doesn't match `JsonExplanation` |
| `500` | Unexpected error (details hidden unless the app runs in debug) |

---

## Tech stack

| Layer | Choice |
| --- | --- |
| API | FastAPI (Starlette + Pydantic v2) |
| Validation | Pydantic models on both the request and the AI response |
| AI | Groq (`llama-3.3-70b-versatile`) with JSON mode |
| Config | `pydantic-settings` + `.env` |
| Server | Uvicorn |
| UI | Vanilla HTML/CSS/JS, no build step |
| Docs | OpenAPI / Swagger UI / ReDoc, generated from the code |

---

## Technical decisions

**Deterministic first, AI second.** Key counting, type detection and schema inference are pure Python — reproducible, instant and free. The LLM is reserved for natural language. It also means two thirds of the API keeps working with no API key at all.

**The AI response is validated like any other input.** `explain_json()` requests JSON mode and then runs `JsonExplanation.model_validate()` on the answer. A model that hallucinates a different shape produces a clean `502`, never a malformed `200`.

**Two size limits, not one.** `BodySizeLimitMiddleware` rejects oversized HTTP bodies (1 MB) before they're parsed; a stricter limit (5 KB) guards what gets forwarded to the LLM, where payload size means cost and latency. Both live in `Settings` as a single source of truth.

**A single error envelope.** Handlers registered in `app/core/exceptions.py` normalize `AppError`, `HTTPException` and validation errors into `{error, status_code, path}`, so clients — including the bundled UI — parse one shape.

**Errors as domain exceptions.** Services raise `PayloadTooLargeError` / `AIResponseError` and never import FastAPI. HTTP status codes are attached at the boundary, which keeps the services testable and framework-agnostic.

**Middleware ordering is intentional.** Request logging is added last so it wraps everything, including rejections from the size limit — a request refused with 413 still shows up in the log.

**The UI is served by the API.** Static files are mounted at `/ui`, so the demo's `fetch` calls are same-origin and the project needs no CORS configuration to be demoable.

**Versioned routes from day one.** Everything lives under `/api/v1/json`, so a v2 can coexist rather than break clients.

---

## Project structure

```
json-intelligence/
├── app/
│   ├── main.py                     # App factory, OpenAPI metadata, meta routes, /ui mount
│   ├── core/
│   │   ├── config.py               # Settings (.env) — keys and size limits
│   │   ├── exceptions.py           # Domain errors + global handlers
│   │   └── logging.py              # Console + file logging setup
│   ├── middleware/
│   │   ├── size_limit.py           # Rejects bodies over the limit (413)
│   │   └── request_logging.py      # method, path, status, duration
│   ├── models/
│   │   ├── request_models.py       # JsonInput
│   │   └── response_models.py      # Analysis / Schema / Explain / Error
│   ├── routes/
│   │   └── json_routes.py          # /analyze, /schema, /explain
│   ├── services/
│   │   ├── analyzer.py             # Recursive structure analysis
│   │   ├── schema_generator.py     # JSON Schema draft-07 inference
│   │   └── ai.py                   # Groq client, prompt, response validation
│   └── static/                     # Demo UI (index.html, styles.css, app.js)
├── docs/BACKLOG.md                 # Epics and issues this project was built from
├── logs/app.log                    # Runtime log (created on first run)
├── requirements.txt
└── README.md
```

---

## Roadmap

- Automated test suite (`pytest` + `httpx`) over the three endpoints and the error envelope
- Docker image for one-command runs
- Schema export (download `.json`) from the UI
- Rate limiting and authentication
- Saved analyses and history
- Advanced transformations and AI-powered recommendations

---

## Author

Built by **Galilea Granados**. Backend architecture, API design and structured AI integration.

License: MIT

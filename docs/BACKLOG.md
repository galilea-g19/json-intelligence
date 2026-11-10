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

## Issue #27 — Rate limiting en `/explain` ✅

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

**Resultado:** limitador propio de ventana deslizante en memoria
(`app/core/rate_limit.py`, sin dependencias nuevas).

- Decisiones: **4/minuto y 40/día por IP**, **tope global de 500/día**,
  implementación propia, contadores en memoria (una instancia; Redis si hubiera varias)
- 429 con el envelope de error y `Retry-After` en segundos (redondeado hacia arriba)
- Una petición rechazada no consume cuota ni llega a Groq; una inválida (422)
  tampoco cuenta; un intento válido cuenta aunque Groq falle
- `FORWARDED_ALLOW_IPS="*"` en el `Dockerfile` para leer la IP real detrás del proxy
- 32 tests nuevos (reloj simulado) + paso en el job `docker` del CI que verifica
  el 429 y la cuota por IP vía `X-Forwarded-For` dentro del contenedor

## Issue #30 — Rate limiting con contadores en Redis ✅

**Contexto**

Plataforma elegida para la demo: **Vercel** (ya aloja el portafolio `porfile`
y el proyecto `json-intelligence` está conectado al repo). En Vercel la API
corre como funciones que escalan a **varias instancias** y se apagan cuando no
hay tráfico, así que los contadores en memoria de #27 no sirven: cada instancia
contaría por su cuenta (con 3 instancias, 12/min en vez de 4, y el tope global
×3) y se reiniciarían al apagarse.

**Tareas**

- Backend de contadores en **Redis** (Vercel Marketplace, p. ej. Upstash, plan
  gratuito) con la misma ventana deslizante: sorted sets por clave y operación
  atómica (pipeline/`MULTI` o script Lua) para que dos peticiones simultáneas
  no se cuelen
- Selección automática: Redis si hay URL de conexión configurada; si no,
  memoria (desarrollo local, Docker, tests)
- Si Redis no responde: decidir y documentar el comportamiento (recomendado:
  **fail-closed** en `/explain` → 503, porque protege el presupuesto de Groq)
- Misma API pública: `check(ip)`, 429 + `Retry-After`, mismos mensajes
- Tests: los actuales siguen pasando con memoria; tests del backend Redis con
  un fake (`fakeredis`) y el reloj simulado
- Documentar la variable de conexión en README y `compose.yaml`

**DoD**

- Con Redis configurado, el límite se respeta aunque haya varias instancias
- Sin Redis, todo funciona como hoy (186+ tests en verde, CI en verde)

**Resultado:**

- Redis: **Upstash for Redis** (plan Free, 500 000 comandos/mes) desde el
  Marketplace de Vercel, región `us-east-1`, conectado a Production y Preview
  (no a Development: en local se usa memoria). Variable usada: `REDIS_URL`
- Cliente `redis` (redis-py) en lugar del SDK REST de Upstash: estándar, sin
  atarse al proveedor, testeable con `fakeredis`
- Almacenes intercambiables (`MemoryStore` / `RedisStore`) con la misma
  ventana deslizante; en Redis, un **script Lua atómico** por petición
- **Fail-closed**: si Redis no responde → 503 en `/explain`, rápido (1
  reintento como máximo; redis-py reintentaba varias veces por defecto)
- **Caché local de bloqueos**: una IP rechazada no vuelve a consultar Redis
  hasta su `Retry-After` (protege la cuota de comandos ante abuso)
- Tests: todos los del limitador corren contra memoria **y** Redis
  (`fakeredis[lua]`), más tests de instancias compartidas, 503 y caché.
  226 tests, 100 % de cobertura en `rate_limit.py`
- CI: dos contenedores de la API contra un **Redis real** comparten el límite;
  con Redis apagado, `/explain` da 503 en pocos segundos y `/analyze` sigue en 200

## Issue #28 — Deploy de la demo en Vercel

**Contexto**

Plataforma: **Vercel**. Estado actual (nov. 2026): el proyecto existe y se
despliega en cada push a `main`, pero está configurado **sin framework**, así
que Vercel lo trata como sitio estático: `https://json-intelligence.vercel.app/`
muestra el HTML de la UI y todo lo demás (`/ui/`, `/docs`, `/api/v1/json/*`)
da 404. La API de Python no se ejecuta.

**Tareas**

- Configurar el proyecto para ejecutar la API: preset **FastAPI** nativo o
  runtime **`container`** con el `Dockerfile` de #26 (decidir al empezar)
- Variables de entorno en Vercel: `GROQ_API_KEY`, `ENVIRONMENT=production` y
  la conexión a Redis de #30
- Logs a stdout en producción (en Vercel no hay `logs/app.log` persistente)
- Revisar la IP del cliente detrás del proxy de Vercel para el rate limiting
- Verificar en la URL pública: `/ui/`, `/docs`, los 3 endpoints, `/test-env`
  → 404, y el 429 de `/explain`
- URL de la demo en el README; enlazarla desde el portafolio (`porfile`)

**DoD**

- La UI y Swagger responden en `https://json-intelligence.vercel.app`
- `/analyze` y `/schema` responden 200; `/explain` responde con la API key real
- `/test-env` devuelve 404 y el rate limit funciona en producción

## Orden EPIC 8

1. ✅ #25 → deuda técnica (base limpia)
2. ✅ #26 → Docker
3. ✅ #27 → rate limiting (**antes** de publicar)
4. ✅ #30 → contadores del rate limiting en Redis (requisito de Vercel)
5. #28 → deploy en Vercel

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

# JSON Intelligence API — production image.
#
#   docker build -t json-intelligence .
#   docker run --env-file .env -p 8000:8000 json-intelligence
#
# Two stages: the builder installs the dependencies into a virtualenv, and the
# runtime stage copies only that virtualenv and the app code, so pip, its cache
# and the build layers never reach the final image.

ARG PYTHON_VERSION=3.14

# ---------------------------------------------------------------------------
# Stage 1 — builder: install dependencies into /opt/venv
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copied on its own so this layer is cached until requirements.txt changes.
COPY requirements.txt .
# --only-binary: every dependency ships a prebuilt wheel for this Python, so no
# compiler is needed. If one ever doesn't, the build fails here, loudly.
RUN pip install --only-binary=:all: -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2 — runtime
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000 \
    ENVIRONMENT=production

# Unprivileged user: the API never needs root.
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appuser app ./app

# app/core/logging.py writes logs/app.log relative to the working directory.
RUN mkdir logs && chown appuser:appuser logs

USER appuser

EXPOSE 8000

# python:slim has no curl, so the probe uses the standard library.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/' % os.environ.get('PORT', '8000'), timeout=4)"]

# Shell form only to expand $PORT (Render/Railway/Fly inject it); exec keeps
# uvicorn as PID 1 so it receives SIGTERM and shuts down cleanly.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

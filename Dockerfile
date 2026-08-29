# ---- frontend build (Svelte/Inertia via Vite) -------------------------------
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build   # -> /frontend/dist (+ .vite/manifest.json)

# ---- python builder ---------------------------------------------------------
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m app
USER app
WORKDIR /home/app/src

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --chown=app:app src/ /home/app/src/
# Built frontend assets; django-vite reads the manifest here (BASE_DIR.parent).
COPY --from=frontend --chown=app:app /frontend/dist /home/app/frontend/dist

# Collect static at build time: Cloud Run's filesystem is ephemeral and every
# instance is fresh, so WhiteNoise must serve a manifest baked into the image.
# Dummy env satisfies settings import (no DB/network is touched by collectstatic).
RUN SECRET_KEY=build-only DEBUG=False \
    POSTGRES_DATABASE_NAME=build POSTGRES_DATABASE_USER=build \
    POSTGRES_DATABASE_PASSWORD=build POSTGRES_DATABASE_HOST=build \
    POSTGRES_DATABASE_PORT=5432 \
    python manage.py collectstatic --no-input

# Cloud Run injects $PORT (defaults to 8080). Jobs override this command with
# `python manage.py <migrate|run_daily_digest|release_lessons>`.
CMD ["sh", "-c", "gunicorn cocoon.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers=3 --threads=2 --timeout=120 --log-level=info"]

# Househunt Opción A — multi-stage: Vite build → FastAPI static + API
# syntax=docker/dockerfile:1

FROM node:20-alpine AS deps-web
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

FROM node:20-alpine AS build-web
WORKDIR /web
COPY --from=deps-web /web/node_modules ./node_modules
COPY apps/web/ ./
RUN npm run build && mkdir -p /out && cp -r dist/. /out/

FROM python:3.12-slim AS deps-api
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*
COPY services/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime with Playwright Chromium baked in (required for live scrap in prod).
# Image ~1GB; Railway service should have ≥1–2 GB RAM.
FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    STATIC_DIR=/app/static \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=deps-api /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps-api /usr/local/bin /usr/local/bin
RUN playwright install --with-deps chromium

COPY services/api/ /app/
COPY --from=build-web /out /app/static

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/api/health" || exit 1

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

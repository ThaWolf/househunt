# Househunt Opción A — multi-stage: web build (stub OK) + API runtime
# syntax=docker/dockerfile:1

# --- Frontend deps / build (placeholder until FE lane fills apps/web) ---
FROM node:20-alpine AS deps-web
WORKDIR /web
# Create minimal stub so stage succeeds without apps/web yet
RUN mkdir -p /out && echo '<!doctype html><html><body><p>Househunt SPA placeholder</p></body></html>' > /out/index.html

FROM node:20-alpine AS build-web
WORKDIR /web
COPY --from=deps-web /out /out
# When apps/web exists, replace with: COPY apps/web/package*.json ./ && npm ci && COPY apps/web . && npm run build && cp -r dist /out

# --- API deps ---
FROM python:3.12-slim AS deps-api
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*
COPY services/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Runtime ---
FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    STATIC_DIR=/app/static

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=deps-api /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps-api /usr/local/bin /usr/local/bin
COPY services/api/ /app/
COPY --from=build-web /out /app/static

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/api/health" || exit 1

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

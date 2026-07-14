# househunt

Personal house-hunting aggregator (Argentina) — Vite/React + FastAPI + Playwright adapters.

Branch de factory: `factory/iter-001`.

## Quick start (local)

```bash
# API + Postgres
docker compose up --build

# SPA (otra terminal) — proxy /api → :8000
cd apps/web && npm install && npm run dev
```

- Web: http://localhost:5173  
- API: http://localhost:8000 (`/api/health`, `/docs`)  
- Prod-like (Opción A, SPA en static): solo Compose/`Dockerfile` → http://localhost:8000

## Frontend

[`apps/web`](apps/web) — Vite · React · TypeScript · Tailwind.

```bash
cd apps/web && npm install && npm run dev   # :5173
npm run build && npm test
```

## Backend

[`services/api`](services/api) — FastAPI · Alembic · adapters ×5 (fixtures by default).

```bash
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # JWT_SECRET + DATABASE_URL (+ Google opcional)
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pytest -q
```

## Env keys

Ver [`.env.example`](.env.example) / `services/api/.env.example`.  
Nunca commitees secretos reales. Hub local: `projects/househunt/secrets.local.env`.

`DATABASE_URL`, `JWT_*`, `GOOGLE_OAUTH_*`, `ADAPTER_*`, `FEATURE_*`, `CORS_ORIGINS`, `FRONTEND_URL`.

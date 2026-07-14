# househunt

Personal house-hunting aggregator (Argentina) — Vite/React + FastAPI + Playwright adapters.

Branch de factory: `factory/iter-001`.

## Quick start (local)

```bash
# API + Postgres (Opción A image)
make up
# or: docker compose up --build

# SPA (otra terminal) — proxy /api → :8000
make web
# or: cd apps/web && npm install && npm run dev
```

- Web: http://localhost:5173  
- API: http://localhost:8000 (`/api/health`, `/docs`)  
- Prod-like (Opción A, SPA en static): solo Compose/`Dockerfile` → http://localhost:8000

Healthcheck: `GET /api/health`.

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
cp ../../.env.example .env   # JWT_SECRET + DATABASE_URL (+ Google opcional)
alembic upgrade head
make -C ../.. api
# or: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pytest -q
```

## Makefile

| Target | Action |
|--------|--------|
| `make up` | `docker compose up --build` |
| `make test` | API pytest + web vitest |
| `make web` | Vite dev server |
| `make api` | uvicorn reload |

## CI

GitHub Actions: [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — pytest (API) + npm test/build (web); Docker image build on pull requests only.

## Deploy (Railway)

See **[docs/deploy-railway.md](docs/deploy-railway.md)** — Postgres plugin, env vars, OAuth redirects, single Docker service (Opción A). `RAILWAY_PUBLIC_URL` is deferred until you generate a domain.

## Env keys

Ver [`.env.example`](.env.example) / `services/api/.env.example`.  
Nunca commitees secretos reales. Hub local: `projects/househunt/secrets.local.env`.

`DATABASE_URL`, `JWT_*`, `GOOGLE_OAUTH_*`, `ADAPTER_*`, `FEATURE_*`, `CORS_ORIGINS`, `FRONTEND_URL`.  
`RAILWAY_PUBLIC_URL` — deferred (see Railway doc).

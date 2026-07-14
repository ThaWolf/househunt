# Househunt API

FastAPI backend for Househunt MVP (auth, search adapters, AppScore, interest/visits/calendar).

## Setup

```bash
cd services/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill JWT_SECRET + DATABASE_URL
```

## Database

Postgres via root compose:

```bash
# from repo root
docker compose up -d postgres
alembic upgrade head
```

## Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: `GET http://localhost:8000/api/health`
- OpenAPI: `http://localhost:8000/docs`

## Tests

```bash
pytest -q
```

## Google OAuth

Callback redirects to `{FRONTEND_URL}/auth/callback#accessToken=…&refreshToken=…`.

Calendar sync requires `FEATURE_GOOGLE_CALENDAR=true` and complete `GOOGLE_OAUTH_*` secrets; otherwise `POST /api/calendar/sync` returns `501 feature_disabled`.

## Adapters

Five portals under `app/adapters/` (zonaprop, argenprop, mercadolibre, remax, century21).  
Default `ADAPTER_USE_FIXTURES=true` for reliable MVP. Century21 can probe Hydra at `century21.com.ar/api` when fixtures off.

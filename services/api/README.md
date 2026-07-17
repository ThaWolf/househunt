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

**Default `ADAPTER_USE_FIXTURES=false`** (local-real): ZonaProp + Mercado Libre scrape live via Playwright
and return real `sourceUrl` + portal CDN images with `dataSource=live`. On bot_wall / failure the portal
returns **empty** with a typed error — never invents listings.

Curated fixtures (`sample_listings.json`) are empty by default after iter-4 purge (picsum / fake `/zp-NNNN.html` removed).
Set `ADAPTER_USE_FIXTURES=true` only for offline demos once you add verified `fixture_curated` rows.

`ADAPTER_TIMEOUT_SECONDS` default **45** (Playwright needs headroom). Rate-limit ≈ 1 req / 3s between browser fetches.

```bash
# Playwright browsers (first time)
python -m playwright install chromium
```

## Backfill external listings (iter-11)

Re-extracts + rescores already-saved `data_source=external` Properties (e.g. after
an extractor fix) without users re-pasting URLs. Sequential Playwright, safe for
Railway one-off runs. See `app/scripts/backfill_external.py` and
`API_CONTRACT.md` §12 / `ARCHITECTURE.md` §17 in the agent-army hub for the
full contract.

```bash
# All external Properties (default scope)
python -m app.scripts.backfill_external

# Scoped smoke (CSV of external_id, or --interest-list-id / --user-email)
python -m app.scripts.backfill_external --external-ids 16928305,19247558 --dry-run
```

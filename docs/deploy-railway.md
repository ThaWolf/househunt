# Deploy Househunt on Railway (Opción A)

Single Docker service: multi-stage Dockerfile builds Vite → FastAPI serves `/api/*` + SPA static. Postgres is a separate Railway plugin.

Branch de trabajo factory: `factory/iter-001`. Do not force-push `main`.

## 1. Prerequisites

- Railway account + project (or create one)
- Repo pushed to GitHub and linked to Railway **or** Railway CLI (`railway link`)
- Local secrets ready (JWT, Google OAuth) — never paste them into chat or commit them

## 2. Postgres plugin

1. In the Railway project: **New** → **Database** → **PostgreSQL**.
2. Open the Postgres service → **Variables** → copy `DATABASE_URL` (or use **Connect** / reference variables).
3. On the **app** service, add a variable reference so `DATABASE_URL` points at the plugin connection string.
   - App code accepts `postgresql://…` and normalizes to `postgresql+asyncpg://…`.
4. Optional: if Railway exposes a private URL, you may set `DATABASE_URL_RAILWAY_PRIVATE` for in-network use later — MVP can use the linked `DATABASE_URL` only.

## 3. App service (single Docker — Opción A)

1. **New** → **GitHub Repo** (or empty service) → set root Dockerfile:
   - Dockerfile: `/Dockerfile` (repo root)
   - Builder: Dockerfile
2. Ensure the service builds the whole monorepo context (needs `apps/web` + `services/api`).
3. Healthcheck path: `GET /api/health` (Dockerfile already defines one).
4. `PORT` is injected by Railway — do not hardcode a public port in the platform UI beyond Railway’s default.

Start command is already in the image:

```text
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
```

## 4. Environment variables (app service)

Set these on the **app** service (values from your local `secrets.local.env` / Railway UI — never commit them):

| Key | Notes |
|-----|--------|
| `DATABASE_URL` | From Postgres plugin (reference) |
| `JWT_SECRET` | Strong random secret |
| `JWT_ACCESS_TTL_MINUTES` | e.g. `30` |
| `JWT_REFRESH_TTL_DAYS` | e.g. `14` |
| `GOOGLE_OAUTH_CLIENT_ID` | Google Cloud Console |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google Cloud Console |
| `GOOGLE_OAUTH_REDIRECT_URI` | Must match Console exactly (see below) |
| `FRONTEND_URL` | Prod: same public origin as the app (after domain) |
| `CORS_ORIGINS` | Prod Opción A (same origin): empty or omit |
| `ADAPTER_*_ENABLED` | Usually `true` for all five portals |
| `ADAPTER_USE_FIXTURES` | `true` until live scrapers are stable |
| `FEATURE_GOOGLE_CALENDAR` | `false` until OAuth + calendar scopes ready |
| `FEATURE_GOOGLE_MAPS` | `false` unless Maps is enabled |
| `GOOGLE_MAPS_API_KEY` | Optional. Without it (or with `FEATURE_GOOGLE_MAPS=false`), UI/API must degrade — no crash, maps/POI maps features off |
| `FEATURE_POI` | `false` (stub) |
| `FEATURE_IMAGE_PROXY` | `true` recommended |
| `ENVIRONMENT` | `production` |
| `RAILWAY_PUBLIC_URL` | **Deferred** — set after you have a public domain |

Do **not** put secrets in the frontend bundle. CI must not echo secret values.

## 5. Google OAuth redirects (localhost vs prod)

| Environment | `GOOGLE_OAUTH_REDIRECT_URI` | Also authorized in Google Console |
|-------------|-----------------------------|-----------------------------------|
| Local | `http://localhost:8000/api/auth/google/callback` | Yes |
| Prod | `https://<your-public-host>/api/auth/google/callback` | Yes (add when domain exists) |

- After login, API redirects the browser to `{FRONTEND_URL}/auth/callback#…`.
- Local FE: `FRONTEND_URL=http://localhost:5173`.
- Prod Opción A: `FRONTEND_URL=https://<your-public-host>` (same host as API).

## 6. Domain → `RAILWAY_PUBLIC_URL` (later)

1. App service → **Settings** → **Networking** → **Generate domain** (or custom domain).
2. Set `RAILWAY_PUBLIC_URL=https://<that-host>` (no trailing slash).
3. Align `FRONTEND_URL`, `GOOGLE_OAUTH_REDIRECT_URI`, and Google Console URIs with that host.
4. Until the domain exists, leave `RAILWAY_PUBLIC_URL` unset; local OAuth still works with localhost redirects.

## 7. Deploy checklist

- [ ] Postgres plugin running
- [ ] `DATABASE_URL` linked on app
- [ ] `JWT_*` set
- [ ] Google OAuth localhost URI works locally; prod URI added when domain exists
- [ ] First deploy green; `GET /api/health` OK
- [ ] SPA loads from the same origin (Opción A)
- [ ] Set `RAILWAY_PUBLIC_URL` + prod OAuth redirect when domain is ready

## 8. Local parity

```bash
# From repo root
docker compose up --build   # postgres + Opción A api image
# or
make up
```

See root [README.md](../README.md) for Vite-on-host + API workflows.

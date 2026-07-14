# househunt

Personal house-hunting aggregator (Argentina) — Vite web + FastAPI API.

## Backend

API lives in [`services/api`](services/api). Contract: hub `factory/lanes/design/API_CONTRACT.md`.

### Local (uvicorn)

```bash
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set JWT_SECRET + DATABASE_URL
# with Postgres up:
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: `GET /api/health`
- Docs: `/docs`

### Docker Compose (api + postgres)

```bash
docker compose up --build
```

- API: `http://localhost:8000`
- Postgres: `localhost:5432` (`househunt` / `househunt` / `househunt`)

### Tests

```bash
cd services/api && pytest -q
```

### Env keys (see `.env.example`)

`DATABASE_URL`, `JWT_*`, `GOOGLE_OAUTH_*`, `ADAPTER_*`, `FEATURE_*`, `CORS_ORIGINS`, `FRONTEND_URL`.

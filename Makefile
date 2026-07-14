.PHONY: up test web api api-live qa-smoke down

# Postgres host mapping uses 5433 when local :5432 is busy (Docker VM disk may also need prune).
up:
	docker compose up --build

# Host Postgres port for tools: localhost:5433

down:
	docker compose down

# Unit/integration suites (no live portals)
test:
	cd services/api && pytest -q
	cd apps/web && npm test

web:
	cd apps/web && npm run dev

api:
	cd services/api && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Host live scrap (ADAPTER_USE_FIXTURES=false). Requires Chromium:
#   cd services/api && python -m playwright install chromium
# Compose Opción A stays slim — no Chromium in image; prefer this target for real portals.
api-live:
	cd services/api && ADAPTER_USE_FIXTURES=false uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# QA gate smoke (API must be up — e.g. make api-live). Env: HOUSEHUNT_API_BASE, QA_SMOKE_*
qa-smoke:
	python3 scripts/qa_smoke_search.py

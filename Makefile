.PHONY: up test web api down

# Postgres + Opción A API image (SPA in static)
up:
	docker compose up --build

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

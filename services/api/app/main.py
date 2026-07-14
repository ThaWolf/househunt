"""Househunt FastAPI app — API + SPA static mount."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.auth.router import router as auth_router
from app.calendar.router import router as calendar_router
from app.config import get_settings
from app.errors import AppError, app_error_handler, http_exception_handler, validation_exception_handler
from app.geo.router import router as geo_router
from app.interest.router import router as interest_router
from app.media.router import router as media_router
from app.meta import router as meta_router
from app.properties.router import router as properties_router
from app.search.router import router as search_router
from app.visits.router import router as visits_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.environment in ("development", "test") or "sqlite" in settings.database_url:
        from app.db.base import init_db

        await init_db()
    yield


def _resolve_static() -> Path:
    settings = get_settings()
    static_path = Path(settings.static_dir)
    if not static_path.is_absolute():
        static_path = Path(__file__).resolve().parent.parent / static_path
    static_path.mkdir(parents=True, exist_ok=True)
    return static_path


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    app.include_router(meta_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(geo_router, prefix="/api")
    app.include_router(search_router, prefix="/api")
    app.include_router(properties_router, prefix="/api")
    app.include_router(interest_router, prefix="/api")
    app.include_router(visits_router, prefix="/api")
    app.include_router(calendar_router, prefix="/api")
    app.include_router(media_router, prefix="/api")

    static_path = _resolve_static()
    assets = static_path / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    index = static_path / "index.html"

    @app.get("/")
    async def spa_root():
        if index.exists():
            return FileResponse(index)
        return JSONResponse(
            {
                "service": "househunt-api",
                "docs": "/docs",
                "health": "/api/health",
            }
        )

    # SPA fallback for client-side routes (does not override /api, /docs, etc.)
    @app.get("/app/{full_path:path}")
    async def spa_app_routes(full_path: str):
        _ = full_path
        if index.exists():
            return FileResponse(index)
        raise HTTPException(404, "SPA not built yet")

    # Generic SPA fallback excluding reserved prefixes
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        reserved = ("api", "docs", "redoc", "openapi.json", "assets")
        first = full_path.split("/", 1)[0]
        if first in reserved:
            raise HTTPException(404, "Not found")
        candidate = static_path / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        if index.exists():
            return FileResponse(index)
        raise HTTPException(404, "SPA not built yet")

    return app


app = create_app()

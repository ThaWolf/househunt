"""Application settings and feature flags."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Househunt API"
    app_version: str = "0.1.0-mvp"
    environment: str = "development"
    debug: bool = False

    database_url: str = Field(
        default="postgresql+asyncpg://househunt:househunt@localhost:5432/househunt",
        alias="DATABASE_URL",
    )

    jwt_secret: str = Field(default="dev-only-change-me", alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = Field(default=30, alias="JWT_ACCESS_TTL_MINUTES")
    jwt_refresh_ttl_days: int = Field(default=14, alias="JWT_REFRESH_TTL_DAYS")

    google_oauth_client_id: str | None = Field(default=None, alias="GOOGLE_OAUTH_CLIENT_ID")
    google_oauth_client_secret: str | None = Field(
        default=None, alias="GOOGLE_OAUTH_CLIENT_SECRET"
    )
    google_oauth_redirect_uri: str | None = Field(
        default=None, alias="GOOGLE_OAUTH_REDIRECT_URI"
    )

    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    port: int = Field(default=8000, alias="PORT")

    adapter_zonaprop_enabled: bool = Field(default=True, alias="ADAPTER_ZONAPROP_ENABLED")
    adapter_argenprop_enabled: bool = Field(default=True, alias="ADAPTER_ARGENPROP_ENABLED")
    adapter_mercadolibre_enabled: bool = Field(
        default=True, alias="ADAPTER_MERCADOLIBRE_ENABLED"
    )
    adapter_remax_enabled: bool = Field(default=True, alias="ADAPTER_REMAX_ENABLED")
    adapter_century21_enabled: bool = Field(default=True, alias="ADAPTER_CENTURY21_ENABLED")
    adapter_use_fixtures: bool = Field(default=True, alias="ADAPTER_USE_FIXTURES")
    adapter_timeout_seconds: float = Field(default=12.0, alias="ADAPTER_TIMEOUT_SECONDS")

    feature_google_calendar: bool = Field(default=False, alias="FEATURE_GOOGLE_CALENDAR")
    feature_poi: bool = Field(default=False, alias="FEATURE_POI")
    feature_image_proxy: bool = Field(default=True, alias="FEATURE_IMAGE_PROXY")

    static_dir: str = Field(default="static", alias="STATIC_DIR")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if isinstance(value, str) and value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins.strip():
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def google_oauth_configured(self) -> bool:
        return bool(
            self.google_oauth_client_id
            and self.google_oauth_client_secret
            and self.google_oauth_redirect_uri
            and not str(self.google_oauth_client_id).startswith("********")
            and not str(self.google_oauth_client_secret).startswith("********")
        )

    def effective_google_calendar(self) -> bool:
        return bool(self.feature_google_calendar and self.google_oauth_configured())

    def adapter_enabled(self, portal: str) -> bool:
        mapping = {
            "zonaprop": self.adapter_zonaprop_enabled,
            "argenprop": self.adapter_argenprop_enabled,
            "mercadolibre": self.adapter_mercadolibre_enabled,
            "remax": self.adapter_remax_enabled,
            "century21": self.adapter_century21_enabled,
        }
        return mapping.get(portal, False)

    def analysis_status(self, portal: str) -> Literal["ready", "needs_probe"]:
        return "ready" if portal == "century21" else "needs_probe"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Auto-disable calendar if secrets incomplete
    if settings.feature_google_calendar and not settings.google_oauth_configured():
        object.__setattr__(settings, "feature_google_calendar", False)
    return settings

"""Century 21 adapter — HTML/Playwright live (no anonymous Hydra)."""

from __future__ import annotations

from app.adapters.browser import BrowserFetchError
from app.adapters.century21.live import fetch_century21_live
from app.adapters.common import empty_result, fetch_with_fixtures, live_ok_result
from app.adapters.types import AdapterResult
from app.config import get_settings
from app.schemas.common import AdapterErrorCode, AdapterStatus, PortalId
from app.schemas.property import SearchFilters


def _error_code(raw: str) -> AdapterErrorCode:
    try:
        return AdapterErrorCode(raw)
    except ValueError:
        return AdapterErrorCode.network


class Century21Adapter:
    portal = PortalId.century21
    analysis_status = "ready"

    async def fetch(self, filters: SearchFilters) -> AdapterResult:
        settings = get_settings()
        if settings.adapter_use_fixtures:
            return await fetch_with_fixtures(
                self.portal, filters, analysis_status=self.analysis_status
            )
        try:
            items = await fetch_century21_live(filters, settings=settings)
            return live_ok_result(self.portal, filters, items, settings=settings)
        except BrowserFetchError as exc:
            code = _error_code(exc.code)
            status = (
                AdapterStatus.partial
                if code
                in (
                    AdapterErrorCode.bot_wall,
                    AdapterErrorCode.rate_limit,
                    AdapterErrorCode.auth_required,
                )
                else AdapterStatus.error
            )
            maturity = "broken" if code == AdapterErrorCode.auth_required else None
            return empty_result(
                self.portal,
                filters,
                settings=settings,
                code=code,
                message=exc.message,
                status=status,
                mode="live",
                maturity=maturity,
            )

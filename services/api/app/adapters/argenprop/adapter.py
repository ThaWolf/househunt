from __future__ import annotations

from app.adapters.browser import BrowserFetchError
from app.adapters.common import empty_result, fetch_with_fixtures, live_ok_result
from app.adapters.argenprop.live import fetch_argenprop_live
from app.adapters.types import AdapterResult
from app.config import get_settings
from app.schemas.common import AdapterErrorCode, AdapterStatus, PortalId
from app.schemas.property import SearchFilters


def _error_code(raw: str) -> AdapterErrorCode:
    try:
        return AdapterErrorCode(raw)
    except ValueError:
        return AdapterErrorCode.network


class ArgenpropAdapter:
    portal = PortalId.argenprop
    analysis_status = "ready"

    async def fetch(self, filters: SearchFilters) -> AdapterResult:
        settings = get_settings()
        if settings.adapter_use_fixtures:
            return await fetch_with_fixtures(
                self.portal, filters, analysis_status=self.analysis_status
            )
        try:
            items = await fetch_argenprop_live(filters, settings=settings)
            return live_ok_result(self.portal, filters, items, settings=settings)
        except BrowserFetchError as exc:
            code = _error_code(exc.code)
            status = (
                AdapterStatus.partial
                if code in (AdapterErrorCode.bot_wall, AdapterErrorCode.rate_limit)
                else AdapterStatus.error
            )
            return empty_result(
                self.portal,
                filters,
                settings=settings,
                code=code,
                message=exc.message,
                status=status,
                mode="live",
            )

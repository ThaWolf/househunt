from __future__ import annotations

from app.adapters.browser import BrowserFetchError
from app.adapters.common import empty_result, fetch_with_fixtures, live_ok_result
from app.adapters.remax.live import fetch_remax_live
from app.adapters.types import AdapterResult
from app.config import get_settings
from app.schemas.common import AdapterErrorCode, AdapterStatus, PortalId
from app.schemas.property import SearchFilters


def _error_code(raw: str) -> AdapterErrorCode:
    try:
        return AdapterErrorCode(raw)
    except ValueError:
        return AdapterErrorCode.network


class RemaxAdapter:
    portal = PortalId.remax
    analysis_status = "ready"

    async def fetch(self, filters: SearchFilters) -> AdapterResult:
        settings = get_settings()
        if settings.adapter_use_fixtures:
            return await fetch_with_fixtures(
                self.portal, filters, analysis_status=self.analysis_status
            )
        try:
            items = await fetch_remax_live(filters, settings=settings)
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
        except Exception as exc:  # noqa: BLE001
            return empty_result(
                self.portal,
                filters,
                settings=settings,
                code=AdapterErrorCode.network,
                message=f"Remax live failed: {type(exc).__name__}",
                status=AdapterStatus.error,
                mode="live",
            )

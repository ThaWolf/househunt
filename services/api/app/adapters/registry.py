"""Adapter registry — 5 portals selectable by feature flags."""

from __future__ import annotations

from app.adapters.argenprop.adapter import ArgenpropAdapter
from app.adapters.base import PortalAdapter
from app.adapters.century21.adapter import Century21Adapter
from app.adapters.mercadolibre.adapter import MercadoLibreAdapter
from app.adapters.remax.adapter import RemaxAdapter
from app.adapters.types import AdapterError, AdapterResult
from app.adapters.zonaprop.adapter import ZonaPropAdapter
from app.config import Settings, get_settings
from app.schemas.common import AdapterErrorCode, AdapterStatus, PortalId
from app.schemas.property import SearchFilters

_ADAPTERS: dict[PortalId, PortalAdapter] = {
    PortalId.zonaprop: ZonaPropAdapter(),
    PortalId.argenprop: ArgenpropAdapter(),
    PortalId.mercadolibre: MercadoLibreAdapter(),
    PortalId.remax: RemaxAdapter(),
    PortalId.century21: Century21Adapter(),
}


def all_adapters() -> dict[PortalId, PortalAdapter]:
    return dict(_ADAPTERS)


def get_adapter(portal: PortalId) -> PortalAdapter:
    return _ADAPTERS[portal]


async def run_adapter(
    portal: PortalId,
    filters: SearchFilters,
    *,
    settings: Settings | None = None,
) -> AdapterResult:
    settings = settings or get_settings()
    if not settings.adapter_enabled(portal.value):
        return AdapterResult(
            portal=portal,
            status=AdapterStatus.skipped,
            items=[],
            unsupported_filters=[],
            error=AdapterError(
                code=AdapterErrorCode.not_implemented,
                message=f"Adapter {portal.value} disabled by feature flag",
                retryable=False,
            ),
        )
    adapter = get_adapter(portal)
    try:
        return await adapter.fetch(filters)
    except Exception as exc:  # noqa: BLE001
        return AdapterResult(
            portal=portal,
            status=AdapterStatus.error,
            items=[],
            unsupported_filters=[],
            error=AdapterError(
                code=AdapterErrorCode.network,
                message=f"Adapter crashed: {type(exc).__name__}",
                retryable=True,
            ),
        )

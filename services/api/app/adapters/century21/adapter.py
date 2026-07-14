"""Century 21 adapter — prefer Hydra/API entrypoint; fixture fallback."""

from __future__ import annotations

import logging

import httpx

from app.adapters.common import filter_raw_items, fetch_with_fixtures
from app.adapters.fixtures.loader import load_fixture_properties
from app.adapters.types import AdapterError, AdapterResult, RawProperty
from app.config import get_settings
from app.schemas.common import (
    AdapterErrorCode,
    AdapterStatus,
    Operation,
    PortalId,
    PropertyType,
)
from app.schemas.property import SearchFilters

logger = logging.getLogger(__name__)

C21_SEARCH_UI = "https://century21.com.ar/busqueda/tipo_casa/operacion_venta"
C21_API_DOCS = "https://century21.com.ar/api/docs.jsonld"
C21_API_BASE = "https://century21.com.ar/api"


class Century21Adapter:
    portal = PortalId.century21
    analysis_status = "ready"

    async def fetch(self, filters: SearchFilters) -> AdapterResult:
        settings = get_settings()
        if settings.adapter_use_fixtures:
            return await fetch_with_fixtures(
                self.portal, filters, analysis_status=self.analysis_status
            )

        # Attempt real Hydra/API discovery + listings; degrade gracefully
        try:
            async with httpx.AsyncClient(
                timeout=settings.adapter_timeout_seconds,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; HousehuntMVP/0.1; +https://github.com/ThaWolf/househunt)"
                    ),
                    "Accept": "application/ld+json, application/json",
                },
            ) as client:
                docs = await client.get(C21_API_DOCS)
                if docs.status_code >= 400:
                    raise RuntimeError(f"docs status {docs.status_code}")

                # Hydra entrypoints vary; try common collection paths
                candidates = [
                    f"{C21_API_BASE}/propiedades",
                    f"{C21_API_BASE}/properties",
                    f"{C21_API_BASE}/inmuebles",
                    f"{C21_SEARCH_UI}",
                ]
                parsed: list[RawProperty] = []
                last_error: str | None = None
                for url in candidates:
                    resp = await client.get(url)
                    if resp.status_code >= 400:
                        last_error = f"{url} -> {resp.status_code}"
                        continue
                    parsed = self._parse_payload(resp)
                    if parsed:
                        break

                if parsed:
                    return AdapterResult(
                        portal=self.portal,
                        status=AdapterStatus.ok,
                        items=filter_raw_items(parsed, filters),
                        unsupported_filters=[],
                        error=None,
                    )

                # API reachable but schema unknown → fixtures + partial
                items = filter_raw_items(load_fixture_properties(self.portal), filters)
                return AdapterResult(
                    portal=self.portal,
                    status=AdapterStatus.partial,
                    items=items,
                    unsupported_filters=[],
                    error=AdapterError(
                        code=AdapterErrorCode.parse,
                        message=last_error or "C21 API reachable; listing schema not mapped yet",
                        retryable=True,
                    ),
                )
        except Exception as exc:  # noqa: BLE001 — never crash search
            logger.warning("century21 fetch failed: %s", type(exc).__name__)
            items = filter_raw_items(load_fixture_properties(self.portal), filters)
            return AdapterResult(
                portal=self.portal,
                status=AdapterStatus.partial if items else AdapterStatus.error,
                items=items,
                unsupported_filters=[],
                error=AdapterError(
                    code=AdapterErrorCode.network,
                    message="Century21 live fetch failed; returning fixtures",
                    retryable=True,
                ),
            )

    def _parse_payload(self, resp: httpx.Response) -> list[RawProperty]:
        ctype = resp.headers.get("content-type", "")
        if "json" not in ctype and "ld+json" not in ctype:
            return []
        try:
            data = resp.json()
        except Exception:
            return []

        members = []
        if isinstance(data, list):
            members = data
        elif isinstance(data, dict):
            for key in ("hydra:member", "member", "items", "results", "data"):
                if isinstance(data.get(key), list):
                    members = data[key]
                    break

        out: list[RawProperty] = []
        for i, row in enumerate(members[:30]):
            if not isinstance(row, dict):
                continue
            ext = str(
                row.get("id")
                or row.get("@id")
                or row.get("codigo")
                or row.get("externalId")
                or f"c21-live-{i}"
            )
            title = str(row.get("titulo") or row.get("title") or row.get("name") or "Propiedad C21")
            url = str(
                row.get("url")
                or row.get("permalink")
                or row.get("sourceUrl")
                or f"https://century21.com.ar/propiedad/{ext}"
            )
            price = row.get("precio") or row.get("price") or row.get("priceAmount")
            amount = None
            if isinstance(price, (int, float)):
                amount = float(price)
            elif isinstance(price, dict):
                amount = float(price.get("amount") or price.get("value") or 0) or None

            out.append(
                RawProperty(
                    portal=PortalId.century21,
                    external_id=ext.split("/")[-1],
                    source_url=url,
                    title=title,
                    description=row.get("descripcion") or row.get("description"),
                    operation=Operation.buy,
                    property_type=PropertyType.house,
                    price_amount=amount,
                    price_currency="USD",
                    address_raw=row.get("direccion") or row.get("address"),
                    rooms=row.get("ambientes") or row.get("rooms"),
                    bathrooms=row.get("banos") or row.get("bathrooms"),
                    raw_hints={"source": "century21_live"},
                )
            )
        return out

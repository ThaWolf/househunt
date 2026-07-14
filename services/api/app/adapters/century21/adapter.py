"""Century 21 adapter — Hydra/API best-effort; never invent listings."""

from __future__ import annotations

import logging

import httpx

from app.adapters.common import empty_result, fetch_with_fixtures, filter_raw_items, live_ok_result
from app.adapters.types import RawProperty
from app.config import get_settings
from app.schemas.common import (
    AdapterErrorCode,
    AdapterStatus,
    DataSource,
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

    async def fetch(self, filters: SearchFilters):
        settings = get_settings()
        if settings.adapter_use_fixtures:
            return await fetch_with_fixtures(
                self.portal, filters, analysis_status=self.analysis_status
            )

        try:
            async with httpx.AsyncClient(
                timeout=min(settings.adapter_timeout_seconds, 15.0),
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; HousehuntMVP/0.4; +https://github.com/ThaWolf/househunt)"
                    ),
                    "Accept": "application/ld+json, application/json",
                },
            ) as client:
                docs = await client.get(C21_API_DOCS)
                if docs.status_code == 403:
                    return empty_result(
                        self.portal,
                        filters,
                        settings=settings,
                        code=AdapterErrorCode.bot_wall,
                        message="Century21 API bot wall; omitting results",
                        status=AdapterStatus.partial,
                    )
                if docs.status_code >= 400:
                    return empty_result(
                        self.portal,
                        filters,
                        settings=settings,
                        code=AdapterErrorCode.network,
                        message=f"C21 docs status {docs.status_code}; omitting results",
                    )

                candidates = [
                    f"{C21_API_BASE}/propiedades",
                    f"{C21_API_BASE}/properties",
                    f"{C21_API_BASE}/inmuebles",
                    C21_SEARCH_UI,
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
                    return live_ok_result(
                        self.portal, filters, filter_raw_items(parsed, filters), settings=settings
                    )

                return empty_result(
                    self.portal,
                    filters,
                    settings=settings,
                    code=AdapterErrorCode.parse,
                    message=last_error or "C21 API reachable; listing schema not mapped",
                    status=AdapterStatus.partial,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("century21 fetch failed: %s", type(exc).__name__)
            return empty_result(
                self.portal,
                filters,
                settings=settings,
                code=AdapterErrorCode.network,
                message="Century21 live fetch failed; omitting results",
            )

    def _parse_payload(self, resp: httpx.Response) -> list[RawProperty]:
        ctype = resp.headers.get("content-type", "")
        if "json" not in ctype and "ld+json" not in ctype:
            return []
        try:
            data = resp.json()
        except Exception:
            return []

        members: list = []
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
                or ""
            )
            if not url or "century21.com.ar" not in url:
                # No invent: skip rows without real portal URL
                continue
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
                    data_source=DataSource.live,
                    raw_hints={"source": "century21_live"},
                )
            )
        return out

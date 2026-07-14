"""Remax live via public findAll API (prefer API over SPA HTML)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.adapters.rooms_parse import rooms_min_from_filters
from app.adapters.types import RawProperty
from app.adapters.veracity import HOUSEHUNT_PLACEHOLDER_URL, image_host_ok_for_portal
from app.config import Settings, get_settings
from app.schemas.common import DataSource, Operation, PortalId, PropertyType
from app.schemas.property import SearchFilters

logger = logging.getLogger(__name__)

FINDALL_URL = "https://api-ar.redremax.com/remaxweb-ar/api/listings/findAll"
DETAIL_BASE = "https://www.remax.com.ar/listings"
CDN_BASE = "https://d1acdg20u0pmxj.cloudfront.net"

# type.id 9 = casa (observed 2026-07-14)
_CASA_TYPE_ID = 9
_SALE_OP_ID = 1

_HEADERS = {
    "Origin": "https://www.remax.com.ar",
    "Referer": "https://www.remax.com.ar/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def _photo_url(photo: dict[str, Any]) -> str | None:
    path = photo.get("value") or photo.get("rawValue") or ""
    if not path:
        return None
    path = str(path).lstrip("/")
    if path.startswith("http"):
        return path
    parts = path.split("/")
    # listings/{id}/{file}.jpg → listings/{id}/1080xAUTO/{file}.jpg
    if len(parts) >= 3 and parts[0] == "listings":
        sized = f"{CDN_BASE}/{parts[0]}/{parts[1]}/1080xAUTO/{parts[-1]}"
        if not sized.endswith((".jpg", ".jpeg", ".png", ".webp")):
            sized = sized + ".jpg"
        return sized
    return f"{CDN_BASE}/{path}"


def _geo_tokens(filters: SearchFilters) -> list[str]:
    tokens: list[str] = []
    loc = filters.location.locality if filters.location else None
    district = filters.location.district if filters.location else None
    if loc:
        tokens.append(loc.lower())
        if "gonnet" in loc.lower():
            tokens.extend(["gonnet", "manuel b", "manuel-b"])
        if "city bell" in loc.lower():
            tokens.append("city bell")
    if district:
        tokens.append(district.lower())
    if not tokens:
        tokens = ["la plata", "gonnet", "city bell", "gba"]
    return tokens


def _matches_geo(row: dict[str, Any], tokens: list[str]) -> bool:
    hay = " ".join(
        [
            str(row.get("title") or ""),
            str(row.get("displayAddress") or ""),
            str(row.get("slug") or ""),
            str((row.get("addressInfo") or {})),
        ]
    ).lower()
    return any(t in hay for t in tokens)


def _row_to_raw(row: dict[str, Any], *, locality_hint: str | None) -> RawProperty | None:
    slug = row.get("slug")
    ext = str(row.get("id") or row.get("internalId") or "")
    if not slug or not ext:
        return None
    source_url = f"{DETAIL_BASE}/{slug}"
    title = str(row.get("title") or f"Propiedad Remax {ext}")
    rooms = row.get("totalRooms")
    if isinstance(rooms, float):
        rooms = int(rooms)
    if not isinstance(rooms, int):
        rooms = None
    amount = row.get("price")
    if isinstance(amount, (int, float)):
        amount = float(amount)
    else:
        amount = None
    cur = row.get("currency") or {}
    currency = cur.get("value") if isinstance(cur, dict) else "USD"
    images: list[dict] = []
    for i, photo in enumerate((row.get("photos") or [])[:5]):
        if not isinstance(photo, dict):
            continue
        url = _photo_url(photo)
        if url and image_host_ok_for_portal(PortalId.remax, url):
            images.append({"url": url, "order": i, "kind": "source"})
    if not images:
        images.append({"url": HOUSEHUNT_PLACEHOLDER_URL, "order": 0, "kind": "placeholder"})

    type_val = (row.get("type") or {}).get("value") if isinstance(row.get("type"), dict) else None
    prop_type = PropertyType.house
    if type_val and "departamento" in str(type_val):
        prop_type = PropertyType.apartment
    elif type_val and "terreno" in str(type_val):
        prop_type = PropertyType.land

    loc = row.get("location") or {}
    lat = lng = None
    if isinstance(loc, dict) and loc.get("coordinates"):
        coords = loc["coordinates"]
        if isinstance(coords, list) and len(coords) >= 2:
            lng, lat = float(coords[0]), float(coords[1])

    return RawProperty(
        portal=PortalId.remax,
        external_id=ext,
        source_url=source_url,
        title=title,
        description=None,
        operation=Operation.buy,
        property_type=prop_type,
        price_amount=amount,
        price_currency=str(currency or "USD"),
        address_raw=row.get("displayAddress"),
        address_province="Buenos Aires",
        address_locality=locality_hint,
        geo_lat=lat,
        geo_lng=lng,
        rooms=rooms,
        bathrooms=row.get("bathrooms") if isinstance(row.get("bathrooms"), int) else None,
        area_covered_m2=float(row["dimensionCovered"])
        if isinstance(row.get("dimensionCovered"), (int, float))
        else None,
        area_total_m2=float(row["dimensionLand"])
        if isinstance(row.get("dimensionLand"), (int, float))
        else None,
        images=images,
        data_source=DataSource.live,
        raw_hints={"source": "remax_findall", "slug": slug},
    )


async def scrape_remax(
    filters: SearchFilters,
    *,
    settings: Settings | None = None,
    max_items: int = 20,
) -> list[RawProperty]:
    settings = settings or get_settings()
    rooms_min = rooms_min_from_filters(filters)
    tokens = _geo_tokens(filters)
    locality_hint = filters.location.locality if filters.location else None
    page_size = min(filters.page_size_hint or settings.adapter_page_size_hint, 50)
    max_pages = min(filters.max_pages or settings.adapter_max_pages, 5)

    out: list[RawProperty] = []
    async with httpx.AsyncClient(
        timeout=min(settings.adapter_timeout_seconds, 25.0),
        headers=_HEADERS,
        follow_redirects=True,
    ) as client:
        for page in range(max_pages):
            if len(out) >= max_items:
                break
            resp = await client.get(
                FINDALL_URL,
                params={"page": page, "pageSize": page_size},
            )
            if resp.status_code == 401:
                from app.adapters.browser import BrowserFetchError

                raise BrowserFetchError("auth_required", "Remax findAll returned 401")
            if resp.status_code == 403:
                from app.adapters.browser import BrowserFetchError

                raise BrowserFetchError("bot_wall", "Remax findAll bot wall")
            if resp.status_code >= 400:
                from app.adapters.browser import BrowserFetchError

                raise BrowserFetchError("network", f"Remax findAll HTTP {resp.status_code}")
            payload = resp.json()
            data = payload.get("data") or {}
            rows = data.get("data") if isinstance(data, dict) else []
            if not isinstance(rows, list) or not rows:
                break
            for row in rows:
                if not isinstance(row, dict):
                    continue
                op = row.get("operation") or {}
                if isinstance(op, dict) and op.get("id") not in (None, _SALE_OP_ID):
                    if str(op.get("value") or "").lower() not in ("sale", "venta", ""):
                        continue
                typ = row.get("type") or {}
                # Prefer houses; allow PH when geo matches tightly
                type_id = typ.get("id") if isinstance(typ, dict) else None
                type_val = str(typ.get("value") or "").lower() if isinstance(typ, dict) else ""
                if type_id not in (None, _CASA_TYPE_ID) and "casa" not in type_val and "ph" not in type_val:
                    continue
                if not _matches_geo(row, tokens):
                    continue
                rooms = row.get("totalRooms")
                if rooms_min is not None:
                    if rooms is None or int(rooms) < rooms_min:
                        continue
                raw = _row_to_raw(row, locality_hint=locality_hint)
                if raw is None:
                    continue
                out.append(raw)
                if len(out) >= max_items:
                    break

    # If geo filter yielded nothing, take casa+sale with rooms from first pages (GBA-wide fallback)
    if not out:
        logger.info("remax geo filter empty; retrying casa/sale without geo string match")
        async with httpx.AsyncClient(
            timeout=min(settings.adapter_timeout_seconds, 25.0),
            headers=_HEADERS,
            follow_redirects=True,
        ) as client:
            resp = await client.get(FINDALL_URL, params={"page": 0, "pageSize": page_size})
            rows = ((resp.json().get("data") or {}).get("data")) or []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                typ = row.get("type") or {}
                type_id = typ.get("id") if isinstance(typ, dict) else None
                if type_id != _CASA_TYPE_ID:
                    continue
                op = row.get("operation") or {}
                if isinstance(op, dict) and op.get("id") not in (None, _SALE_OP_ID):
                    continue
                rooms = row.get("totalRooms")
                if rooms_min is not None and (rooms is None or int(rooms) < rooms_min):
                    continue
                # Soft geo: require La Plata / GBA-ish tokens in slug/title OR no location filter
                if filters.location and not _matches_geo(row, tokens + ["plata", "gba", "buenos"]):
                    continue
                raw = _row_to_raw(row, locality_hint=locality_hint)
                if raw:
                    out.append(raw)
                if len(out) >= max_items:
                    break

    logger.info("remax live scraped %s items", len(out))
    return out


async def fetch_remax_live(
    filters: SearchFilters,
    *,
    settings: Settings | None = None,
) -> list[RawProperty]:
    return await scrape_remax(filters, settings=settings)

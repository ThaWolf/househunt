"""Extract a listing from an arbitrary URL (iter-9 — "agregar publicación externa").

Two paths, one implementation:
- **Known portal** (host matches ZP/AP/ML/Remax/C21): portal id is the real one and
  images keep the portal CDN.
- **Unknown host**: generic extraction via JSON-LD (schema.org) + Open Graph. Portal =
  ``external`` and any non-banned ``og:image`` is trusted as ``kind=source`` (the user
  added the URL explicitly).

Parsing is done in-page (Playwright) so SPA-rendered metadata is available. No new deps.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any
from urllib.parse import urlparse, urlunparse

from app.adapters.amenities_parse import parse_amenities
from app.adapters.browser import BrowserFetchError, browser_page, goto_html
from app.adapters.listing_meta import detect_locality, detect_property_type
from app.adapters.price_parse import parse_price
from app.adapters.rooms_parse import parse_rooms
from app.adapters.types import RawProperty
from app.adapters.veracity import is_banned_image_host
from app.config import Settings, get_settings
from app.schemas.common import DataSource, Operation, PortalId, PropertyType

logger = logging.getLogger(__name__)


class ExternalExtractError(Exception):
    """Raised when a URL can't be turned into a usable listing."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code  # "unsupported_url" | "extract_failed"
        self.message = message


# host suffix → portal (reused idea from veracity.PORTAL_SOURCE_HOSTS)
_HOST_PORTAL: list[tuple[str, PortalId]] = [
    ("zonaprop.com.ar", PortalId.zonaprop),
    ("argenprop.com", PortalId.argenprop),
    ("mercadolibre.com.ar", PortalId.mercadolibre),
    ("remax.com.ar", PortalId.remax),
    ("century21.com.ar", PortalId.century21),
]

# per-portal external id extraction from the URL
_ID_PATTERNS: dict[PortalId, re.Pattern[str]] = {
    PortalId.zonaprop: re.compile(r"-(\d{5,})\.html", re.I),
    PortalId.argenprop: re.compile(r"(\d{6,})(?:$|[?/#])"),
    PortalId.mercadolibre: re.compile(r"MLA-?(\d{6,})", re.I),
    PortalId.century21: re.compile(r"/propiedad/(\d+)", re.I),
    PortalId.remax: re.compile(r"(\d{6,})(?:$|[?/#])"),
}


def _clean_url(url: str) -> str:
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc, p.path, "", "", ""))


def _detect_portal(host: str) -> PortalId | None:
    host = (host or "").lower()
    for suffix, portal in _HOST_PORTAL:
        if host == suffix or host.endswith("." + suffix):
            return portal
    return None


def _external_id(url: str, portal: PortalId | None) -> str:
    if portal is not None:
        pat = _ID_PATTERNS.get(portal)
        if pat:
            m = pat.search(url)
            if m:
                return m.group(1)
    digest = hashlib.sha1(_clean_url(url).lower().encode("utf-8")).hexdigest()[:12]
    return f"ext-{digest}"


# Runs in the page: collect JSON-LD blocks + OG/meta + title + candidate images.
_EXTRACT_JS = r"""
() => {
  const ld = [];
  for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
    const t = (s.textContent || '').trim();
    if (t) ld.push(t.slice(0, 20000));
  }
  const meta = {};
  for (const m of document.querySelectorAll('meta[property], meta[name]')) {
    const k = (m.getAttribute('property') || m.getAttribute('name') || '').toLowerCase();
    const v = m.getAttribute('content') || '';
    if (k && v && !(k in meta)) meta[k] = v;
  }
  const ogImages = [];
  for (const m of document.querySelectorAll('meta[property="og:image"], meta[property="og:image:secure_url"]')) {
    const v = m.getAttribute('content') || '';
    if (v) ogImages.push(v);
  }
  return {
    ld,
    meta,
    ogImages,
    title: document.title || '',
    bodyText: (document.body && document.body.innerText || '').slice(0, 4000),
  };
}
"""


def _iter_ld_nodes(raw_blocks: list[str]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for block in raw_blocks:
        try:
            data = json.loads(block)
        except (json.JSONDecodeError, ValueError):
            continue
        stack = [data]
        while stack:
            cur = stack.pop()
            if isinstance(cur, list):
                stack.extend(cur)
            elif isinstance(cur, dict):
                if "@graph" in cur and isinstance(cur["@graph"], list):
                    stack.extend(cur["@graph"])
                nodes.append(cur)
    return nodes


def _first(*vals: Any) -> Any:
    for v in vals:
        if v:
            return v
    return None


def _ld_pick(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Pull the most listing-like fields out of JSON-LD nodes."""
    out: dict[str, Any] = {}
    for node in nodes:
        name = node.get("name") or node.get("headline")
        if name and "name" not in out:
            out["name"] = name
        desc = node.get("description")
        if desc and "description" not in out:
            out["description"] = desc
        img = node.get("image")
        if img and "image" not in out:
            if isinstance(img, dict):
                img = img.get("url")
            out["image"] = img
        offers = node.get("offers")
        if offers:
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            if isinstance(offers, dict):
                if offers.get("price") and "price" not in out:
                    out["price"] = offers.get("price")
                if offers.get("priceCurrency") and "priceCurrency" not in out:
                    out["priceCurrency"] = offers.get("priceCurrency")
        addr = node.get("address")
        if isinstance(addr, dict) and "address" not in out:
            out["address"] = addr
    return out


def _collect_images(ld: dict[str, Any], og_images: list[str], portal: PortalId | None) -> list[dict]:
    urls: list[str] = []
    ld_img = ld.get("image")
    if isinstance(ld_img, list):
        urls.extend([u for u in ld_img if isinstance(u, str)])
    elif isinstance(ld_img, str):
        urls.append(ld_img)
    urls.extend(og_images)

    seen: set[str] = set()
    images: list[dict] = []
    order = 0
    for u in urls:
        u = (u or "").strip()
        if not u or u in seen or not u.startswith("http"):
            continue
        if is_banned_image_host(u):
            continue
        seen.add(u)
        images.append({"url": u, "order": order, "kind": "source"})
        order += 1
        if order >= 12:
            break
    return images


def _price(ld: dict[str, Any], meta: dict[str, str], body_text: str) -> tuple[float | None, str | None]:
    # JSON-LD offers.price is the most reliable
    raw = ld.get("price")
    currency = ld.get("priceCurrency") or meta.get("product:price:currency")
    if raw is None:
        raw = meta.get("product:price:amount") or meta.get("og:price:amount")
    if raw is not None:
        text = f"{currency or ''} {raw}"
        amount, cur = parse_price(str(text), default_currency=(currency or "USD"))
        if amount:
            return amount, (cur or currency or "USD")
    # fallback: scan body — reject street heights; prefer largest marked price
    amount, cur = parse_price(
        body_text or "",
        default_currency="USD",
        prefer_largest=True,
        reject_street_numbers=True,
    )
    return amount, cur


def _normalize_locality(
    url: str,
    title: str,
    description: str | None,
    body_text: str,
    ld_locality: str | None,
    ld_province: str | None,
) -> tuple[str | None, str | None, str | None]:
    """Return (locality, neighborhood, province) preferring slug heuristics."""
    loc, neigh = detect_locality(url, title, description or body_text)
    if loc:
        return loc, neigh, "Buenos Aires"
    # Clean JSON-LD admin labels like "Partido de La Plata, Argentina"
    if ld_locality:
        low = ld_locality.lower()
        if "gonnet" in low:
            return "Gonnet", None, "Buenos Aires"
        if "partido de la plata" in low or ld_locality.strip().lower().startswith("partido"):
            return "La Plata", None, "Buenos Aires"
        # drop country suffix
        cleaned = ld_locality.split(",")[0].strip()
        if cleaned:
            return cleaned, None, ld_province or "Buenos Aires"
    return ld_locality, None, ld_province


async def extract_listing(url: str, *, settings: Settings | None = None) -> RawProperty:
    """Fetch ``url`` and build a RawProperty (data_source=external). Raises ExternalExtractError."""
    settings = settings or get_settings()
    url = (url or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ExternalExtractError("unsupported_url", "URL inválida (usá http/https).")

    portal = _detect_portal(parsed.hostname or "")
    timeout_ms = int(max(settings.adapter_timeout_seconds, 20) * 1000)

    try:
        async with browser_page(timeout_ms=timeout_ms) as page:
            await goto_html(page, url, wait_bot_clear_seconds=6.0)
            try:
                await page.wait_for_timeout(1200)
            except Exception:
                pass
            data = await page.evaluate(_EXTRACT_JS)
    except BrowserFetchError as exc:
        raise ExternalExtractError("extract_failed", f"No se pudo abrir la publicación ({exc.code}).") from exc
    except Exception as exc:  # noqa: BLE001
        raise ExternalExtractError("extract_failed", f"Fallo al extraer: {type(exc).__name__}") from exc

    meta: dict[str, str] = data.get("meta") or {}
    ld = _ld_pick(_iter_ld_nodes(data.get("ld") or []))
    og_images: list[str] = data.get("ogImages") or []
    page_title: str = data.get("title") or ""
    body_text: str = data.get("bodyText") or ""

    title = _first(ld.get("name"), meta.get("og:title"), page_title)
    if not title:
        raise ExternalExtractError("extract_failed", "No se pudo leer el título de la publicación.")
    title = str(title).strip()[:500]

    description = _first(ld.get("description"), meta.get("og:description"), meta.get("description"))
    description = str(description).strip()[:4000] if description else None

    images = _collect_images(ld, og_images, portal)
    amount, currency = _price(ld, meta, body_text)

    prop_type = detect_property_type(url, title)
    if prop_type is PropertyType.other:
        # external listings aren't restricted to houses; default to house when unknown
        prop_type = PropertyType.house

    addr = ld.get("address") if isinstance(ld.get("address"), dict) else {}
    ld_locality = addr.get("addressLocality") if addr else None
    ld_province = addr.get("addressRegion") if addr else None
    street = addr.get("streetAddress") if addr else None
    locality, neighborhood, province = _normalize_locality(
        url, title, description, body_text, ld_locality, ld_province
    )
    rooms = parse_rooms(url, title, description, body_text)
    amenities = parse_amenities(title, description, body_text)

    raw = RawProperty(
        portal=portal or PortalId.external,
        external_id=_external_id(url, portal),
        source_url=_clean_url(url),
        title=title,
        description=description,
        operation=Operation.buy,
        property_type=prop_type,
        price_amount=amount,
        price_currency=currency or "USD",
        address_raw=street,
        address_province=province,
        address_locality=locality,
        address_neighborhood=neighborhood,
        rooms=rooms,
        amenities=amenities,
        images=images,
        data_source=DataSource.external,
        raw_hints={"source": "external_url", "host": parsed.hostname or "", "detectedPortal": portal.value if portal else None},
    )
    logger.info(
        "external extract: portal=%s id=%s price=%s imgs=%s from %s",
        raw.portal.value,
        raw.external_id,
        raw.price_amount,
        len(raw.images),
        raw.source_url,
    )
    return raw

"""ZonaProp live scraper (Playwright)."""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse, urlunparse

from app.adapters.browser import BrowserFetchError, browser_page, goto_html
from app.adapters.rooms_parse import parse_rooms, rooms_min_from_filters
from app.adapters.types import RawProperty
from app.adapters.veracity import HOUSEHUNT_PLACEHOLDER_URL, image_host_ok_for_portal
from app.config import Settings, get_settings
from app.schemas.common import DataSource, Operation, PortalId, PropertyType
from app.schemas.property import SearchFilters

logger = logging.getLogger(__name__)

_LOCALITY_SLUGS = {
    "gonnet": "manuel-b-gonnet",
    "manuel b. gonnet": "manuel-b-gonnet",
    "manuel b gonnet": "manuel-b-gonnet",
    "city bell": "city-bell",
    "la plata": "la-plata",
    "pilar": "pilar",
}


def build_search_url(filters: SearchFilters) -> str:
    slug = "la-plata"
    if filters.location and filters.location.locality:
        key = filters.location.locality.strip().lower()
        slug = _LOCALITY_SLUGS.get(key, re.sub(r"[^a-z0-9]+", "-", key).strip("-") or "la-plata")
    elif filters.geo and filters.geo.locality:
        key = filters.geo.locality.strip().lower()
        slug = _LOCALITY_SLUGS.get(key, re.sub(r"[^a-z0-9]+", "-", key).strip("-") or "la-plata")
    rooms_min = rooms_min_from_filters(filters)
    # Navent pattern observed in market URLs (probe pending exact CF confirm)
    if rooms_min and rooms_min >= 1:
        return f"https://www.zonaprop.com.ar/casas-venta-{slug}-mas-de-{rooms_min}-ambientes.html"
    return f"https://www.zonaprop.com.ar/casas-venta-{slug}.html"


def _clean_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _title_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/").split("/")[-1]
    path = re.sub(r"\.html?$", "", path, flags=re.I)
    path = re.sub(r"-\d+$", "", path)
    path = re.sub(r"^veclcain-?", "", path, flags=re.I)
    words = [w for w in path.replace("-", " ").split() if w]
    return " ".join(w.capitalize() for w in words) or "Casa en venta"


def _parse_price(text: str | None) -> tuple[float | None, str | None]:
    if not text:
        return None, None
    t = text.replace("\xa0", " ").strip()
    currency = "USD" if "USD" in t.upper() or "U$S" in t.upper() else ("ARS" if "$" in t else None)
    digits = re.sub(r"[^\d]", "", t)
    if not digits:
        return None, currency
    try:
        return float(digits), currency or "USD"
    except ValueError:
        return None, currency


def _guess_locality(loc: str | None, filters: SearchFilters) -> tuple[str | None, str | None]:
    raw = (loc or "").strip() or None
    locality = filters.location.locality if filters.location else None
    neighborhood = None
    if raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if parts:
            neighborhood = parts[0]
            if not locality and len(parts) > 1:
                locality = parts[0]
            elif parts[0].lower().startswith("manuel"):
                locality = locality or "Gonnet"
    return locality, neighborhood


EXTRACT_JS = """
() => {
  const out = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('a[href*="/propiedades/clasificado/"]')) {
    const href = (a.href || '').split('#')[0];
    if (!href || seen.has(href)) continue;
    seen.add(href);
    const card = a.closest('[data-qa="POSTING_CARD"]')
      || a.closest('[data-id]')
      || a.closest('article')
      || a.parentElement;
    const titleEl = card && card.querySelector(
      '[data-qa="POSTING_CARD_DESCRIPTION"], h2, h3, .postingCardTitle, .PostingCard-title'
    );
    const img = card && card.querySelector(
      'img[src*="zonapropcdn"], img[data-src*="zonapropcdn"], img'
    );
    const priceEl = card && card.querySelector(
      '[data-qa="POSTING_CARD_PRICE"], .price-value, .postingCardPrice, .PostingCard-price'
    );
    const locEl = card && card.querySelector(
      '[data-qa="POSTING_CARD_LOCATION"], .postingCardLocation, .PostingCard-location'
    );
    const featsEl = card && card.querySelector(
      '[data-qa="POSTING_CARD_FEATURES"], .postingCardFeatures, .PostingCard-features, ul'
    );
    const idMatch = href.match(/(\\d{6,})\\.html/);
    const titleText = (titleEl && titleEl.textContent || '').trim();
    const featsText = (featsEl && featsEl.textContent || '').trim();
    const cardText = (card && card.innerText || '').slice(0, 600);
    out.push({
      href,
      title: titleText,
      img: img && (img.getAttribute('src') || img.getAttribute('data-src')),
      price: priceEl && priceEl.textContent.trim(),
      loc: locEl && locEl.textContent.trim(),
      feats: featsText,
      cardText,
      id: idMatch && idMatch[1],
    });
    if (out.length >= 40) break;
  }
  return out;
}
"""


async def scrape_zonaprop(
    filters: SearchFilters,
    *,
    settings: Settings | None = None,
    max_items: int = 20,
) -> list[RawProperty]:
    settings = settings or get_settings()
    url = build_search_url(filters)
    timeout_ms = int(max(settings.adapter_timeout_seconds, 20) * 1000)
    rooms_min = rooms_min_from_filters(filters)

    async with browser_page(timeout_ms=timeout_ms) as page:
        try:
            await goto_html(page, url, wait_bot_clear_seconds=14.0)
        except BrowserFetchError as exc:
            # Room-path slug may 404/CF; fall back to base locality URL
            if rooms_min and "mas-de" in url:
                fallback = re.sub(r"-mas-de-\d+-ambientes", "", url)
                logger.info("zonaprop rooms URL failed (%s); retry %s", exc.code, fallback)
                await goto_html(page, fallback, wait_bot_clear_seconds=14.0)
                url = fallback
            else:
                raise
        rows = await page.evaluate(EXTRACT_JS)

    items: list[RawProperty] = []
    for row in rows[:max_items]:
        href = _clean_url(row.get("href") or "")
        ext = str(row.get("id") or "")
        if not href or not ext:
            continue
        if "zonaprop.com.ar" not in href:
            continue
        title = (row.get("title") or "").strip()
        # Card title often equals price strip — derive from URL slug when weak
        if not title or re.fullmatch(r"(USD|U\$S|\$)?[\d\.\s,]+", title, flags=re.I):
            title = _title_from_url(href)
        amount, currency = _parse_price(row.get("price"))
        locality, neighborhood = _guess_locality(row.get("loc"), filters)
        rooms = parse_rooms(
            row.get("feats"),
            row.get("cardText"),
            title,
            href,
        )
        # If portal rooms URL was applied and card lacks rooms, inherit min as lower bound hint
        if rooms is None and rooms_min is not None and "mas-de" in url:
            rooms = rooms_min
        img_url = row.get("img")
        images: list[dict] = []
        if img_url and image_host_ok_for_portal(PortalId.zonaprop, img_url):
            bigger = re.sub(r"/\d+x\d+/", "/720x532/", img_url)
            images.append({"url": bigger, "order": 0, "kind": "source"})
        else:
            images.append({"url": HOUSEHUNT_PLACEHOLDER_URL, "order": 0, "kind": "placeholder"})

        items.append(
            RawProperty(
                portal=PortalId.zonaprop,
                external_id=ext,
                source_url=href,
                title=title,
                description=None,
                operation=Operation.buy,
                property_type=PropertyType.house,
                price_amount=amount,
                price_currency=currency or "USD",
                address_raw=row.get("loc"),
                address_province="Buenos Aires",
                address_locality=locality,
                address_neighborhood=neighborhood,
                rooms=rooms,
                images=images,
                data_source=DataSource.live,
                raw_hints={"source": "zonaprop_live", "searchUrl": url},
            )
        )
    logger.info("zonaprop live scraped %s items from %s", len(items), url)
    return items


async def fetch_zonaprop_live(
    filters: SearchFilters,
    *,
    settings: Settings | None = None,
) -> list[RawProperty]:
    try:
        return await scrape_zonaprop(filters, settings=settings)
    except BrowserFetchError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise BrowserFetchError("parse", f"ZonaProp scrape failed: {type(exc).__name__}") from exc

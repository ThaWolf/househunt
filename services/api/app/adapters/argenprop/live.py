"""Argenprop live scraper (Playwright HTML)."""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse, urlunparse

from app.adapters.amenities_parse import parse_amenities
from app.adapters.browser import BrowserFetchError, browser_page, goto_html
from app.adapters.rooms_parse import parse_rooms, rooms_min_from_filters
from app.adapters.types import RawProperty
from app.adapters.veracity import HOUSEHUNT_PLACEHOLDER_URL, image_host_ok_for_portal
from app.config import Settings, get_settings
from app.schemas.common import DataSource, Operation, PortalId, PropertyType
from app.schemas.property import SearchFilters

logger = logging.getLogger(__name__)

_LOCALITY_SLUGS = {
    "gonnet": "manuel-gonnet",
    "manuel b. gonnet": "manuel-gonnet",
    "manuel b gonnet": "manuel-gonnet",
    "manuel gonnet": "manuel-gonnet",
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
    base = f"https://www.argenprop.com/casas/venta/{slug}"
    if rooms_min:
        base = f"{base}/{rooms_min}-ambientes"
    return base


def _clean_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


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


EXTRACT_JS = """
() => {
  const out = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('a[href*="/casa-en-venta"]')) {
    const href = (a.href || '').split('#')[0];
    const m = href.match(/--(\\d+)\\/?$/);
    if (!m) continue;
    const id = m[1];
    if (seen.has(id)) continue;
    seen.add(id);
    const card = a.closest('div, article, li') || a.parentElement;
    const img = card && card.querySelector('img');
    const priceEl = card && card.querySelector(
      '.card__price, .price, [class*="price"]'
    );
    const title = (a.getAttribute('title') || a.textContent || '').trim()
      || (img && (img.getAttribute('alt') || '')) || '';
    const cardText = (card && card.innerText || '').slice(0, 700);
    const imgSrc = img && (img.getAttribute('src') || img.getAttribute('data-src') || '');
    out.push({
      id,
      href,
      title,
      img: imgSrc,
      imgAlt: img && img.getAttribute('alt'),
      price: priceEl && priceEl.textContent.trim(),
      cardText,
    });
    if (out.length >= 40) break;
  }
  return out;
}
"""


async def scrape_argenprop(
    filters: SearchFilters,
    *,
    settings: Settings | None = None,
    max_items: int = 20,
) -> list[RawProperty]:
    settings = settings or get_settings()
    url = build_search_url(filters)
    timeout_ms = int(max(settings.adapter_timeout_seconds, 20) * 1000)
    rooms_min = rooms_min_from_filters(filters)
    locality = filters.location.locality if filters.location else None

    async with browser_page(timeout_ms=timeout_ms) as page:
        await goto_html(page, url, wait_bot_clear_seconds=10.0)
        rows = await page.evaluate(EXTRACT_JS)

    items: list[RawProperty] = []
    for row in rows[:max_items]:
        href = _clean_url(row.get("href") or "")
        if href.startswith("/"):
            href = urljoin("https://www.argenprop.com", href)
        ext = str(row.get("id") or "")
        if not href or not ext or "argenprop.com" not in href:
            continue
        title = (row.get("title") or "").strip() or f"Casa Argenprop {ext}"
        rooms = parse_rooms(href, row.get("imgAlt"), row.get("cardText"), title)
        if rooms is None and rooms_min is not None and f"{rooms_min}-ambientes" in url:
            rooms = rooms_min
        amount, currency = _parse_price(row.get("price"))
        img_url = row.get("img") or ""
        if img_url.startswith("//"):
            img_url = "https:" + img_url
        elif img_url.startswith("/"):
            img_url = urljoin("https://www.argenprop.com", img_url)
        images: list[dict] = []
        if img_url and image_host_ok_for_portal(PortalId.argenprop, img_url):
            images.append({"url": img_url, "order": 0, "kind": "source"})
        else:
            images.append({"url": HOUSEHUNT_PLACEHOLDER_URL, "order": 0, "kind": "placeholder"})

        desc = None
        card = (row.get("cardText") or "").strip()
        if len(card) > 40:
            desc = card[:2000]

        amenities = parse_amenities(title, desc, href, card)

        items.append(
            RawProperty(
                portal=PortalId.argenprop,
                external_id=ext,
                source_url=href,
                title=title[:200],
                description=desc,
                operation=Operation.buy,
                property_type=PropertyType.house,
                price_amount=amount,
                price_currency=currency or "USD",
                address_raw=None,
                address_province="Buenos Aires",
                address_locality=locality,
                rooms=rooms,
                amenities=amenities,
                images=images,
                data_source=DataSource.live,
                raw_hints={"source": "argenprop_live", "searchUrl": url},
            )
        )
    logger.info("argenprop live scraped %s items from %s", len(items), url)
    return items


async def fetch_argenprop_live(
    filters: SearchFilters,
    *,
    settings: Settings | None = None,
) -> list[RawProperty]:
    try:
        return await scrape_argenprop(filters, settings=settings)
    except BrowserFetchError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise BrowserFetchError("parse", f"Argenprop scrape failed: {type(exc).__name__}") from exc

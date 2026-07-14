"""Mercado Libre Inmuebles live scraper (Playwright)."""

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

_LOCALITY_PATH = {
    "gonnet": "manuel-b-gonnet",
    "manuel b. gonnet": "manuel-b-gonnet",
    "manuel b gonnet": "manuel-b-gonnet",
    "city bell": "city-bell",
    "la plata": "",
    "pilar": "pilar",
}


def build_search_url(filters: SearchFilters) -> str:
    # Verified 2026-07-14:
    # …/casas/venta/3-ambientes/bsas-gba-sur/la-plata/manuel-b-gonnet/
    rooms_min = rooms_min_from_filters(filters)
    rooms_seg = f"{rooms_min}-ambientes/" if rooms_min else ""
    base = f"https://inmuebles.mercadolibre.com.ar/casas/venta/{rooms_seg}bsas-gba-sur/la-plata"
    loc = None
    if filters.location and filters.location.locality:
        loc = filters.location.locality.strip().lower()
    elif filters.geo and filters.geo.locality:
        loc = filters.geo.locality.strip().lower()
    if loc:
        slug = _LOCALITY_PATH.get(loc)
        if slug is None:
            slug = re.sub(r"[^a-z0-9]+", "-", loc).strip("-")
        if slug:
            base = f"{base}/{slug}"
    return base + "/"


def _clean_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _parse_price_from_card(text: str | None) -> tuple[float | None, str | None]:
    if not text:
        return None, None
    t = text.replace("\xa0", " ").strip()
    currency = "USD" if "U$S" in t.upper() or "USD" in t.upper() else "ARS"
    digits = re.sub(r"[^\d]", "", t)
    if not digits:
        return None, currency
    try:
        return float(digits), currency
    except ValueError:
        return None, currency


EXTRACT_JS = """
() => {
  const out = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('a')) {
    const href = (a.href || '').split('#')[0];
    const m = href.match(/MLA-(\\d+)/i);
    if (!m) continue;
    const id = m[1];
    if (seen.has(id)) continue;
    if (!/mercadolibre\\.com\\.ar/i.test(href)) continue;
    seen.add(id);
    const card = a.closest('li') || a.closest('.ui-search-result') || a.closest('.poly-card') || a.parentElement;
    const img = card && card.querySelector('img');
    const priceEl = card && card.querySelector(
      '.andes-money-amount__fraction, .poly-price__current .andes-money-amount__fraction, .price-tag-fraction'
    );
    const currencyEl = card && card.querySelector(
      '.andes-money-amount__currency-symbol, .price-tag-symbol'
    );
    const attrsEl = card && card.querySelector(
      '.ui-search-card-attributes, .poly-attributes_list, .ui-search-item__group__element'
    );
    const title = (a.textContent || '').trim();
    const imgSrc = img && (img.getAttribute('src') || img.getAttribute('data-src') || '');
    const cardText = (card && card.innerText || '').slice(0, 600);
    out.push({
      id,
      href,
      title,
      img: imgSrc,
      price: priceEl && priceEl.textContent.trim(),
      currencySymbol: currencyEl && currencyEl.textContent.trim(),
      attrs: attrsEl && attrsEl.textContent.trim(),
      cardText,
    });
    if (out.length >= 40) break;
  }
  return out;
}
"""


async def scrape_mercadolibre(
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
        final_url, _html, _status = await goto_html(page, url, wait_bot_clear_seconds=10.0)
        if "captcha" in final_url.lower():
            raise BrowserFetchError("bot_wall", f"ML captcha wall at {final_url}")
        rows = await page.evaluate(EXTRACT_JS)

    locality = filters.location.locality if filters.location else None
    items: list[RawProperty] = []
    for row in rows[:max_items]:
        href = _clean_url(row.get("href") or "")
        ext = str(row.get("id") or "")
        if not href or not ext:
            continue
        title = (row.get("title") or "").strip() or f"Casa MLA-{ext}"
        # Skip non-property noise (building materials etc.)
        if not re.search(r"casa|chalet|ph|inmueble|propiedad", title, re.I) and "casa.mercadolibre" not in href:
            if "articulo.mercadolibre" in href:
                continue
        amount, currency = _parse_price_from_card(row.get("price"))
        if row.get("currencySymbol") and "U$S" in str(row.get("currencySymbol")).upper():
            currency = "USD"
        rooms = parse_rooms(row.get("attrs"), row.get("cardText"), title, href)
        if rooms is None and rooms_min is not None and f"{rooms_min}-ambientes" in url:
            # Portal already filtered by N-ambientes path
            rooms = rooms_min
        img_url = row.get("img") or ""
        if " " in img_url:
            img_url = img_url.split()[0]
        images: list[dict] = []
        if img_url and image_host_ok_for_portal(PortalId.mercadolibre, img_url):
            images.append({"url": img_url, "order": 0, "kind": "source"})
        else:
            images.append({"url": HOUSEHUNT_PLACEHOLDER_URL, "order": 0, "kind": "placeholder"})

        items.append(
            RawProperty(
                portal=PortalId.mercadolibre,
                external_id=ext,
                source_url=href,
                title=title,
                description=None,
                operation=Operation.buy,
                property_type=PropertyType.house,
                price_amount=amount,
                price_currency=currency or "USD",
                address_raw=None,
                address_province="Buenos Aires",
                address_locality=locality,
                address_neighborhood=None,
                rooms=rooms,
                images=images,
                data_source=DataSource.live,
                raw_hints={"source": "mercadolibre_live", "searchUrl": url},
            )
        )
    logger.info("mercadolibre live scraped %s items from %s", len(items), url)
    return items


async def fetch_mercadolibre_live(
    filters: SearchFilters,
    *,
    settings: Settings | None = None,
) -> list[RawProperty]:
    try:
        return await scrape_mercadolibre(filters, settings=settings)
    except BrowserFetchError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise BrowserFetchError("parse", f"ML scrape failed: {type(exc).__name__}") from exc

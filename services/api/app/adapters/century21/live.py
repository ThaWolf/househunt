"""Century 21 live scraper — HTML/Playwright (Hydra anonymous returns 401)."""

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

C21_SEARCH_UI = "https://century21.com.ar/busqueda/tipo_casa/operacion_venta"
C21_GBA_SUR = "https://century21.com.ar/v/resultados/en-pais_argentina/en-estado_gba-sur"


def build_search_url(filters: SearchFilters) -> str:
    loc = None
    if filters.location and filters.location.locality:
        loc = filters.location.locality.strip().lower()
    elif filters.geo and filters.geo.locality:
        loc = filters.geo.locality.strip().lower()
    # GBA Sur inventory covers Gonnet / La Plata / City Bell better than national
    if loc and any(x in loc for x in ("gonnet", "plata", "bell", "berisso", "ensenada")):
        return C21_GBA_SUR
    return C21_SEARCH_UI


def _clean_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _parse_price(text: str) -> tuple[float | None, str | None]:
    if not text:
        return None, None
    currency = "USD" if "USD" in text.upper() or "U$S" in text.upper() else ("ARS" if "$" in text else None)
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        return None, currency
    try:
        return float(digits), currency or "USD"
    except ValueError:
        return None, currency


def _parse_title_line(card_text: str) -> str:
    for line in (card_text or "").splitlines():
        line = line.strip()
        if not line or line.lower() in ("anterior", "siguiente", "nueva en el mercado"):
            continue
        if re.match(r"^\d+/\d+$", line):
            continue
        if "en venta" in line.lower() or "casa" in line.lower() or len(line) > 25:
            return line[:200]
    return "Casa en venta Century21"


EXTRACT_JS = """
() => {
  const out = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('a[href*="/propiedad/"]')) {
    const href = (a.href || '').split('#')[0];
    const m = href.match(/\\/propiedad\\/(\\d+)/);
    if (!m) continue;
    const id = m[1];
    if (seen.has(id)) continue;
    seen.add(id);
    const card = a.closest('.card, article, .col, .item, li, .propiedad, div') || a.parentElement;
    const img = card && card.querySelector('img');
    const cardText = (card && card.innerText || '').slice(0, 900);
    out.push({
      id,
      href,
      img: img && (img.src || img.getAttribute('data-src') || ''),
      cardText,
    });
    if (out.length >= 40) break;
  }
  return out;
}
"""


async def scrape_century21(
    filters: SearchFilters,
    *,
    settings: Settings | None = None,
    max_items: int = 20,
) -> list[RawProperty]:
    settings = settings or get_settings()
    url = build_search_url(filters)
    timeout_ms = int(max(settings.adapter_timeout_seconds, 25) * 1000)
    rooms_min = rooms_min_from_filters(filters)
    locality = filters.location.locality if filters.location else None

    async with browser_page(timeout_ms=timeout_ms) as page:
        await goto_html(page, url, wait_bot_clear_seconds=8.0)
        # SPA hydrates cards after first paint
        try:
            await page.wait_for_selector('a[href*="/propiedad/"]', timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)
        rows = await page.evaluate(EXTRACT_JS)

    items: list[RawProperty] = []
    for row in rows[: max_items * 2]:
        href = _clean_url(row.get("href") or "")
        ext = str(row.get("id") or "")
        if not href or not ext or "century21.com.ar" not in href:
            continue
        card_text = row.get("cardText") or ""
        title = _parse_title_line(card_text)
        rooms = parse_rooms(card_text, href, title)
        # Prefer listings matching geo tokens when location set
        if locality:
            hay = (card_text + " " + href + " " + title).lower()
            tokens = [locality.lower()]
            if "gonnet" in locality.lower():
                tokens.extend(["gonnet", "la plata", "gba sur"])
            if not any(t in hay for t in tokens):
                # keep GBA Sur results if searching Gonnet (parent district expand)
                if "gba sur" not in hay and "la plata" not in hay and "gonnet" not in hay:
                    continue
        amount, currency = _parse_price(card_text)
        img_url = row.get("img") or ""
        images: list[dict] = []
        if img_url and image_host_ok_for_portal(PortalId.century21, img_url):
            images.append({"url": img_url, "order": 0, "kind": "source"})
        else:
            images.append({"url": HOUSEHUNT_PLACEHOLDER_URL, "order": 0, "kind": "placeholder"})

        desc = None
        if len(card_text) > 80:
            # Skip UI chrome — take last paragraph-ish chunk
            parts = [p.strip() for p in card_text.split("\n") if len(p.strip()) > 60]
            if parts:
                desc = parts[-1][:2000]

        items.append(
            RawProperty(
                portal=PortalId.century21,
                external_id=ext,
                source_url=href,
                title=title,
                description=desc,
                operation=Operation.buy,
                property_type=PropertyType.house,
                price_amount=amount,
                price_currency=currency or "USD",
                address_raw=None,
                address_province="Buenos Aires",
                address_locality=locality,
                rooms=rooms,
                images=images,
                data_source=DataSource.live,
                raw_hints={"source": "century21_html", "searchUrl": url},
            )
        )
        if len(items) >= max_items:
            break

    # If rooms.min wiped candidate set pre-filter, still return with rooms when URL inventory is large
    if rooms_min is not None:
        with_rooms = [i for i in items if i.rooms is None or i.rooms >= rooms_min]
        # Prefer with_rooms when any; else leave items (diagnostics will tipify wipe)
        if with_rooms:
            items = with_rooms

    logger.info("century21 live scraped %s items from %s", len(items), url)
    return items


async def fetch_century21_live(
    filters: SearchFilters,
    *,
    settings: Settings | None = None,
) -> list[RawProperty]:
    try:
        return await scrape_century21(filters, settings=settings)
    except BrowserFetchError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise BrowserFetchError("parse", f"Century21 scrape failed: {type(exc).__name__}") from exc

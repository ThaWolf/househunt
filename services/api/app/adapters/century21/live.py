"""Century 21 live scraper — HTML/Playwright (Hydra anonymous returns 401)."""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse, urlunparse

from app.adapters.browser import BrowserFetchError, browser_page, goto_html
from app.adapters.listing_meta import detect_locality, detect_property_type
from app.adapters.price_parse import parse_price
from app.adapters.rooms_parse import parse_rooms, rooms_min_from_filters
from app.adapters.types import RawProperty
from app.adapters.veracity import HOUSEHUNT_PLACEHOLDER_URL, image_host_ok_for_portal
from app.config import Settings, get_settings
from app.geo.match import location_matches_listing
from app.schemas.common import DataSource, Operation, PortalId, PropertyType
from app.schemas.property import SearchFilters

logger = logging.getLogger(__name__)

C21_BASE = "https://century21.com.ar/v/resultados"
# Casas multi-type (casa + duplex + cabaña + náutica), como la UI "Casas en venta".
C21_TYPE_CASAS = "tipo_casa-o-casa-duplex-o-cabana-o-casa-nautica"

# Fallbacks (localidad sin mapeo server-side) — comportamiento iter-7 + cleanup post-scrape.
C21_SEARCH_UI = "https://century21.com.ar/busqueda/tipo_casa/operacion_venta"
C21_GBA_SUR = f"{C21_BASE}/en-pais_argentina/en-estado_gba-sur"

# iter-8: C21 SÍ filtra geo/tipo/rooms/precio server-side por URL anónima.
# Mapa localidad → (estado, municipio, colonia|None). Ver lanes/analysis/RCA.md (iter-8).
# Colonia confirmada solo Gonnet; el resto de hijos de La Plata usan municipio-level
# (`en-municipio_gba-sur-la-plata`) y el geo-cleanup post-scrape afina el barrio.
_C21_GEO: dict[str, tuple[str, str, str | None]] = {
    "gonnet": ("gba-sur", "gba-sur-la-plata", "la-plata-manuel-b-gonnet"),
    "manuel b gonnet": ("gba-sur", "gba-sur-la-plata", "la-plata-manuel-b-gonnet"),
    "manuel b. gonnet": ("gba-sur", "gba-sur-la-plata", "la-plata-manuel-b-gonnet"),
    "city bell": ("gba-sur", "gba-sur-la-plata", None),
    "villa elisa": ("gba-sur", "gba-sur-la-plata", None),
    "tolosa": ("gba-sur", "gba-sur-la-plata", None),
    "gorina": ("gba-sur", "gba-sur-la-plata", None),
    "joaquin gorina": ("gba-sur", "gba-sur-la-plata", None),
    "ringuelet": ("gba-sur", "gba-sur-la-plata", None),
    "hernandez": ("gba-sur", "gba-sur-la-plata", None),
    "los hornos": ("gba-sur", "gba-sur-la-plata", None),
    "la plata": ("gba-sur", "gba-sur-la-plata", None),
}


def _resolve_locality(filters: SearchFilters) -> str | None:
    if filters.location and filters.location.locality:
        return filters.location.locality.strip().lower()
    if filters.geo and filters.geo.locality:
        return filters.geo.locality.strip().lower()
    return None


def _c21_geo(loc: str | None) -> tuple[str, str, str | None] | None:
    """Return (estado, municipio, colonia|None) for a locality, or None if unmapped."""
    if not loc:
        return None
    entry = _C21_GEO.get(loc)
    if entry is not None:
        return entry
    # Gonnet aliases / substrings
    if "gonnet" in loc:
        return _C21_GEO["gonnet"]
    # Any other La Plata child / La Plata itself → municipio-level, geo-cleanup afina.
    if "plata" in loc or loc in _C21_GEO:
        return ("gba-sur", "gba-sur-la-plata", None)
    return None


def _price_currency(filters: SearchFilters) -> str:
    cur = "usd"
    if filters.price and filters.price.currency:
        c = filters.price.currency
        cur = (c.value if hasattr(c, "value") else str(c)).lower()
    return cur


def build_search_url(filters: SearchFilters) -> str:
    """iter-8: URL de resultados **filtrada** server-side de C21.

    Reemplaza el scrape genérico de GBA Sur (que traía todos los tipos/localidades).
    Estructura verificada (Gonnet 3 dorm ≤150k → 23 casas incl 309776). Si la localidad
    no tiene mapeo geo → fallback al entrypoint iter-7 + limpieza post-scrape.
    """
    loc = _resolve_locality(filters)
    geo = _c21_geo(loc)
    if geo is None:
        # Sin mapeo → comportamiento iter-7 (GBA Sur genérico) + cleanup post-scrape.
        if loc and any(x in loc for x in ("bell", "berisso", "ensenada", "quilmes")):
            return C21_GBA_SUR
        return C21_SEARCH_UI

    estado, municipio, colonia = geo
    parts = [
        C21_BASE,
        C21_TYPE_CASAS,
        "operacion_venta",
        "uso_habitacional",
        "en-pais_argentina",
        f"en-estado_{estado}",
        f"en-municipio_{municipio}",
    ]
    if colonia:
        parts.append(f"en-colonia_{colonia}")

    rooms_min = rooms_min_from_filters(filters)
    if rooms_min:
        parts.append(f"dormitorios_{rooms_min}")

    if filters.price and (filters.price.min or filters.price.max):
        parts.append(f"moneda_{_price_currency(filters)}")
        if filters.price.min:
            parts.append(f"precio-desde_{int(filters.price.min)}")
        if filters.price.max:
            parts.append(f"precio-hasta_{int(filters.price.max)}")

    return "/".join(parts)


def _clean_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _parse_price(text: str) -> tuple[float | None, str | None]:
    if not text:
        return None, None
    # iter-6: number-group aware (evita concatenar todos los dígitos del card) + US$ → USD
    amount, currency = parse_price(text, default_currency="USD")
    return amount, currency or "USD"


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
  // iter-9: la galería <img class="image-gallery-image"> es HERMANA del <a> de texto,
  // no descendiente, así que a.closest(...).querySelector('img') no la ve. Construimos
  // un mapa id→primera-foto parseando el segmento /propiedades/<id>/ de la URL de imagen.
  const imgById = {};
  for (const img of document.querySelectorAll('img')) {
    const src = img.src || img.getAttribute('data-src') || '';
    const mm = src.match(/\\/propiedades\\/(\\d+)\\//);
    if (!mm) continue;
    if (!imgById[mm[1]]) imgById[mm[1]] = src;  // primera = slide 1 (portada)
  }
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
    const cardImg = card && card.querySelector('img');
    const cardText = (card && card.innerText || '').slice(0, 900);
    out.push({
      id,
      href,
      img: imgById[id] || (cardImg && (cardImg.src || cardImg.getAttribute('data-src'))) || '',
      cardText,
    });
    if (out.length >= 200) break;
  }
  return out;
}
"""


async def _collect_rows(page, *, target: int = 120, max_scrolls: int = 16) -> list[dict]:
    """Accumulate unique cards across scrolls (C21 GBA Sur is an infinite-scroll SPA)."""
    seen: set[str] = set()
    rows: list[dict] = []
    stagnant = 0
    for _ in range(max_scrolls):
        batch = await page.evaluate(EXTRACT_JS)
        before = len(rows)
        for r in batch:
            rid = str(r.get("id") or "")
            if not rid or rid in seen:
                continue
            seen.add(rid)
            rows.append(r)
        if len(rows) >= target:
            break
        # Stop if two consecutive scrolls add nothing (reached the end)
        stagnant = stagnant + 1 if len(rows) == before else 0
        if stagnant >= 2:
            break
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1400)
    return rows


async def scrape_century21(
    filters: SearchFilters,
    *,
    settings: Settings | None = None,
    max_items: int = 40,
) -> list[RawProperty]:
    """iter-8: entrypoint = URL **filtrada** server-side (tipo+geo+dormitorios+precio).

    `build_search_url` arma `/v/resultados/…en-municipio_/en-colonia_/dormitorios_N/
    moneda_/precio-hasta_N`, que C21 filtra sin login (verificado: Gonnet 3 dorm ≤150k
    → 23 casas incl 309776). Igual mantenemos la **defensa iter-7** (parse real de
    tipo/localidad + geo-cleanup + enforce casa) para descartar colas (p.ej. algún City
    Bell que la colonia deja pasar). Si la localidad no tiene mapeo geo, `build_search_url`
    cae al entrypoint GBA Sur genérico y el cleanup hace el resto. Ver `analysis/RCA.md` (iter-8).
    """
    from app.search.postfilter import resolve_location  # lazy: evita ciclo de import

    settings = settings or get_settings()
    url = build_search_url(filters)
    timeout_ms = int(max(settings.adapter_timeout_seconds, 25) * 1000)
    rooms_min = rooms_min_from_filters(filters)
    location = resolve_location(filters)

    async with browser_page(timeout_ms=timeout_ms) as page:
        await goto_html(page, url, wait_bot_clear_seconds=8.0)
        # SPA hydrates cards after first paint
        try:
            await page.wait_for_selector('a[href*="/propiedad/"]', timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)
        rows = await _collect_rows(page, target=max_items * 8)

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("century21 raw ids: %s", [r.get("id") for r in rows])

    dropped_type = 0
    dropped_geo = 0
    items: list[RawProperty] = []
    for row in rows:
        href = _clean_url(row.get("href") or "")
        ext = str(row.get("id") or "")
        if not href or not ext or "century21.com.ar" not in href:
            continue
        card_text = row.get("cardText") or ""
        title = _parse_title_line(card_text)

        # 1) Tipo real (slug líder). Fuera de scope (depto/oficina/cochera/…) → drop.
        prop_type = detect_property_type(href, title)
        if prop_type != PropertyType.house:
            dropped_type += 1
            continue

        # 2) Localidad real (slug/card), nunca la del filtro.
        loc_name, neigh = detect_locality(href, title, card_text)
        slug_text = href.rsplit("_", 1)[-1].replace("-", " ") if "_" in href else ""

        # 3) Limpieza post-scraping geo: solo la ubicación pedida (dato real).
        if location is not None and not location_matches_listing(
            location,
            address_locality=loc_name,
            address_neighborhood=neigh,
            address_raw=slug_text or None,
            title=title,
        ):
            dropped_geo += 1
            continue

        rooms = parse_rooms(card_text, href, title)
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
                property_type=prop_type,
                price_amount=amount,
                price_currency=currency or "USD",
                address_raw=slug_text or None,
                address_province="Buenos Aires",
                address_locality=loc_name,
                address_neighborhood=neigh,
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

    logger.info(
        "century21 live: %s scraped rows → %s casas (drop tipo=%s, geo=%s) from %s",
        len(rows),
        len(items),
        dropped_type,
        dropped_geo,
        url,
    )
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

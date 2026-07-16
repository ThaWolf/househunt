"""Parse real property_type + locality from a listing slug/card (iter-7).

Century 21 lists mixed types in one results page and its slug is the reliable
source of truth for the type: `/propiedad/<id>_casa-en-venta-en-la-plata-…`.
The LEADING slug token is authoritative — scanning the whole text is unsafe
(e.g. a *casa* whose slug ends in `-verde-cochera` must not be read as cochera).
"""

from __future__ import annotations

import re

from app.geo.normalize import normalize_geo_text
from app.schemas.common import PropertyType

# Leading slug/title token → type. Order-independent (exact leading word).
_TYPE_LEAD: dict[str, PropertyType] = {
    # casas
    "casa": PropertyType.house,
    "casas": PropertyType.house,
    "chalet": PropertyType.house,
    "quinta": PropertyType.house,
    "duplex": PropertyType.house,
    "triplex": PropertyType.house,
    "vivienda": PropertyType.house,
    # deptos / ph
    "departamento": PropertyType.apartment,
    "departamentos": PropertyType.apartment,
    "depto": PropertyType.apartment,
    "monoambiente": PropertyType.apartment,
    "loft": PropertyType.apartment,
    "semipiso": PropertyType.apartment,
    "piso": PropertyType.apartment,
    "ph": PropertyType.apartment,
    # tierra
    "terreno": PropertyType.land,
    "lote": PropertyType.land,
    "campo": PropertyType.land,
    "chacra": PropertyType.land,
    "fraccion": PropertyType.land,
    "parcela": PropertyType.land,
    # comercial / otros (fuera de scope casas)
    "oficina": PropertyType.other,
    "local": PropertyType.other,
    "cochera": PropertyType.other,
    "galpon": PropertyType.other,
    "deposito": PropertyType.other,
    "edificio": PropertyType.other,
    "hotel": PropertyType.other,
    "consultorio": PropertyType.other,
    "fondo": PropertyType.other,  # fondo-de-comercio
    "negocio": PropertyType.other,
}

_C21_SLUG_RE = re.compile(r"/propiedad/\d+_([a-z0-9\-]+)", re.IGNORECASE)


def _c21_slug(href: str | None) -> str:
    m = _C21_SLUG_RE.search(href or "")
    return m.group(1).lower() if m else ""


def detect_property_type(href: str | None = None, title: str | None = None) -> PropertyType:
    """Real type from the leading slug token (preferred) or leading title word.

    Unknown → ``other`` (dropped downstream), never ``house`` — evita re-colar
    deptos/oficinas/cocheras como si fueran casas.
    """
    slug = _c21_slug(href)
    if slug:
        lead = slug.split("-", 1)[0]
        if lead in _TYPE_LEAD:
            return _TYPE_LEAD[lead]
    if title:
        words = normalize_geo_text(title).split()
        if words and words[0] in _TYPE_LEAD:
            return _TYPE_LEAD[words[0]]
    return PropertyType.other


# La Plata child localities (barrios) — más específico que "La Plata".
_LA_PLATA_CHILDREN: dict[str, str] = {
    "gonnet": "Gonnet",
    "manuel b gonnet": "Gonnet",
    "manuel belgrano gonnet": "Gonnet",
    "city bell": "City Bell",
    "villa elisa": "Villa Elisa",
    "tolosa": "Tolosa",
    "ringuelet": "Ringuelet",
    "gorina": "Gorina",
    "joaquin gorina": "Gorina",
    "hernandez": "Hernández",
    "los hornos": "Los Hornos",
    "san carlos": "San Carlos",
    "melchor romero": "Melchor Romero",
    "lisandro olmos": "Lisandro Olmos",
    "olmos": "Lisandro Olmos",
    "abasto": "Abasto",
    "arturo segui": "Arturo Seguí",
    "el peligro": "El Peligro",
    "etcheverry": "Etcheverry",
}

# Otras localidades GBA Sur / partidos vecinos que aparecen en resultados C21.
_OTHER_LOCALITIES: dict[str, str] = {
    "la plata": "La Plata",
    "berisso": "Berisso",
    "ensenada": "Ensenada",
    "berazategui": "Berazategui",
    "hudson": "Hudson",
    "guillermo enrique hudson": "Hudson",
    "ranelagh": "Ranelagh",
    "quilmes": "Quilmes",
    "bernal": "Bernal",
    "ezpeleta": "Ezpeleta",
    "don bosco": "Don Bosco",
    "wilde": "Wilde",
    "sarandi": "Sarandí",
    "avellaneda": "Avellaneda",
    "lanus": "Lanús",
    "lomas de zamora": "Lomas de Zamora",
    "temperley": "Temperley",
    "banfield": "Banfield",
    "adrogue": "Adrogué",
    "burzaco": "Burzaco",
    "longchamps": "Longchamps",
    "glew": "Glew",
    "monte grande": "Monte Grande",
    "ezeiza": "Ezeiza",
    "canning": "Canning",
    "brandsen": "Brandsen",
    "magdalena": "Magdalena",
}

# Longest tokens first so "manuel b gonnet" wins over a bare "gonnet" etc.
_ALL_LOCALITIES: list[tuple[str, str, bool]] = sorted(
    [(k, v, True) for k, v in _LA_PLATA_CHILDREN.items()]
    + [(k, v, False) for k, v in _OTHER_LOCALITIES.items()],
    key=lambda t: len(t[0]),
    reverse=True,
)


def _scan_locality(hay: str) -> tuple[str | None, str | None]:
    """Scan one normalized text; child (barrio) wins over city; longest token first."""
    other_hit: str | None = None
    for token, display, is_child in _ALL_LOCALITIES:
        if re.search(rf"\b{re.escape(token)}\b", hay):
            if is_child:
                return display, display  # barrio más específico → corta
            if other_hit is None:
                other_hit = display
    if other_hit:
        return other_hit, None
    return None, None


def detect_locality(
    href: str | None = None,
    title: str | None = None,
    card_text: str | None = None,
) -> tuple[str | None, str | None]:
    """Return ``(locality, neighborhood)`` parsed from slug/title/card.

    **El slug manda** (fuente de verdad); el card se usa solo si el slug no dice
    nada — así el nombre de la oficina C21 (p.ej. "Century 21 Gonnet") no pisa la
    localidad real del aviso (p.ej. City Bell). Un hijo de La Plata (Gonnet/
    Tolosa/…) se devuelve como localidad y barrio; una ciudad simple como
    localidad. ``None`` si no hay nada reconocible → lo decide el geo post-filter.
    """
    slug = _c21_slug(href).replace("-", " ")
    for source in (slug, title, card_text):
        hay = normalize_geo_text(source)
        if not hay:
            continue
        loc, neigh = _scan_locality(hay)
        if loc:
            return loc, neigh
    return None, None

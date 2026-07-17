"""Parse rooms/ambientes from portal card text, titles, and URL slugs (E22)."""

from __future__ import annotations

import re
import unicodedata

_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(\d+)\s*-ambientes?\b", re.I),
    re.compile(r"(\d+)\s*ambientes?\b", re.I),
    re.compile(r"(\d+)\s*amb\b", re.I),
    re.compile(r"(\d+)\s*dormitorios?\b", re.I),
    re.compile(r"(\d+)\s*hab(?:itaciones?)?\b", re.I),
    re.compile(r"(\d+)\s*rec\.?\b", re.I),  # Century21 "3 Rec."
)

_WORD_NUM: dict[str, int] = {
    "un": 1,
    "una": 1,
    "uno": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
}

_WORD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(un|una|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)"
        r"\s+dormitorios?\b",
        re.I,
    ),
    re.compile(
        r"\b(un|una|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)"
        r"\s+ambientes?\b",
        re.I,
    ),
    re.compile(
        r"\b(un|una|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)"
        r"\s+habitaciones?\b",
        re.I,
    ),
)


def _fold(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def parse_rooms(*parts: str | None) -> int | None:
    """Return first plausible rooms count found in any text/URL fragment."""
    for part in parts:
        if not part:
            continue
        for pat in _PATTERNS:
            m = pat.search(part)
            if not m:
                continue
            n = int(m.group(1))
            if 1 <= n <= 30:
                return n
        folded = _fold(part)
        for pat in _WORD_PATTERNS:
            m = pat.search(folded)
            if not m:
                continue
            n = _WORD_NUM.get(m.group(1).lower())
            if n is not None and 1 <= n <= 30:
                return n
    return None


def rooms_min_from_filters(filters) -> int | None:
    rooms = getattr(filters, "rooms", None)
    if rooms is None:
        return None
    return getattr(rooms, "min", None)


# --- E31 (iter-11): dormitorios/habitaciones win over slug "-N-ambientes" -----
#
# "Ambientes" (rooms incl. living/kitchen) != "dormitorios/habitaciones" (bedrooms).
# Portal URLs/titles often lead with ambientes (e.g. "...-6-ambientes--16928305")
# while the hero text/JSON-LD carries the real bedroom count (3). Filter + AppScore
# use habitaciones semantics, so bedrooms must win whenever both signals exist.

_BEDROOM_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(\d+)\s*dormitorios?\b", re.I),
    re.compile(r"(\d+)\s*dorm\.?\b", re.I),
    re.compile(r"(\d+)\s*hab(?:itaciones?)?\b", re.I),
    re.compile(r"(\d+)\s*rec\.?\b", re.I),
)

_BEDROOM_WORD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(un|una|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)"
        r"\s+dormitorios?\b",
        re.I,
    ),
    re.compile(
        r"\b(un|una|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)"
        r"\s+habitaciones?\b",
        re.I,
    ),
)


def _first_number(patterns: tuple[re.Pattern[str], ...], *parts: str | None) -> int | None:
    for part in parts:
        if not part:
            continue
        for pat in patterns:
            m = pat.search(part)
            if not m:
                continue
            n = int(m.group(1))
            if 1 <= n <= 30:
                return n
    return None


def _first_word_number(patterns: tuple[re.Pattern[str], ...], *parts: str | None) -> int | None:
    for part in parts:
        if not part:
            continue
        folded = _fold(part)
        for pat in patterns:
            m = pat.search(folded)
            if not m:
                continue
            n = _WORD_NUM.get(m.group(1).lower())
            if n is not None and 1 <= n <= 30:
                return n
    return None


def parse_bedrooms(*parts: str | None) -> int | None:
    """First plausible dormitorios/habitaciones count from text (no slug/URL)."""
    n = _first_number(_BEDROOM_PATTERNS, *parts)
    if n is not None:
        return n
    return _first_word_number(_BEDROOM_WORD_PATTERNS, *parts)


def parse_rooms_for_listing(
    url: str | None,
    title: str | None,
    description: str | None,
    body: str | None,
    *,
    ld_bedrooms: int | None = None,
) -> int | None:
    """Rooms for an extracted listing (iter-11 · E31).

    Order: JSON-LD ``numberOfBedrooms`` -> dormitorios/hab regex in
    title+description+body -> legacy ``parse_rooms`` (slug ``-N-ambientes`` and
    friends). Bedrooms win over ambientes whenever both are present and differ.
    """
    if ld_bedrooms is not None and 1 <= ld_bedrooms <= 30:
        return ld_bedrooms
    bedrooms = parse_bedrooms(title, description, body)
    if bedrooms is not None:
        return bedrooms
    return parse_rooms(url, title, description, body)

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

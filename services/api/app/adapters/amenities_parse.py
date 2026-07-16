"""Parse amenity tokens from listing text (iter-10).

Canonical tokens match ``interest.amenities.HIGHLIGHT_SPEC``:
``pileta``, ``jardin``, ``cochera``, ``quincho``.
"""

from __future__ import annotations

import re
import unicodedata

# alias phrases (normalized, no accents) → canonical token
_ALIASES: list[tuple[str, str]] = [
    ("pileta", "pileta"),
    ("piscina", "pileta"),
    ("jardin", "jardin"),
    ("jardines", "jardin"),
    ("parque", "jardin"),
    ("parques", "jardin"),
    ("patio", "jardin"),
    ("cochera", "cochera"),
    ("garage", "cochera"),
    ("garaje", "cochera"),
    ("estacionamiento", "cochera"),
    ("quincho", "quincho"),
    ("parrilla", "quincho"),
    ("parrillero", "quincho"),
]


def _fold(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def parse_amenities(*parts: str | None) -> list[str]:
    """Return unique canonical amenity tokens found in any text part."""
    blob = " ".join(_fold(p) for p in parts if p)
    if not blob:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for alias, token in _ALIASES:
        # word-ish boundary (allow plurals already in alias list)
        if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", blob):
            if token not in seen:
                seen.add(token)
                found.append(token)
    return found

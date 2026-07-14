"""Parse rooms/ambientes from portal card text, titles, and URL slugs (E22)."""

from __future__ import annotations

import re

_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(\d+)\s*-ambientes?\b", re.I),
    re.compile(r"(\d+)\s*ambientes?\b", re.I),
    re.compile(r"(\d+)\s*amb\b", re.I),
    re.compile(r"(\d+)\s*dormitorios?\b", re.I),
    re.compile(r"(\d+)\s*hab(?:itaciones?)?\b", re.I),
    re.compile(r"(\d+)\s*rec\.?\b", re.I),  # Century21 "3 Rec."
)


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
    return None


def rooms_min_from_filters(filters) -> int | None:
    rooms = getattr(filters, "rooms", None)
    if rooms is None:
        return None
    return getattr(rooms, "min", None)

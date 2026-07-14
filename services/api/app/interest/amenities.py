"""Interest amenitiesHighlight helpers (API_CONTRACT E9)."""

from __future__ import annotations

from app.schemas.interest import AmenityHighlight

# Orden fijo: pileta, jardin, luego cochera/quincho (máx 4). Siempre pileta+jardin.
HIGHLIGHT_SPEC: list[tuple[str, str]] = [
    ("pileta", "Pileta"),
    ("jardin", "Jardín/parque"),
    ("cochera", "Cochera"),
    ("quincho", "Quincho"),
]


def amenities_highlight(amenities: list[str] | None) -> list[AmenityHighlight]:
    present = {a.lower() for a in (amenities or [])}
    # Always include pileta + jardin; fill up to 4
    out: list[AmenityHighlight] = []
    for token, label in HIGHLIGHT_SPEC:
        out.append(
            AmenityHighlight(
                token=token,
                label=label,
                present=token in present,
            )
        )
        if len(out) >= 4:
            break
    return out

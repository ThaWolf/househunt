"""GET /geo/suggest ranking over static seed."""

from __future__ import annotations

from app.geo.normalize import normalize_geo_text
from app.geo.seed import GEO_SEED, GeoSeedPlace
from app.schemas.property import GeoPlace


def _to_geo_place(place: GeoSeedPlace) -> GeoPlace:
    return GeoPlace(
        query=place.label,
        locality=place.locality,
        district=place.district,
        province=place.province,
        country=place.country,
        place_id=place.place_id,
        label=place.label,
        aliases=list(place.aliases),
    )


def suggest_places(q: str, *, limit: int = 8) -> list[GeoPlace]:
    needle = normalize_geo_text(q)
    if not needle:
        return []

    ranked: list[tuple[int, GeoSeedPlace]] = []
    for place in GEO_SEED:
        loc_n = normalize_geo_text(place.locality)
        label_n = normalize_geo_text(place.label)
        aliases_n = [normalize_geo_text(a) for a in place.aliases]

        score: int | None = None
        if loc_n.startswith(needle) or needle.startswith(loc_n):
            score = 300
        elif any(a.startswith(needle) or needle.startswith(a) for a in aliases_n if a):
            score = 200
        elif needle in loc_n or any(needle in a for a in aliases_n):
            score = 150
        elif needle in label_n:
            score = 100
        if score is not None:
            # slight bonus for exact locality
            if loc_n == needle:
                score += 50
            ranked.append((score, place))

    ranked.sort(key=lambda x: (-x[0], x[1].label))
    return [_to_geo_place(p) for _, p in ranked[:limit]]

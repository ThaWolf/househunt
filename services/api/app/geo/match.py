"""Listing ↔ Location geo match (DOMAIN §2.3)."""

from __future__ import annotations

from app.geo.normalize import normalize_geo_text
from app.geo.seed import LA_PLATA_CHILD_LOCALITIES, GEO_SEED, find_seed_by_locality
from app.schemas.property import Location


def _haystack(
    *,
    locality: str | None,
    neighborhood: str | None,
    raw: str | None,
    title: str | None,
) -> str:
    return normalize_geo_text(
        " ".join(x for x in (locality, neighborhood, raw, title) if x)
    )


def _tokens_for_place(locality: str, district: str | None, place_id: str | None) -> set[str]:
    tokens: set[str] = {normalize_geo_text(locality)}
    seed = None
    if place_id:
        seed = next((p for p in GEO_SEED if p.place_id == place_id), None)
    if seed is None:
        seed = find_seed_by_locality(locality)
    if seed:
        tokens.add(normalize_geo_text(seed.locality))
        tokens.update(normalize_geo_text(a) for a in seed.aliases)
    # Hard rule: Gonnet ≠ Pilar — never expand Gonnet to district siblings
    loc_n = normalize_geo_text(locality)
    if loc_n == "la plata" or (
        seed and normalize_geo_text(seed.locality) == "la plata"
    ):
        tokens |= set(LA_PLATA_CHILD_LOCALITIES)
        tokens.add("manuel belgrano gonnet")
        tokens.add("manuel b gonnet")
    elif district and normalize_geo_text(district) == "la plata" and loc_n == "la plata":
        tokens |= set(LA_PLATA_CHILD_LOCALITIES)
    return {t for t in tokens if t}


def location_matches_listing(
    location: Location,
    *,
    address_locality: str | None,
    address_neighborhood: str | None = None,
    address_raw: str | None = None,
    title: str | None = None,
) -> bool:
    """Return True if listing is inside the selected place."""
    hay = _haystack(
        locality=address_locality,
        neighborhood=address_neighborhood,
        raw=address_raw,
        title=title,
    )
    if not hay:
        return False

    loc_n = normalize_geo_text(location.locality)
    listing_loc = normalize_geo_text(address_locality)

    # Parent district expand: La Plata filter accepts Gonnet / City Bell / La Plata
    if loc_n == "la plata":
        if listing_loc in LA_PLATA_CHILD_LOCALITIES:
            return True
        # also accept via raw/title containing child tokens
        for child in LA_PLATA_CHILD_LOCALITIES:
            if child in hay:
                return True
        return False

    tokens = _tokens_for_place(location.locality, location.district, location.place_id)

    # Prefer locality field equality when present
    if listing_loc:
        if listing_loc in tokens:
            return True
        # Gonnet strict: Pilar must never pass
        if loc_n == "gonnet" and listing_loc == "pilar":
            return False
        if loc_n == "gonnet" and listing_loc not in tokens and "gonnet" not in listing_loc:
            # do not accept same-district City Bell for Gonnet filter
            if listing_loc == "city bell":
                return False

    for token in tokens:
        if not token:
            continue
        # whole-token-ish: containment in haystack
        if token in hay:
            # Guard: province alone is not enough — already not in tokens
            # Guard: "gonnet" filter must not match "pilar" via title alone when locality is Pilar
            if listing_loc and listing_loc == "pilar" and loc_n == "gonnet":
                return False
            return True

    return False

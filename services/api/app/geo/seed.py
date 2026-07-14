"""Static AR geo seed from DOMAIN §2.2."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GeoSeedPlace:
    place_id: str
    label: str
    locality: str
    district: str | None
    province: str
    country: str = "AR"
    aliases: tuple[str, ...] = field(default_factory=tuple)


# Minimal mandatory + recommended expansion (DOMAIN)
GEO_SEED: tuple[GeoSeedPlace, ...] = (
    GeoSeedPlace(
        place_id="ar-gonnet",
        label="Manuel B. Gonnet, La Plata, Buenos Aires",
        locality="Gonnet",
        district="La Plata",
        province="Buenos Aires",
        aliases=("gonnet", "manuel b gonnet", "manuel belgrano gonnet"),
    ),
    GeoSeedPlace(
        place_id="ar-city-bell",
        label="City Bell, La Plata, Buenos Aires",
        locality="City Bell",
        district="La Plata",
        province="Buenos Aires",
        aliases=("city bell",),
    ),
    GeoSeedPlace(
        place_id="ar-la-plata",
        label="La Plata, Buenos Aires",
        locality="La Plata",
        district="La Plata",
        province="Buenos Aires",
        aliases=("la plata",),
    ),
    GeoSeedPlace(
        place_id="ar-pilar",
        label="Pilar, Buenos Aires",
        locality="Pilar",
        district="Pilar",
        province="Buenos Aires",
        aliases=("pilar",),
    ),
    GeoSeedPlace(
        place_id="ar-tigre",
        label="Tigre, Buenos Aires",
        locality="Tigre",
        district="Tigre",
        province="Buenos Aires",
        aliases=("tigre",),
    ),
    GeoSeedPlace(
        place_id="ar-san-isidro",
        label="San Isidro, Buenos Aires",
        locality="San Isidro",
        district="San Isidro",
        province="Buenos Aires",
        aliases=("san isidro",),
    ),
    GeoSeedPlace(
        place_id="ar-vicente-lopez",
        label="Vicente López, Buenos Aires",
        locality="Vicente López",
        district="Vicente López",
        province="Buenos Aires",
        aliases=("vicente lopez", "olivos", "florida"),
    ),
    GeoSeedPlace(
        place_id="ar-san-fernando",
        label="San Fernando, Buenos Aires",
        locality="San Fernando",
        district="San Fernando",
        province="Buenos Aires",
        aliases=("san fernando",),
    ),
    GeoSeedPlace(
        place_id="ar-escobar",
        label="Escobar, Buenos Aires",
        locality="Escobar",
        district="Escobar",
        province="Buenos Aires",
        aliases=("escobar",),
    ),
    GeoSeedPlace(
        place_id="ar-moron",
        label="Morón, Buenos Aires",
        locality="Morón",
        district="Morón",
        province="Buenos Aires",
        aliases=("moron",),
    ),
    GeoSeedPlace(
        place_id="ar-caba",
        label="CABA",
        locality="CABA",
        district=None,
        province="CABA",
        aliases=("caba", "capital federal", "caba capital"),
    ),
    GeoSeedPlace(
        place_id="ar-palermo",
        label="Palermo, CABA",
        locality="Palermo",
        district=None,
        province="CABA",
        aliases=("palermo",),
    ),
    GeoSeedPlace(
        place_id="ar-belgrano",
        label="Belgrano, CABA",
        locality="Belgrano",
        district=None,
        province="CABA",
        aliases=("belgrano",),
    ),
    GeoSeedPlace(
        place_id="ar-nordelta",
        label="Nordelta, Tigre, Buenos Aires",
        locality="Nordelta",
        district="Tigre",
        province="Buenos Aires",
        aliases=("nordelta",),
    ),
    GeoSeedPlace(
        place_id="ar-martinez",
        label="Martínez, San Isidro, Buenos Aires",
        locality="Martínez",
        district="San Isidro",
        province="Buenos Aires",
        aliases=("martinez",),
    ),
    GeoSeedPlace(
        place_id="ar-quilmes",
        label="Quilmes, Buenos Aires",
        locality="Quilmes",
        district="Quilmes",
        province="Buenos Aires",
        aliases=("quilmes",),
    ),
    GeoSeedPlace(
        place_id="ar-lomas",
        label="Lomas de Zamora, Buenos Aires",
        locality="Lomas de Zamora",
        district="Lomas de Zamora",
        province="Buenos Aires",
        aliases=("lomas de zamora", "lomas"),
    ),
    GeoSeedPlace(
        place_id="ar-hurlingham",
        label="Hurlingham, Buenos Aires",
        locality="Hurlingham",
        district="Hurlingham",
        province="Buenos Aires",
        aliases=("hurlingham",),
    ),
)


# Parent district expand (E6): filter locality La Plata includes children
LA_PLATA_CHILD_LOCALITIES = frozenset({"la plata", "gonnet", "city bell"})


def find_seed_by_locality(locality: str) -> GeoSeedPlace | None:
    from app.geo.normalize import normalize_geo_text

    key = normalize_geo_text(locality)
    for place in GEO_SEED:
        if normalize_geo_text(place.locality) == key:
            return place
        if key in {normalize_geo_text(a) for a in place.aliases}:
            return place
    return None

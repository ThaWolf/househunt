"""Build ZoneReport from locality seed."""

from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.types import RawProperty
from app.schemas.common import GeocodeSource, GeocodeStatus, ZonePlaceSource, ZoneProvider
from app.schemas.property import ZoneGeo, ZonePlace, ZoneReport
from app.zone.seed_data import centroid_for, seeds_for


def build_zone_report(raw: RawProperty) -> ZoneReport:
    lat = raw.geo_lat
    lng = raw.geo_lng
    geocode_status = GeocodeStatus.missing
    geocode_source: GeocodeSource | None = None
    centroid = centroid_for(raw.address_locality)

    if lat is not None and lng is not None:
        # P0-4 (iter-11): extract may have persisted a seed centroid onto
        # geo_lat/geo_lng when the portal gave no real coords (so downstream
        # consumers reading the row directly still get a usable point). Detect
        # that case by exact match against the seed table so the report keeps
        # calling it "approximate/seed_locality" instead of a false "exact".
        if centroid is not None and (lat, lng) == centroid:
            geocode_status = GeocodeStatus.approximate
            geocode_source = GeocodeSource.seed_locality
        else:
            geocode_status = GeocodeStatus.exact
            geocode_source = GeocodeSource.portal
    elif centroid:
        lat, lng = centroid
        geocode_status = GeocodeStatus.approximate
        geocode_source = GeocodeSource.seed_locality

    poi: list[ZonePlace] = []
    commerce: list[ZonePlace] = []
    transit: list[ZonePlace] = []
    for seed in seeds_for(raw.address_locality):
        place = ZonePlace(
            id=seed.id,
            name=seed.name,
            category=seed.category,
            lat=seed.lat,
            lng=seed.lng,
            distance_m=seed.distance_m,
            source=ZonePlaceSource.seed,
        )
        if seed.bucket == "poi":
            poi.append(place)
        elif seed.bucket == "commerce":
            commerce.append(place)
        else:
            transit.append(place)

    locality = raw.address_locality or "la zona"
    summary = (
        f"Entorno de {locality}: {len(poi)} puntos de interés, "
        f"{len(commerce)} comercios y {len(transit)} opciones de transporte (seed MVP)."
    )

    return ZoneReport(
        summary=summary,
        poi=poi,
        commerce=commerce,
        transit=transit,
        geo=ZoneGeo(
            lat=lat,
            lng=lng,
            geocode_status=geocode_status,
            geocode_source=geocode_source,
        ),
        generated_at=datetime.now(timezone.utc),
        provider=ZoneProvider.seed,
    )

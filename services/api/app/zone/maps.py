"""MapEmbed URL helpers — embed only when Maps key is valid."""

from __future__ import annotations

from urllib.parse import quote_plus

from app.adapters.types import RawProperty
from app.config import Settings, get_settings
from app.schemas.common import GeoPoint, MapPinKind, MapProvider
from app.schemas.property import MapEmbed, MapPin, ZoneReport
from app.zone.seed_data import centroid_for


def _external_url(*, lat: float | None, lng: float | None, query: str | None) -> str:
    if lat is not None and lng is not None:
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    q = quote_plus(query or "Argentina")
    return f"https://www.google.com/maps/search/?api=1&query={q}"


def _embed_url(*, lat: float, lng: float, api_key: str, zoom: int = 14) -> str:
    return (
        "https://www.google.com/maps/embed/v1/view"
        f"?key={api_key}&center={lat},{lng}&zoom={zoom}&maptype=roadmap"
    )


def build_map_embed(
    raw: RawProperty,
    zone: ZoneReport | None = None,
    *,
    settings: Settings | None = None,
) -> MapEmbed:
    settings = settings or get_settings()

    lat = raw.geo_lat
    lng = raw.geo_lng
    if (lat is None or lng is None) and zone and zone.geo.lat is not None:
        lat, lng = zone.geo.lat, zone.geo.lng
    if lat is None or lng is None:
        centroid = centroid_for(raw.address_locality)
        if centroid:
            lat, lng = centroid

    query = raw.address_raw or raw.address_locality or raw.title
    external = _external_url(lat=lat, lng=lng, query=query)

    pins: list[MapPin] = []
    if lat is not None and lng is not None:
        pins.append(
            MapPin(
                id=f"listing-{raw.external_id}",
                lat=lat,
                lng=lng,
                label=raw.title[:80],
                kind=MapPinKind.listing,
            )
        )
    if zone:
        for place in (zone.poi + zone.commerce + zone.transit)[:8]:
            if place.lat is None or place.lng is None:
                continue
            kind = MapPinKind.poi
            if place in zone.commerce:
                kind = MapPinKind.commerce
            elif place in zone.transit:
                kind = MapPinKind.transit
            pins.append(
                MapPin(
                    id=place.id,
                    lat=place.lat,
                    lng=place.lng,
                    label=place.name,
                    kind=kind,
                )
            )

    use_embed = settings.effective_google_maps() and lat is not None and lng is not None
    embed_url = None
    provider = MapProvider.external_only
    if use_embed and settings.google_maps_api_key:
        embed_url = _embed_url(lat=lat, lng=lng, api_key=settings.google_maps_api_key)
        provider = MapProvider.google_embed

    # Contract requires center lat/lng; fall back to Buenos Aires approx if missing
    center_lat = lat if lat is not None else -34.6037
    center_lng = lng if lng is not None else -58.3816

    return MapEmbed(
        center=GeoPoint(lat=center_lat, lng=center_lng),
        zoom=14,
        pins=pins,
        embed_url=embed_url,
        external_url=external,
        provider=provider,
    )

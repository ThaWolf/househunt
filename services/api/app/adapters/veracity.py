"""Listing fidelity / ban-list helpers (DOMAIN §16 · E20)."""

from __future__ import annotations

from urllib.parse import urlparse

from app.schemas.common import DataSource, PortalId

# Stock / placeholder CDNs forbidden as kind=source (or proxied origin)
BANNED_IMAGE_HOST_PATTERNS: tuple[str, ...] = (
    "picsum.photos",
    "placeholder.com",
    "via.placeholder.com",
    "loremflickr.com",
    "placekitten.com",
    "placehold.co",
    "placehold.it",
    "dummyimage.com",
    "lorempixel.com",
    "source.unsplash.com",
    "images.unsplash.com",
    "unsplash.com",
)

# Fake fabricated portal paths from iter-3 fixtures
BANNED_SOURCE_URL_PATTERNS: tuple[str, ...] = (
    "/propiedades/zp-",
    "/propiedades/ap-",
    "/propiedades/ml-",
    "/propiedades/rx-",
    "/propiedades/c21-",
)

PORTAL_SOURCE_HOSTS: dict[PortalId, tuple[str, ...]] = {
    PortalId.zonaprop: ("zonaprop.com.ar",),
    PortalId.argenprop: ("argenprop.com",),
    PortalId.mercadolibre: (
        "mercadolibre.com.ar",
        "mercado.com",
        "casa.mercadolibre.com.ar",
    ),
    PortalId.remax: ("remax.com.ar",),
    PortalId.century21: ("century21.com.ar",),
}

PORTAL_IMAGE_HOST_SUFFIXES: dict[PortalId, tuple[str, ...]] = {
    PortalId.zonaprop: ("zonapropcdn.com", "zonaprop.com.ar", "naventcdn.com"),
    PortalId.argenprop: ("argenprop.com",),
    PortalId.mercadolibre: ("mlstatic.com", "mercadolibre.com", "mercadolibre.com.ar"),
    # E26: Remax CloudFront listing CDN + imgs subdomain
    PortalId.remax: ("remax.com.ar", "cloudfront.net", "imgs.remax.com.ar"),
    PortalId.century21: ("century21.com.ar", "21online.lat", "cdn.21online.lat"),
}

HOUSEHUNT_PLACEHOLDER_URL = "/placeholder-listing.svg"


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def is_banned_image_host(url: str) -> bool:
    host = host_of(url)
    if not host:
        return False
    for pattern in BANNED_IMAGE_HOST_PATTERNS:
        if host == pattern or host.endswith("." + pattern) or pattern in host:
            return True
    return False


def is_fake_source_url(url: str) -> bool:
    lowered = (url or "").lower()
    return any(p in lowered for p in BANNED_SOURCE_URL_PATTERNS)


def source_url_matches_portal(portal: PortalId, url: str) -> bool:
    host = host_of(url)
    if not host:
        return False
    allowed = PORTAL_SOURCE_HOSTS.get(portal, ())
    return any(host == h or host.endswith("." + h) for h in allowed)


def image_host_ok_for_portal(portal: PortalId, url: str) -> bool:
    if is_banned_image_host(url):
        return False
    host = host_of(url)
    if not host:
        return False
    suffixes = PORTAL_IMAGE_HOST_SUFFIXES.get(portal, ())
    return any(host == s or host.endswith("." + s) for s in suffixes)


def normalize_data_source(value: str | DataSource | None) -> DataSource:
    if isinstance(value, DataSource):
        return value
    if value in ("live", "fixture_curated", "demo_stub"):
        return DataSource(value)
    return DataSource.live

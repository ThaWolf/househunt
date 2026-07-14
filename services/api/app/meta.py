from fastapi import APIRouter, Depends

from app.adapters.registry import all_adapters
from app.auth.deps import get_current_user
from app.config import get_settings
from app.db.models import User
from app.schemas.interest import AdaptersMetaResponse, PortalMeta

router = APIRouter(tags=["meta"])

_DEFAULT_MATURITY = {
    "zonaprop": "live_partial",
    "mercadolibre": "live_partial",
    "argenprop": "live_ok",
    "remax": "live_ok",
    "century21": "live_ok",
}


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {"status": "ok", "version": settings.app_version}


@router.get("/meta/adapters", response_model=AdaptersMetaResponse)
async def adapters_meta(user: User = Depends(get_current_user)) -> AdaptersMetaResponse:
    _ = user
    settings = get_settings()
    portals = []
    for portal, adapter in all_adapters().items():
        analysis = getattr(adapter, "analysis_status", settings.analysis_status(portal.value))
        maturity = getattr(adapter, "maturity", None) or _DEFAULT_MATURITY.get(
            portal.value, "live_partial"
        )
        portals.append(
            PortalMeta(
                id=portal.value,
                enabled=settings.adapter_enabled(portal.value),
                analysis_status=analysis,
                maturity=maturity,
                hybrid_default=settings.adapter_hybrid_default,
            )
        )
    return AdaptersMetaResponse(
        portals=portals,
        features={
            "googleCalendar": settings.effective_google_calendar(),
            "googleMaps": settings.effective_google_maps(),
            "imageProxy": settings.feature_image_proxy,
            "poi": settings.feature_poi,
            "hybridAdapters": settings.adapter_hybrid_default,
        },
    )

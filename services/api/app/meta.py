from fastapi import APIRouter, Depends

from app.adapters.registry import all_adapters
from app.auth.deps import get_current_user
from app.config import get_settings
from app.db.models import User
from app.schemas.interest import AdaptersMetaResponse, PortalMeta

router = APIRouter(tags=["meta"])


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
        portals.append(
            PortalMeta(
                id=portal.value,
                enabled=settings.adapter_enabled(portal.value),
                analysis_status=getattr(adapter, "analysis_status", settings.analysis_status(portal.value)),
            )
        )
    return AdaptersMetaResponse(
        portals=portals,
        features={
            "googleCalendar": settings.effective_google_calendar(),
            "imageProxy": settings.feature_image_proxy,
            "poi": settings.feature_poi,
        },
    )

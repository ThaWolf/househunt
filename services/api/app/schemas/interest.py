"""Interest and visit DTOs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import (
    CamelModel,
    InterestState,
    PageMeta,
    Visit,
    VisitStatus,
)
from app.schemas.property import PropertyDTO


class InterestItem(CamelModel):
    id: UUID
    property: PropertyDTO
    state: InterestState
    user_score: int | None = None
    visit: Visit
    comments: str | None = None
    comment_flag: bool = False
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class InterestListResponse(CamelModel):
    items: list[InterestItem]
    meta: PageMeta


class CreateInterestRequest(CamelModel):
    property_id: UUID


class PatchInterestRequest(CamelModel):
    user_score: int | None = Field(default=None, ge=1, le=10)
    comments: str | None = None


class VisitUpsertRequest(CamelModel):
    status: VisitStatus
    at: datetime | None = None


class VisitListItem(CamelModel):
    property_id: UUID
    interest_id: UUID | None = None
    title: str | None = None
    visit: Visit


class VisitListResponse(CamelModel):
    items: list[VisitListItem]
    meta: PageMeta


class CalendarEvent(CamelModel):
    interest_id: UUID
    property_id: UUID
    title: str
    source_url: str
    visit: Visit
    google_event_id: str | None = None


class CalendarResponse(CamelModel):
    events: list[CalendarEvent]


class CalendarSyncRequest(CamelModel):
    interest_ids: list[UUID] | None = None


class CalendarSyncResponse(CamelModel):
    synced: int = 0
    failed: int = 0
    errors: list[dict] = Field(default_factory=list)


class PortalMeta(CamelModel):
    id: str
    enabled: bool
    analysis_status: str


class AdaptersMetaResponse(CamelModel):
    portals: list[PortalMeta]
    features: dict[str, bool]

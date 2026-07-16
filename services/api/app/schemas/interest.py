"""Interest and visit DTOs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import (
    CamelModel,
    InterestState,
    ListMemberRole,
    PageMeta,
    Visit,
    VisitStatus,
)
from app.schemas.property import PropertyDTO


class AmenityHighlight(CamelModel):
    token: str
    label: str
    present: bool


class AddedByUser(CamelModel):
    user_id: UUID
    display_name: str | None = None
    email: str


class InterestItem(CamelModel):
    id: UUID
    property: PropertyDTO
    state: InterestState
    rooms: int | None = None
    amenities_highlight: list[AmenityHighlight] = Field(default_factory=list)
    user_score: int | None = None
    visit: Visit
    comments: str | None = None
    comment_flag: bool = False
    added_by: AddedByUser | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class InterestListResponse(CamelModel):
    items: list[InterestItem]
    meta: PageMeta


class CreateInterestRequest(CamelModel):
    property_id: UUID
    list_id: UUID | None = None


class ExternalInterestRequest(CamelModel):
    """iter-9: agregar una publicación externa por URL a intereses."""

    url: str = Field(min_length=8, max_length=2048)
    list_id: UUID | None = None


class PatchInterestRequest(CamelModel):
    user_score: int | None = Field(default=None, ge=1, le=10)
    comments: str | None = None


class VisitUpsertRequest(CamelModel):
    status: VisitStatus
    at: datetime | None = None
    list_id: UUID | None = None


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
    list_id: UUID | None = None


class InterestListSummary(CamelModel):
    id: UUID
    name: str
    role: ListMemberRole
    member_count: int


class InterestListsResponse(CamelModel):
    items: list[InterestListSummary]


class ListMember(CamelModel):
    user_id: UUID
    email: str
    display_name: str | None = None
    role: ListMemberRole
    joined_at: datetime


class InterestListDetail(CamelModel):
    id: UUID
    name: str
    owner_user_id: UUID
    members: list[ListMember]


class InviteMemberRequest(CamelModel):
    email: str = Field(min_length=3, max_length=320)


class CalendarSyncResponse(CamelModel):
    synced: int = 0
    failed: int = 0
    errors: list[dict] = Field(default_factory=list)


class PortalMeta(CamelModel):
    id: str
    enabled: bool
    analysis_status: str
    maturity: str | None = None
    hybrid_default: bool = True


class AdaptersMetaResponse(CamelModel):
    portals: list[PortalMeta]
    features: dict[str, bool]

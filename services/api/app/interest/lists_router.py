"""CRUD for shared interest lists and members."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.deps import get_current_user
from app.db import models
from app.db.base import get_db
from app.db.models import User
from app.errors import AppError
from app.interest.deps import ensure_default_list, require_membership, require_owner
from app.schemas.common import ListMemberRole
from app.schemas.interest import (
    InterestListDetail,
    InterestListSummary,
    InterestListsResponse,
    InviteMemberRequest,
    ListMember,
)

router = APIRouter(prefix="/interest/lists", tags=["interest-lists"])


@router.get("", response_model=InterestListsResponse)
async def list_my_lists(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterestListsResponse:
    await ensure_default_list(db, user.id)
    result = await db.execute(
        select(models.InterestListMember, models.InterestList)
        .join(models.InterestList, models.InterestListMember.list_id == models.InterestList.id)
        .where(models.InterestListMember.user_id == user.id)
        .order_by(models.InterestList.created_at.asc())
    )
    items: list[InterestListSummary] = []
    for member, lst in result.all():
        count = (
            await db.execute(
                select(func.count())
                .select_from(models.InterestListMember)
                .where(models.InterestListMember.list_id == lst.id)
            )
        ).scalar_one()
        items.append(
            InterestListSummary(
                id=lst.id,
                name=lst.name,
                role=ListMemberRole(member.role),
                member_count=count,
            )
        )
    return InterestListsResponse(items=items)


@router.get("/{list_id}", response_model=InterestListDetail)
async def get_list_detail(
    list_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterestListDetail:
    await require_membership(db, user.id, list_id)
    lst = (
        await db.execute(
            select(models.InterestList)
            .where(models.InterestList.id == list_id)
            .options(selectinload(models.InterestList.members).selectinload(models.InterestListMember.user))
        )
    ).scalar_one_or_none()
    if lst is None:
        raise AppError(404, "not_found", "List not found")
    members = [
        ListMember(
            user_id=m.user_id,
            email=m.user.email,
            display_name=m.user.display_name,
            role=ListMemberRole(m.role),
            joined_at=m.joined_at,
        )
        for m in lst.members
    ]
    return InterestListDetail(
        id=lst.id,
        name=lst.name,
        owner_user_id=lst.owner_user_id,
        members=members,
    )


@router.post("/{list_id}/members", response_model=ListMember, status_code=201)
async def invite_member(
    list_id: UUID,
    body: InviteMemberRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ListMember:
    await require_owner(db, user.id, list_id)
    email_n = body.email.strip().lower()
    invitee = (
        await db.execute(select(User).where(User.email == email_n))
    ).scalar_one_or_none()
    if invitee is None:
        raise AppError(
            422,
            "user_not_found",
            "La persona debe crear cuenta en Househunt primero",
        )

    existing = (
        await db.execute(
            select(models.InterestListMember).where(
                models.InterestListMember.list_id == list_id,
                models.InterestListMember.user_id == invitee.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise AppError(409, "already_member", "User is already a member of this list")

    member = models.InterestListMember(
        list_id=list_id,
        user_id=invitee.id,
        role=ListMemberRole.collaborator.value,
    )
    db.add(member)
    await db.flush()
    return ListMember(
        user_id=invitee.id,
        email=invitee.email,
        display_name=invitee.display_name,
        role=ListMemberRole.collaborator,
        joined_at=member.joined_at,
    )


@router.delete("/{list_id}/members/{member_user_id}", status_code=204)
async def remove_member(
    list_id: UUID,
    member_user_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await require_owner(db, user.id, list_id)
    if member_user_id == user.id:
        raise AppError(400, "validation_error", "Owner cannot remove themselves")
    member = (
        await db.execute(
            select(models.InterestListMember).where(
                models.InterestListMember.list_id == list_id,
                models.InterestListMember.user_id == member_user_id,
            )
        )
    ).scalar_one_or_none()
    if member is None:
        raise AppError(404, "not_found", "Member not found")
    if member.role == ListMemberRole.owner.value:
        raise AppError(400, "validation_error", "Cannot remove list owner")
    await db.delete(member)

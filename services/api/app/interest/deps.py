"""Interest list membership helpers."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.models import User
from app.errors import AppError
from app.schemas.common import ListMemberRole


async def ensure_default_list(db: AsyncSession, user_id: UUID) -> models.InterestList:
    """Each user gets one owned list (MVP)."""
    owned = (
        await db.execute(
            select(models.InterestList).where(models.InterestList.owner_user_id == user_id)
        )
    ).scalar_one_or_none()
    if owned is not None:
        return owned

    lst = models.InterestList(owner_user_id=user_id, name="Mi lista")
    db.add(lst)
    await db.flush()
    db.add(
        models.InterestListMember(
            list_id=lst.id,
            user_id=user_id,
            role=ListMemberRole.owner.value,
        )
    )
    await db.flush()
    return lst


async def get_membership(
    db: AsyncSession, user_id: UUID, list_id: UUID
) -> models.InterestListMember | None:
    return (
        await db.execute(
            select(models.InterestListMember).where(
                models.InterestListMember.list_id == list_id,
                models.InterestListMember.user_id == user_id,
            )
        )
    ).scalar_one_or_none()


async def require_membership(
    db: AsyncSession, user_id: UUID, list_id: UUID
) -> models.InterestListMember:
    member = await get_membership(db, user_id, list_id)
    if member is None:
        raise AppError(403, "forbidden", "Not a member of this interest list")
    return member


async def require_owner(
    db: AsyncSession, user_id: UUID, list_id: UUID
) -> models.InterestListMember:
    member = await require_membership(db, user_id, list_id)
    if member.role != ListMemberRole.owner.value:
        raise AppError(403, "forbidden", "Only the list owner can do this")
    return member


async def resolve_list_id(
    db: AsyncSession, user: User, list_id: UUID | None
) -> UUID:
    if list_id is not None:
        await require_membership(db, user.id, list_id)
        return list_id
    lst = await ensure_default_list(db, user.id)
    return lst.id


async def get_interest_for_list(
    db: AsyncSession, list_id: UUID, interest_id: UUID
) -> models.InterestItem:
    interest = await db.get(models.InterestItem, interest_id)
    if interest is None or interest.list_id != list_id:
        raise AppError(404, "not_found", "Interest not found")
    return interest

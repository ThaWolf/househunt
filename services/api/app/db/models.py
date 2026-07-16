"""Postgres models per ARCHITECTURE schema."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base

# Use JSON for sqlite tests; JSONB preferred on Postgres via dialect
JSONType = JSON().with_variant(JSONB(), "postgresql")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    refresh_tokens: Mapped[list[RefreshToken]] = relationship(back_populates="user")
    owned_lists: Mapped[list[InterestList]] = relationship(back_populates="owner")
    list_memberships: Mapped[list[InterestListMember]] = relationship(back_populates="user")
    added_interest_items: Mapped[list[InterestItem]] = relationship(
        back_populates="added_by", foreign_keys="InterestItem.added_by_user_id"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (UniqueConstraint("portal", "external_id", name="uq_portal_external"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portal: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    data_source: Mapped[str] = mapped_column(String(32), nullable=False, default="live")
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    operation: Mapped[str] = mapped_column(String(16), nullable=False, default="buy")
    property_type: Mapped[str] = mapped_column(String(32), nullable=False, default="house")
    price_amount: Mapped[float | None] = mapped_column(nullable=True)
    price_currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    address_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    address_province: Mapped[str | None] = mapped_column(String(128), nullable=True)
    address_locality: Mapped[str | None] = mapped_column(String(128), nullable=True)
    address_neighborhood: Mapped[str | None] = mapped_column(String(128), nullable=True)
    geo_lat: Mapped[float | None] = mapped_column(nullable=True)
    geo_lng: Mapped[float | None] = mapped_column(nullable=True)
    rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parking: Mapped[int | None] = mapped_column(Integer, nullable=True)
    area_covered_m2: Mapped[float | None] = mapped_column(nullable=True)
    area_total_m2: Mapped[float | None] = mapped_column(nullable=True)
    amenities: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    images: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    agent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agent_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    listed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    app_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_breakdown: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    raw_hints: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    interest_items: Mapped[list[InterestItem]] = relationship(back_populates="property")


class InterestList(Base):
    __tablename__ = "interest_lists"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="Mi lista")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner: Mapped[User] = relationship(back_populates="owned_lists")
    members: Mapped[list[InterestListMember]] = relationship(back_populates="list")
    interest_items: Mapped[list[InterestItem]] = relationship(back_populates="list")
    visits: Mapped[list[Visit]] = relationship(back_populates="list")


class InterestListMember(Base):
    __tablename__ = "interest_list_members"
    __table_args__ = (UniqueConstraint("list_id", "user_id", name="uq_list_member"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    list_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("interest_lists.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    list: Mapped[InterestList] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="list_memberships")


class InterestItem(Base):
    __tablename__ = "interest_items"
    __table_args__ = (UniqueConstraint("list_id", "property_id", name="uq_list_property_interest"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    list_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("interest_lists.id", ondelete="CASCADE"), index=True
    )
    added_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), index=True
    )
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="active", index=True)
    user_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    list: Mapped[InterestList] = relationship(back_populates="interest_items")
    added_by: Mapped[User] = relationship(
        back_populates="added_interest_items", foreign_keys=[added_by_user_id]
    )
    property: Mapped[Property] = relationship(back_populates="interest_items")


class Visit(Base):
    __tablename__ = "visits"
    __table_args__ = (UniqueConstraint("list_id", "property_id", name="uq_list_property_visit"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    list_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("interest_lists.id", ondelete="CASCADE"), index=True
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="none", index=True)
    at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    google_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    list: Mapped[InterestList] = relationship(back_populates="visits")

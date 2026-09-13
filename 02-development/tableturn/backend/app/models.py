"""SQLAlchemy ORM models.

Deliberately database-agnostic: generic types only, UUIDs stored as strings,
datetimes as DateTime(timezone=True). Swapping SQLite for Postgres must not
touch this file (see _docs/specs.md §10).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class PartyModel(Base):
    __tablename__ = "parties"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="waiting")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    seated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(16), nullable=True)

    table_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tables.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        # Rule R1: the waiting list is ordered by created_at then id.
        Index("ix_parties_status_created", "status", "created_at", "id"),
    )


class TableModel(Base):
    __tablename__ = "tables"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="free")
    occupied_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    occupied_by_party_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("parties.id", ondelete="SET NULL"), nullable=True
    )

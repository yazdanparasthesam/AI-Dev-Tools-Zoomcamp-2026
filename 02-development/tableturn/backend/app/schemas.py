"""Pydantic schemas. These mirror openapi.yaml exactly.

If you change a field here, change openapi.yaml in the same commit —
tests/test_contract.py will fail otherwise.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_serializer

# Business rule R2 (_docs/specs.md): every party ahead of you adds this many
# minutes to your estimate. Asserted in tests/test_rules.py.
MINUTES_PER_PARTY_AHEAD = 10


class PartyStatus(StrEnum):
    waiting = "waiting"
    seated = "seated"
    completed = "completed"
    cancelled = "cancelled"


class TableStatus(StrEnum):
    free = "free"
    occupied = "occupied"


class CancelReason(StrEnum):
    no_show = "no_show"
    walked = "walked"
    other = "other"


def ensure_utc(value: datetime | None) -> datetime | None:
    """Normalise to aware UTC.

    SQLite hands back naive datetimes (it stores no timezone); Postgres hands
    back aware ones. Normalising here keeps rule R10 true on both.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class TimestampedModel(BaseModel):
    """Serialises datetimes as ISO-8601 with a Z suffix (rule R10)."""

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("*", when_used="json")
    def _serialize_datetimes(self, value: object) -> object:
        if isinstance(value, datetime):
            return ensure_utc(value).isoformat().replace("+00:00", "Z")
        return value


class PartyCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=80)]
    party_size: Annotated[int, Field(ge=1, le=20)]
    phone: Annotated[str | None, Field(max_length=40)] = None
    notes: Annotated[str | None, Field(max_length=280)] = None


class PartyUpdate(BaseModel):
    """Partial update; only waiting parties can be edited (rule R7 family)."""

    name: Annotated[str | None, Field(min_length=1, max_length=80)] = None
    party_size: Annotated[int | None, Field(ge=1, le=20)] = None
    phone: Annotated[str | None, Field(max_length=40)] = None
    notes: Annotated[str | None, Field(max_length=280)] = None


class Party(TimestampedModel):
    id: str
    name: str
    party_size: int
    phone: str | None = None
    notes: str | None = None
    status: PartyStatus
    created_at: datetime
    seated_at: datetime | None = None
    table_id: str | None = None
    cancel_reason: str | None = None
    position: int | None = None
    estimated_wait_minutes: int | None = None


class SeatRequest(BaseModel):
    table_id: str


class CancelRequest(BaseModel):
    reason: CancelReason = CancelReason.other


class TableCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=60)]
    capacity: Annotated[int, Field(ge=1, le=20)]


class TableUpdate(BaseModel):
    name: Annotated[str | None, Field(min_length=1, max_length=60)] = None
    capacity: Annotated[int | None, Field(ge=1, le=20)] = None


class Table(TimestampedModel):
    id: str
    name: str
    capacity: int
    status: TableStatus
    occupied_by_party_id: str | None = None
    occupied_since: datetime | None = None


class Stats(BaseModel):
    waiting_count: int
    seated_count: int
    completed_count: int
    cancelled_count: int
    covers_waiting: int
    longest_wait_minutes: int
    average_wait_minutes: int
    free_tables: int
    occupied_tables: int
    free_seats: int


class Health(BaseModel):
    status: str = "ok"
    database: str = "ok"


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    """Shape of every domain error response (see backend/app/errors.py)."""

    error: ErrorDetail

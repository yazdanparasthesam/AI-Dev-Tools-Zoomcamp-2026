"""The domain layer: all business rules from _docs/specs.md §6 live here.

Routes never contain rules; they translate HTTP <-> store calls. The store
never imports FastAPI, which is what keeps the app database-agnostic.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.errors import (
    BlankNameError,
    PartyIsSeatedError,
    PartyNotFoundError,
    PartyNotWaitingError,
    TableNameTakenError,
    TableNotFoundError,
    TableNotOccupiedError,
    TableOccupiedError,
    TableTooSmallError,
)
from backend.app.models import PartyModel, TableModel
from backend.app.schemas import (
    MINUTES_PER_PARTY_AHEAD,
    CancelReason,
    Party,
    PartyCreate,
    PartyStatus,
    PartyUpdate,
    Stats,
    Table,
    TableCreate,
    TableStatus,
    TableUpdate,
    ensure_utc,
)

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


class WaitlistStore(Protocol):
    """The interface the API layer depends on.

    A different backend (in-memory mock, Postgres, a remote service) only has
    to satisfy this protocol — that is the "database-agnostic" seam.
    """

    def list_parties(self, status: PartyStatus | None = None) -> list[Party]: ...
    def create_party(self, data: PartyCreate) -> Party: ...
    def get_party(self, party_id: str) -> Party: ...
    def update_party(self, party_id: str, data: PartyUpdate) -> Party: ...
    def seat_party(self, party_id: str, table_id: str) -> Party: ...
    def cancel_party(self, party_id: str, reason: CancelReason) -> Party: ...
    def delete_party(self, party_id: str) -> None: ...
    def list_tables(self) -> list[Table]: ...
    def create_table(self, data: TableCreate) -> Table: ...
    def update_table(self, table_id: str, data: TableUpdate) -> Table: ...
    def free_table(self, table_id: str) -> Table: ...
    def delete_table(self, table_id: str) -> None: ...
    def stats(self) -> Stats: ...


def _waiting_positions(session: Session) -> dict[str, int]:
    """Rule R1: waiting list ordered by created_at, then id as tie-breaker."""
    ids = session.execute(
        select(PartyModel.id)
        .where(PartyModel.status == PartyStatus.waiting.value)
        .order_by(PartyModel.created_at, PartyModel.id)
    ).scalars()
    return {party_id: index + 1 for index, party_id in enumerate(ids)}


def _to_party(party: PartyModel, positions: dict[str, int]) -> Party:
    position = positions.get(party.id) if party.status == PartyStatus.waiting.value else None
    estimate = (position - 1) * MINUTES_PER_PARTY_AHEAD if position is not None else None
    return Party(
        id=party.id,
        name=party.name,
        party_size=party.party_size,
        phone=party.phone,
        notes=party.notes,
        status=PartyStatus(party.status),
        created_at=ensure_utc(party.created_at),
        seated_at=ensure_utc(party.seated_at),
        table_id=party.table_id,
        cancel_reason=party.cancel_reason,
        position=position,
        estimated_wait_minutes=estimate,
    )


def _to_table(table: TableModel) -> Table:
    return Table(
        id=table.id,
        name=table.name,
        capacity=table.capacity,
        status=TableStatus(table.status),
        occupied_by_party_id=table.occupied_by_party_id,
        occupied_since=ensure_utc(table.occupied_since),
    )


class SqlAlchemyStore:
    """SQLAlchemy implementation of `WaitlistStore`."""

    def __init__(self, session_factory: sessionmaker[Session], clock: Clock = utc_now) -> None:
        self._session_factory = session_factory
        self._clock = clock

    def _now(self) -> datetime:
        return self._clock()

    # -- lookups ---------------------------------------------------------

    @staticmethod
    def _party_or_raise(session: Session, party_id: str) -> PartyModel:
        party = session.get(PartyModel, party_id)
        if party is None:
            raise PartyNotFoundError(party_id)
        return party

    @staticmethod
    def _table_or_raise(session: Session, table_id: str) -> TableModel:
        table = session.get(TableModel, table_id)
        if table is None:
            raise TableNotFoundError(table_id)
        return table

    # -- parties ---------------------------------------------------------

    def list_parties(self, status: PartyStatus | None = None) -> list[Party]:
        with self._session_factory() as session:
            positions = _waiting_positions(session)
            stmt = select(PartyModel)
            if status is not None:
                stmt = stmt.where(PartyModel.status == status.value)
            stmt = stmt.order_by(PartyModel.created_at, PartyModel.id)
            parties = session.execute(stmt).scalars().all()
            # R5: positions/estimates are recomputed on every read, so seating
            # or cancelling a party moves everyone behind it up automatically.
            return [_to_party(party, positions) for party in parties]

    def create_party(self, data: PartyCreate) -> Party:
        now = self._now()
        name = data.name.strip()
        if not name:
            raise BlankNameError("name")
        with self._session_factory() as session:
            party = PartyModel(
                name=name,
                party_size=data.party_size,
                phone=data.phone.strip() if data.phone else None,
                notes=data.notes.strip() if data.notes else None,
                status=PartyStatus.waiting.value,
                created_at=now,
            )
            session.add(party)
            session.commit()
            return _to_party(party, _waiting_positions(session))

    def get_party(self, party_id: str) -> Party:
        with self._session_factory() as session:
            party = self._party_or_raise(session, party_id)
            return _to_party(party, _waiting_positions(session))

    def update_party(self, party_id: str, data: PartyUpdate) -> Party:
        changes = data.model_dump(exclude_unset=True)
        with self._session_factory() as session:
            party = self._party_or_raise(session, party_id)
            if party.status != PartyStatus.waiting.value:
                raise PartyNotWaitingError(party.status)

            for field, value in changes.items():
                if field in {"phone", "notes"} and isinstance(value, str):
                    value = value.strip() or None
                if field == "name" and isinstance(value, str):
                    value = value.strip()
                    if not value:
                        raise BlankNameError("name")
                setattr(party, field, value)

            session.commit()
            return _to_party(party, _waiting_positions(session))

    def seat_party(self, party_id: str, table_id: str) -> Party:
        """Rule R3 + R4 + R5."""
        now = self._now()
        with self._session_factory() as session:
            party = self._party_or_raise(session, party_id)
            if party.status != PartyStatus.waiting.value:
                raise PartyNotWaitingError(party.status)

            table = self._table_or_raise(session, table_id)
            if table.status != TableStatus.free.value:
                raise TableOccupiedError(table.name)
            if table.capacity < party.party_size:
                raise TableTooSmallError(table.name, table.capacity, party.party_size)

            party.status = PartyStatus.seated.value
            party.seated_at = now
            party.table_id = table.id

            table.status = TableStatus.occupied.value
            table.occupied_by_party_id = party.id
            table.occupied_since = now

            session.commit()
            return _to_party(party, _waiting_positions(session))

    def cancel_party(self, party_id: str, reason: CancelReason) -> Party:
        """Rule R7: only from `waiting`."""
        with self._session_factory() as session:
            party = self._party_or_raise(session, party_id)
            if party.status != PartyStatus.waiting.value:
                raise PartyNotWaitingError(party.status)
            party.status = PartyStatus.cancelled.value
            party.cancel_reason = reason.value
            session.commit()
            return _to_party(party, _waiting_positions(session))

    def delete_party(self, party_id: str) -> None:
        with self._session_factory() as session:
            party = self._party_or_raise(session, party_id)
            if party.status == PartyStatus.seated.value:
                # Deleting would leave an occupied table pointing at nothing.
                raise PartyIsSeatedError()
            session.delete(party)
            session.commit()

    # -- tables ----------------------------------------------------------

    def list_tables(self) -> list[Table]:
        with self._session_factory() as session:
            tables = session.execute(select(TableModel).order_by(TableModel.name)).scalars().all()
            return [_to_table(table) for table in tables]

    def create_table(self, data: TableCreate) -> Table:
        name = data.name.strip()
        if not name:
            raise BlankNameError("name")
        with self._session_factory() as session:
            self._assert_name_free(session, name)
            table = TableModel(
                name=name,
                capacity=data.capacity,
                status=TableStatus.free.value,
            )
            session.add(table)
            session.commit()
            return _to_table(table)

    def update_table(self, table_id: str, data: TableUpdate) -> Table:
        changes = data.model_dump(exclude_unset=True)
        with self._session_factory() as session:
            table = self._table_or_raise(session, table_id)

            new_name = changes.get("name")
            if isinstance(new_name, str):
                new_name = new_name.strip()
                if not new_name:
                    raise BlankNameError("name")
                if new_name != table.name:
                    self._assert_name_free(session, new_name, exclude_id=table.id)
                table.name = new_name

            new_capacity = changes.get("capacity")
            if new_capacity is not None:
                if table.status == TableStatus.occupied.value and table.occupied_by_party_id:
                    occupant = session.get(PartyModel, table.occupied_by_party_id)
                    if occupant is not None and new_capacity < occupant.party_size:
                        raise TableTooSmallError(table.name, new_capacity, occupant.party_size)
                table.capacity = new_capacity

            session.commit()
            return _to_table(table)

    def free_table(self, table_id: str) -> Table:
        """Rule R6: turning a table completes the party sitting at it."""
        with self._session_factory() as session:
            table = self._table_or_raise(session, table_id)
            if table.status != TableStatus.occupied.value:
                raise TableNotOccupiedError(table.name)

            if table.occupied_by_party_id:
                party = session.get(PartyModel, table.occupied_by_party_id)
                if party is not None:
                    party.status = PartyStatus.completed.value
                    party.table_id = table.id

            table.status = TableStatus.free.value
            table.occupied_by_party_id = None
            table.occupied_since = None

            session.commit()
            return _to_table(table)

    def delete_table(self, table_id: str) -> None:
        """Rule R8: occupied tables cannot be deleted."""
        with self._session_factory() as session:
            table = self._table_or_raise(session, table_id)
            if table.status == TableStatus.occupied.value:
                raise TableOccupiedError(table.name)

            # Clear historical references so no party keeps a dangling table_id.
            referencing = session.execute(
                select(PartyModel).where(PartyModel.table_id == table.id)
            ).scalars()
            for party in referencing:
                party.table_id = None

            session.delete(table)
            session.commit()

    @staticmethod
    def _assert_name_free(session: Session, name: str, exclude_id: str | None = None) -> None:
        stmt = select(TableModel.id).where(func.lower(TableModel.name) == name.lower())
        if exclude_id is not None:
            stmt = stmt.where(TableModel.id != exclude_id)
        if session.execute(stmt).first() is not None:
            raise TableNameTakenError(name)

    # -- stats -----------------------------------------------------------

    def stats(self) -> Stats:
        now = self._now()
        with self._session_factory() as session:
            parties: Sequence[PartyModel] = session.execute(select(PartyModel)).scalars().all()
            tables: Sequence[TableModel] = session.execute(select(TableModel)).scalars().all()

            waiting = [p for p in parties if p.status == PartyStatus.waiting.value]
            seated = [p for p in parties if p.status == PartyStatus.seated.value]
            completed = [p for p in parties if p.status == PartyStatus.completed.value]
            cancelled = [p for p in parties if p.status == PartyStatus.cancelled.value]

            longest_wait = 0
            if waiting:
                oldest = min(ensure_utc(p.created_at) for p in waiting)
                longest_wait = max(0, int((now - oldest).total_seconds() // 60))

            # R9: mean of seated_at - created_at over seated + completed.
            waits = [
                (ensure_utc(p.seated_at) - ensure_utc(p.created_at)).total_seconds() / 60
                for p in (*seated, *completed)
                if p.seated_at is not None
            ]
            average_wait = int(round(sum(waits) / len(waits))) if waits else 0

            free_tables = [t for t in tables if t.status == TableStatus.free.value]
            return Stats(
                waiting_count=len(waiting),
                seated_count=len(seated),
                completed_count=len(completed),
                cancelled_count=len(cancelled),
                covers_waiting=sum(p.party_size for p in waiting),
                longest_wait_minutes=longest_wait,
                average_wait_minutes=average_wait,
                free_tables=len(free_tables),
                occupied_tables=len(tables) - len(free_tables),
                free_seats=sum(t.capacity for t in free_tables),
            )

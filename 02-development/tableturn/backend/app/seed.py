"""Demo seed data.

Only runs against an empty database and only when SEED_DEMO_DATA is true, so a
fresh clone shows something meaningful instead of an empty screen. Tests never
seed (create_app(seed=False)).
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database import Database
from backend.app.models import PartyModel, TableModel
from backend.app.store import Clock, utc_now

DEMO_TABLES: list[tuple[str, int]] = [
    ("T1", 2),
    ("T2", 4),
    ("T3", 4),
    ("Patio 1", 6),
]

# (name, party_size, notes, minutes_ago)
DEMO_PARTIES: list[tuple[str, int, str | None, int]] = [
    ("Ava", 4, "window seat if possible", 21),
    ("Marcus", 2, None, 12),
    ("The Okafor party", 6, "highchair, nut allergy", 4),
]


def database_is_empty(session: Session) -> bool:
    party_count = session.execute(select(func.count()).select_from(PartyModel)).scalar_one()
    table_count = session.execute(select(func.count()).select_from(TableModel)).scalar_one()
    return party_count == 0 and table_count == 0


def seed_demo_data(database: Database, clock: Clock = utc_now) -> bool:
    """Insert demo rows if the database is empty. Returns True if it seeded."""
    now = clock()
    with database.session_factory() as session:
        if not database_is_empty(session):
            return False

        session.add_all(
            TableModel(name=name, capacity=capacity, status="free")
            for name, capacity in DEMO_TABLES
        )
        session.add_all(
            PartyModel(
                name=name,
                party_size=size,
                notes=notes,
                status="waiting",
                created_at=now - timedelta(minutes=minutes_ago),
            )
            for name, size, notes, minutes_ago in DEMO_PARTIES
        )
        session.commit()
        return True

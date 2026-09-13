"""Shared fixtures.

Every test runs against an isolated in-memory SQLite database and a fake clock,
so nothing touches the developer's tableturn.db and no test depends on the
wall-clock time (rules R2/R9 make time observable).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.database import Database
from backend.app.main import create_app
from backend.app.store import SqlAlchemyStore

FIXED_NOW = datetime(2026, 9, 12, 18, 0, 0, tzinfo=UTC)


class FakeClock:
    """Deterministic stand-in for datetime.now(timezone.utc)."""

    def __init__(self, start: datetime = FIXED_NOW) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs: float) -> None:
        self.now += timedelta(**kwargs)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def database() -> Iterator[Database]:
    db = Database("sqlite://")
    db.create_all()
    try:
        yield db
    finally:
        db.dispose()


@pytest.fixture
def store(database: Database, clock: FakeClock) -> SqlAlchemyStore:
    """The store directly, for unit-level rule tests."""
    return SqlAlchemyStore(database.session_factory, clock=clock)


@pytest.fixture
def app(clock: FakeClock) -> FastAPI:
    return create_app(database_url="sqlite://", seed=False, clock=clock)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    # Entering the context runs the lifespan hook, which creates the tables.
    with TestClient(app) as test_client:
        yield test_client


def add_party(client: TestClient, name: str, size: int = 2, **kwargs) -> dict:
    response = client.post("/api/parties", json={"name": name, "party_size": size, **kwargs})
    assert response.status_code == 201, response.text
    return response.json()


def add_table(client: TestClient, name: str, capacity: int = 4) -> dict:
    response = client.post("/api/tables", json={"name": name, "capacity": capacity})
    assert response.status_code == 201, response.text
    return response.json()

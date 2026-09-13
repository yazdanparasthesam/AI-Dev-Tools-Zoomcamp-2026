"""Engine / session plumbing.

One `Database` object owns an engine and a sessionmaker. `create_app()` builds
one; tests build their own against an isolated in-memory SQLite database.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.models import Base


def build_engine(database_url: str) -> Engine:
    kwargs: dict = {"future": True}
    if database_url.startswith("sqlite"):
        # SQLite needs this to be usable from multiple threads (uvicorn) and,
        # for ":memory:", to share one connection across sessions in tests.
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in database_url or database_url.endswith("://"):
            kwargs["poolclass"] = StaticPool
    return create_engine(database_url, **kwargs)


class Database:
    def __init__(self, database_url: str) -> None:
        self.url = database_url
        self.engine = build_engine(database_url)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
            class_=Session,
        )

    def create_all(self) -> None:
        Base.metadata.create_all(self.engine)

    def drop_all(self) -> None:
        Base.metadata.drop_all(self.engine)

    def session(self) -> Iterator[Session]:
        with self.session_factory() as session:
            yield session

    def dispose(self) -> None:
        self.engine.dispose()

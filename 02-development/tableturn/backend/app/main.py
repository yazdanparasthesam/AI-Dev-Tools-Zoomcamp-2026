"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import router
from backend.app.config import get_settings
from backend.app.database import Database
from backend.app.errors import register_error_handlers
from backend.app.seed import seed_demo_data
from backend.app.store import Clock, SqlAlchemyStore, utc_now

APP_TITLE = "TableTurn API"
APP_VERSION = "1.0.0"


def create_app(
    database_url: str | None = None,
    seed: bool | None = None,
    cors_origins: Sequence[str] | None = None,
    clock: Clock = utc_now,
) -> FastAPI:
    """Build an app instance.

    Tests call this with an isolated in-memory database and `seed=False`;
    `main.py` calls it with no arguments to use the environment.
    """
    settings = get_settings()
    url = database_url or settings.database_url
    should_seed = settings.seed_demo_data if seed is None else seed

    database = Database(url)
    store = SqlAlchemyStore(database.session_factory, clock=clock)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database.create_all()
        if should_seed:
            seed_demo_data(database, clock=clock)
        try:
            yield
        finally:
            database.dispose()

    app = FastAPI(
        title=APP_TITLE,
        version=APP_VERSION,
        description="Host-side restaurant waitlist manager. Contract: openapi.yaml",
        lifespan=lifespan,
    )
    app.state.database = database
    app.state.store = store

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(cors_origins or settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(router)
    return app


# Module-level instance for `uvicorn backend.app.main:app`.
# Tests build their own via create_app() instead of using this one.
app = create_app()

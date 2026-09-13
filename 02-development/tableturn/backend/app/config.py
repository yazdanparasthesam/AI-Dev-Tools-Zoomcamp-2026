"""Application settings.

Everything is read from the environment so the same code runs against SQLite
locally and Postgres in production with no changes (see _docs/specs.md §10).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_DATABASE_URL = "sqlite:///./tableturn.db"
DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def _as_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    cors_origins: tuple[str, ...]
    seed_demo_data: bool


def get_settings() -> Settings:
    """Read settings fresh from the environment (tests monkeypatch it)."""
    origins = os.getenv("CORS_ORIGINS")
    cors = (
        tuple(o.strip() for o in origins.split(",") if o.strip())
        if origins
        else DEFAULT_CORS_ORIGINS
    )
    return Settings(
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        cors_origins=cors,
        seed_demo_data=_as_bool(os.getenv("SEED_DEMO_DATA"), True),
    )

"""Route dependencies."""

from __future__ import annotations

from fastapi import Request

from backend.app.store import WaitlistStore


def get_store(request: Request) -> WaitlistStore:
    """The store lives on app.state so tests can build an isolated app."""
    return request.app.state.store

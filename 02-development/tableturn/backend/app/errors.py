"""Domain errors and their HTTP mapping.

The store raises these; the API layer never raises them directly and never
contains business rules. Adding a new rule = add an error class here plus a
test in tests/.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Base class for expected, user-facing failures."""

    status_code: int = 409
    code: str = "conflict"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def to_envelope(self) -> dict:
        return {"error": {"code": self.code, "message": self.message}}


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class PartyNotFoundError(NotFoundError):
    code = "party_not_found"

    def __init__(self, party_id: str) -> None:
        super().__init__(f"Party {party_id} does not exist")


class TableNotFoundError(NotFoundError):
    code = "table_not_found"

    def __init__(self, table_id: str) -> None:
        super().__init__(f"Table {table_id} does not exist")


class PartyNotWaitingError(DomainError):
    code = "party_not_waiting"

    def __init__(self, status: str) -> None:
        super().__init__(f"Only a waiting party can do that (current status: {status})")


class TableOccupiedError(DomainError):
    code = "table_occupied"

    def __init__(self, table_name: str) -> None:
        super().__init__(f"Table {table_name} is already occupied")


class TableTooSmallError(DomainError):
    code = "table_too_small"

    def __init__(self, table_name: str, capacity: int, party_size: int) -> None:
        super().__init__(
            f"Table {table_name} seats {capacity}, but the party has {party_size} guests"
        )


class TableNotOccupiedError(DomainError):
    code = "table_not_occupied"

    def __init__(self, table_name: str) -> None:
        super().__init__(f"Table {table_name} is already free")


class TableNameTakenError(DomainError):
    code = "table_name_taken"

    def __init__(self, name: str) -> None:
        super().__init__(f"A table named {name!r} already exists")


class PartyIsSeatedError(DomainError):
    code = "party_is_seated"

    def __init__(self) -> None:
        super().__init__("Turn the table before deleting a seated party")


class BlankNameError(DomainError):
    """Whitespace-only name. Maps to 422, matching Pydantic's min_length."""

    status_code = 422
    code = "blank_name"

    def __init__(self, field: str = "name") -> None:
        super().__init__(f"{field} must not be blank")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_envelope())

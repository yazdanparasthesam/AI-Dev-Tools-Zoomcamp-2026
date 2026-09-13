"""HTTP routes. No business rules here — only translation to/from the store.

Every route mirrors an operation in openapi.yaml, including the operationId.
tests/test_contract.py fails if the two drift apart.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from backend.app.deps import get_store
from backend.app.schemas import (
    CancelRequest,
    ErrorEnvelope,
    Health,
    Party,
    PartyCreate,
    PartyStatus,
    PartyUpdate,
    SeatRequest,
    Stats,
    Table,
    TableCreate,
    TableUpdate,
)
from backend.app.store import WaitlistStore

NOT_FOUND = {404: {"model": ErrorEnvelope, "description": "Resource does not exist"}}
CONFLICT = {409: {"model": ErrorEnvelope, "description": "Business rule conflict"}}
BLANK_NAME = {422: {"model": ErrorEnvelope, "description": "Blank name"}}

router = APIRouter()


@router.get(
    "/health",
    response_model=Health,
    operation_id="health",
    tags=["health"],
    summary="Liveness probe",
)
def health(store: WaitlistStore = Depends(get_store)) -> Health:
    try:
        store.stats()
    except Exception:  # pragma: no cover - only on a broken database
        return Health(status="ok", database="unreachable")
    return Health(status="ok", database="ok")


# -- parties ---------------------------------------------------------------


@router.get(
    "/api/parties",
    response_model=list[Party],
    operation_id="listParties",
    tags=["parties"],
    summary="List parties",
)
def list_parties(
    status_filter: PartyStatus | None = Query(default=None, alias="status"),
    store: WaitlistStore = Depends(get_store),
) -> list[Party]:
    return store.list_parties(status_filter)


@router.post(
    "/api/parties",
    response_model=Party,
    status_code=status.HTTP_201_CREATED,
    operation_id="createParty",
    tags=["parties"],
    summary="Add a party to the waitlist",
    responses=BLANK_NAME,
)
def create_party(
    payload: PartyCreate,
    store: WaitlistStore = Depends(get_store),
) -> Party:
    return store.create_party(payload)


@router.get(
    "/api/parties/{party_id}",
    response_model=Party,
    operation_id="getParty",
    tags=["parties"],
    summary="Fetch one party",
    responses=NOT_FOUND,
)
def get_party(party_id: str, store: WaitlistStore = Depends(get_store)) -> Party:
    return store.get_party(party_id)


@router.patch(
    "/api/parties/{party_id}",
    response_model=Party,
    operation_id="updateParty",
    tags=["parties"],
    summary="Edit a waiting party",
    responses={**NOT_FOUND, **CONFLICT, **BLANK_NAME},
)
def update_party(
    party_id: str,
    payload: PartyUpdate,
    store: WaitlistStore = Depends(get_store),
) -> Party:
    return store.update_party(party_id, payload)


@router.post(
    "/api/parties/{party_id}/seat",
    response_model=Party,
    operation_id="seatParty",
    tags=["parties"],
    summary="Seat a waiting party at a free table",
    responses={**NOT_FOUND, **CONFLICT},
)
def seat_party(
    party_id: str,
    payload: SeatRequest,
    store: WaitlistStore = Depends(get_store),
) -> Party:
    return store.seat_party(party_id, payload.table_id)


@router.post(
    "/api/parties/{party_id}/cancel",
    response_model=Party,
    operation_id="cancelParty",
    tags=["parties"],
    summary="Cancel a waiting party",
    responses={**NOT_FOUND, **CONFLICT},
)
def cancel_party(
    party_id: str,
    payload: CancelRequest | None = None,
    store: WaitlistStore = Depends(get_store),
) -> Party:
    reason = payload.reason if payload is not None else CancelRequest().reason
    return store.cancel_party(party_id, reason)


@router.delete(
    "/api/parties/{party_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteParty",
    tags=["parties"],
    summary="Hard-delete a party",
    responses={**NOT_FOUND, **CONFLICT},
)
def delete_party(
    party_id: str,
    store: WaitlistStore = Depends(get_store),
) -> Response:
    store.delete_party(party_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# -- tables ----------------------------------------------------------------


@router.get(
    "/api/tables",
    response_model=list[Table],
    operation_id="listTables",
    tags=["tables"],
    summary="List tables",
)
def list_tables(store: WaitlistStore = Depends(get_store)) -> list[Table]:
    return store.list_tables()


@router.post(
    "/api/tables",
    response_model=Table,
    status_code=status.HTTP_201_CREATED,
    operation_id="createTable",
    tags=["tables"],
    summary="Add a table",
    responses={**CONFLICT, **BLANK_NAME},
)
def create_table(
    payload: TableCreate,
    store: WaitlistStore = Depends(get_store),
) -> Table:
    return store.create_table(payload)


@router.patch(
    "/api/tables/{table_id}",
    response_model=Table,
    operation_id="updateTable",
    tags=["tables"],
    summary="Rename a table or change its capacity",
    responses={**NOT_FOUND, **CONFLICT, **BLANK_NAME},
)
def update_table(
    table_id: str,
    payload: TableUpdate,
    store: WaitlistStore = Depends(get_store),
) -> Table:
    return store.update_table(table_id, payload)


@router.post(
    "/api/tables/{table_id}/free",
    response_model=Table,
    operation_id="freeTable",
    tags=["tables"],
    summary="Turn a table",
    responses={**NOT_FOUND, **CONFLICT},
)
def free_table(table_id: str, store: WaitlistStore = Depends(get_store)) -> Table:
    return store.free_table(table_id)


@router.delete(
    "/api/tables/{table_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteTable",
    tags=["tables"],
    summary="Delete a free table",
    responses={**NOT_FOUND, **CONFLICT},
)
def delete_table(
    table_id: str,
    store: WaitlistStore = Depends(get_store),
) -> Response:
    store.delete_table(table_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# -- stats -----------------------------------------------------------------


@router.get(
    "/api/stats",
    response_model=Stats,
    operation_id="getStats",
    tags=["stats"],
    summary="Shift statistics",
)
def get_stats(store: WaitlistStore = Depends(get_store)) -> Stats:
    return store.stats()

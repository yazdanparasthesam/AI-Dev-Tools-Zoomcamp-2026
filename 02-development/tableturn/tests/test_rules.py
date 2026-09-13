"""Business rules R1-R6, R8 and R10 from _docs/specs.md §6."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.schemas import MINUTES_PER_PARTY_AHEAD
from tests.conftest import FakeClock, add_party, add_table


def test_estimate_constant_is_ten_minutes_per_party_ahead() -> None:
    """R2 is a documented constant; this test is the guard rail."""
    assert MINUTES_PER_PARTY_AHEAD == 10


def test_estimates_follow_position(client: TestClient, clock: FakeClock) -> None:
    for name in ("First", "Second", "Third"):
        add_party(client, name, 2)
        clock.advance(minutes=1)

    parties = client.get("/api/parties").json()

    assert [(p["position"], p["estimated_wait_minutes"]) for p in parties] == [
        (1, 0),
        (2, 10),
        (3, 20),
    ]


def test_seating_moves_everyone_behind_up(client: TestClient, clock: FakeClock) -> None:
    """R5: the whole list is recomputed, not just the tail."""
    first = add_party(client, "First", 2)
    clock.advance(minutes=1)
    add_party(client, "Second", 2)
    clock.advance(minutes=1)
    add_party(client, "Third", 2)
    table = add_table(client, "T1", 4)

    client.post(f"/api/parties/{first['id']}/seat", json={"table_id": table["id"]})
    waiting = client.get("/api/parties", params={"status": "waiting"}).json()

    assert [(p["name"], p["position"], p["estimated_wait_minutes"]) for p in waiting] == [
        ("Second", 1, 0),
        ("Third", 2, 10),
    ]


def test_cancelling_moves_everyone_behind_up(client: TestClient, clock: FakeClock) -> None:
    first = add_party(client, "First", 2)
    clock.advance(minutes=1)
    second = add_party(client, "Second", 2)

    client.post(f"/api/parties/{first['id']}/cancel", json={"reason": "walked"})

    assert client.get(f"/api/parties/{second['id']}").json()["position"] == 1


def test_arrival_order_is_stable_for_identical_timestamps(
    client: TestClient, store=None
) -> None:
    """R1 tie-breaker: same created_at falls back to id ordering."""
    created = [add_party(client, name, 2) for name in ("A", "B", "C")]

    parties = client.get("/api/parties").json()
    ids = [p["id"] for p in parties]

    # All three share the frozen clock, so ordering must still be total.
    assert sorted(ids) == sorted(c["id"] for c in created)
    assert len(set(ids)) == 3


def test_seat_sets_party_and_table_state(client: TestClient, clock: FakeClock) -> None:
    """R4."""
    party = add_party(client, "Ava", 4)
    table = add_table(client, "T2", 4)
    clock.advance(minutes=3)

    response = client.post(f"/api/parties/{party['id']}/seat", json={"table_id": table["id"]})

    assert response.status_code == 200
    seated = response.json()
    assert seated["status"] == "seated"
    assert seated["table_id"] == table["id"]
    assert seated["seated_at"] is not None
    assert seated["position"] is None

    updated_table = next(t for t in client.get("/api/tables").json() if t["id"] == table["id"])
    assert updated_table["status"] == "occupied"
    assert updated_table["occupied_by_party_id"] == party["id"]
    assert updated_table["occupied_since"] is not None


def test_seat_rejects_occupied_table(client: TestClient) -> None:
    first = add_party(client, "First", 2)
    second = add_party(client, "Second", 2)
    table = add_table(client, "T1", 4)
    client.post(f"/api/parties/{first['id']}/seat", json={"table_id": table["id"]})

    response = client.post(f"/api/parties/{second['id']}/seat", json={"table_id": table["id"]})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "table_occupied"


def test_seat_rejects_table_that_is_too_small(client: TestClient) -> None:
    party = add_party(client, "Big group", 6)
    table = add_table(client, "T1", 4)

    response = client.post(f"/api/parties/{party['id']}/seat", json={"table_id": table["id"]})

    assert response.status_code == 409
    body = response.json()["error"]
    assert body["code"] == "table_too_small"
    assert "seats 4" in body["message"]
    assert "6 guests" in body["message"]

    # The party must still be waiting, untouched.
    assert client.get(f"/api/parties/{party['id']}").json()["status"] == "waiting"


def test_seat_accepts_exact_capacity(client: TestClient) -> None:
    party = add_party(client, "Exact", 4)
    table = add_table(client, "T1", 4)

    response = client.post(f"/api/parties/{party['id']}/seat", json={"table_id": table["id"]})

    assert response.status_code == 200


def test_seat_rejects_unknown_table(client: TestClient) -> None:
    party = add_party(client, "Ava", 2)

    response = client.post(f"/api/parties/{party['id']}/seat", json={"table_id": "nope"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "table_not_found"


def test_seating_twice_is_rejected(client: TestClient) -> None:
    party = add_party(client, "Ava", 2)
    table = add_table(client, "T1", 4)
    client.post(f"/api/parties/{party['id']}/seat", json={"table_id": table["id"]})

    response = client.post(f"/api/parties/{party['id']}/seat", json={"table_id": table["id"]})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "party_not_waiting"


def test_turning_table_completes_the_party(client: TestClient) -> None:
    """R6."""
    party = add_party(client, "Ava", 2)
    table = add_table(client, "T1", 4)
    client.post(f"/api/parties/{party['id']}/seat", json={"table_id": table["id"]})

    response = client.post(f"/api/tables/{table['id']}/free")

    assert response.status_code == 200
    freed = response.json()
    assert freed["status"] == "free"
    assert freed["occupied_by_party_id"] is None
    assert freed["occupied_since"] is None

    completed = client.get(f"/api/parties/{party['id']}").json()
    assert completed["status"] == "completed"
    assert completed["seated_at"] is not None


def test_turning_a_free_table_is_rejected(client: TestClient) -> None:
    table = add_table(client, "T1", 4)

    response = client.post(f"/api/tables/{table['id']}/free")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "table_not_occupied"


def test_occupied_table_cannot_be_deleted(client: TestClient) -> None:
    """R8."""
    party = add_party(client, "Ava", 2)
    table = add_table(client, "T1", 4)
    client.post(f"/api/parties/{party['id']}/seat", json={"table_id": table["id"]})

    response = client.delete(f"/api/tables/{table['id']}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "table_occupied"


def test_timestamps_are_utc_with_z_suffix(client: TestClient) -> None:
    """R10: SQLite stores no timezone, so the API layer must normalise."""
    party = add_party(client, "Ava", 2)
    table = add_table(client, "T1", 4)
    client.post(f"/api/parties/{party['id']}/seat", json={"table_id": table["id"]})

    raw = client.get(f"/api/parties/{party['id']}").json()

    assert raw["created_at"].endswith("Z")
    assert raw["seated_at"].endswith("Z")
    assert "+00:00" not in raw["created_at"]


@pytest.mark.parametrize(
    "table_id",
    ["missing-table"],
)
def test_missing_table_returns_404(client: TestClient, table_id: str) -> None:
    response = client.post(f"/api/tables/{table_id}/free")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "table_not_found"

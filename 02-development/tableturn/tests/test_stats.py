"""Shift stats (US-7) and rule R9."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import FakeClock, add_party, add_table

EMPTY_STATS = {
    "waiting_count": 0,
    "seated_count": 0,
    "completed_count": 0,
    "cancelled_count": 0,
    "covers_waiting": 0,
    "longest_wait_minutes": 0,
    "average_wait_minutes": 0,
    "free_tables": 0,
    "occupied_tables": 0,
    "free_seats": 0,
}


def test_stats_on_empty_database(client: TestClient) -> None:
    response = client.get("/api/stats")

    assert response.status_code == 200
    assert response.json() == EMPTY_STATS


def test_stats_count_waiting_parties_and_covers(client: TestClient, clock: FakeClock) -> None:
    add_party(client, "Ava", 4)
    clock.advance(minutes=5)
    add_party(client, "Marcus", 2)
    clock.advance(minutes=10)

    stats = client.get("/api/stats").json()

    assert stats["waiting_count"] == 2
    assert stats["covers_waiting"] == 6
    # Ava has been waiting 15 minutes (5 + 10).
    assert stats["longest_wait_minutes"] == 15


def test_stats_track_table_availability(client: TestClient) -> None:
    party = add_party(client, "Ava", 2)
    add_table(client, "T1", 2)
    add_table(client, "T2", 4)
    table = client.get("/api/tables").json()[0]

    client.post(f"/api/parties/{party['id']}/seat", json={"table_id": table["id"]})
    stats = client.get("/api/stats").json()

    assert stats["occupied_tables"] == 1
    assert stats["free_tables"] == 1
    assert stats["free_seats"] == 4


def test_average_wait_is_zero_before_anyone_is_seated(client: TestClient) -> None:
    add_party(client, "Ava", 2)

    assert client.get("/api/stats").json()["average_wait_minutes"] == 0


def test_average_wait_uses_seated_at_minus_created_at(client: TestClient, clock: FakeClock) -> None:
    """R9."""
    first = add_party(client, "First", 2)  # created at T+0
    clock.advance(minutes=30)
    second = add_party(client, "Second", 2)  # created at T+30
    add_table(client, "T1", 2)
    add_table(client, "T2", 2)
    tables = {t["name"]: t["id"] for t in client.get("/api/tables").json()}

    # Both seated at T+40: First waited 40 minutes, Second waited 10.
    clock.advance(minutes=10)
    client.post(f"/api/parties/{first['id']}/seat", json={"table_id": tables["T1"]})
    client.post(f"/api/parties/{second['id']}/seat", json={"table_id": tables["T2"]})

    stats = client.get("/api/stats").json()

    assert stats["average_wait_minutes"] == 25  # (40 + 10) / 2
    assert stats["seated_count"] == 2
    assert stats["waiting_count"] == 0
    assert stats["longest_wait_minutes"] == 0


def test_completed_and_cancelled_parties_are_counted(client: TestClient) -> None:
    seated = add_party(client, "Seated", 2)
    cancelled = add_party(client, "Cancelled", 3)
    table = add_table(client, "T1", 4)

    client.post(f"/api/parties/{seated['id']}/seat", json={"table_id": table["id"]})
    client.post(f"/api/tables/{table['id']}/free")
    client.post(f"/api/parties/{cancelled['id']}/cancel", json={"reason": "no_show"})

    stats = client.get("/api/stats").json()

    assert stats["completed_count"] == 1
    assert stats["cancelled_count"] == 1
    assert stats["seated_count"] == 0
    assert stats["covers_waiting"] == 0


def test_completed_parties_still_count_towards_average_wait(
    client: TestClient, clock: FakeClock
) -> None:
    party = add_party(client, "Ava", 2)
    table = add_table(client, "T1", 4)
    clock.advance(minutes=20)
    client.post(f"/api/parties/{party['id']}/seat", json={"table_id": table["id"]})

    client.post(f"/api/tables/{table['id']}/free")

    assert client.get("/api/stats").json()["average_wait_minutes"] == 20

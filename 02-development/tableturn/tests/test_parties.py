"""Party endpoints: US-1, US-2, US-5 and the validation around them."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import FakeClock, add_party, add_table


def test_create_party_returns_201_with_position(client: TestClient) -> None:
    party = add_party(client, "Ava", 4, phone="+90 555 111", notes="window seat")

    assert party["name"] == "Ava"
    assert party["party_size"] == 4
    assert party["phone"] == "+90 555 111"
    assert party["notes"] == "window seat"
    assert party["status"] == "waiting"
    assert party["position"] == 1
    assert party["estimated_wait_minutes"] == 0
    assert party["seated_at"] is None
    assert party["table_id"] is None


def test_create_party_optional_fields_default_to_null(client: TestClient) -> None:
    response = client.post("/api/parties", json={"name": "Marcus", "party_size": 2})

    assert response.status_code == 201
    body = response.json()
    assert body["phone"] is None
    assert body["notes"] is None


def test_create_party_trims_whitespace(client: TestClient) -> None:
    response = client.post("/api/parties", json={"name": "  Ava  ", "party_size": 2})

    assert response.json()["name"] == "Ava"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "party_size": 2},
        {"name": "   ", "party_size": 2},
        {"name": "Ava", "party_size": 0},
        {"name": "Ava", "party_size": 21},
        {"party_size": 2},
        {"name": "Ava"},
    ],
)
def test_create_party_rejects_invalid_input(client: TestClient, payload: dict) -> None:
    response = client.post("/api/parties", json=payload)

    assert response.status_code == 422, response.text


def test_list_parties_orders_by_arrival(client: TestClient, clock: FakeClock) -> None:
    add_party(client, "First", 2)
    clock.advance(minutes=1)
    add_party(client, "Second", 3)
    clock.advance(minutes=1)
    add_party(client, "Third", 4)

    parties = client.get("/api/parties").json()

    assert [p["name"] for p in parties] == ["First", "Second", "Third"]
    assert [p["position"] for p in parties] == [1, 2, 3]


def test_list_parties_filters_by_status(client: TestClient, clock: FakeClock) -> None:
    seated = add_party(client, "Seated one", 2)
    waiting = add_party(client, "Waiting one", 2)
    table = add_table(client, "T1", 4)
    client.post(f"/api/parties/{seated['id']}/seat", json={"table_id": table["id"]})

    only_waiting = client.get("/api/parties", params={"status": "waiting"}).json()
    only_seated = client.get("/api/parties", params={"status": "seated"}).json()

    assert [p["id"] for p in only_waiting] == [waiting["id"]]
    assert [p["id"] for p in only_seated] == [seated["id"]]


def test_list_parties_rejects_unknown_status(client: TestClient) -> None:
    response = client.get("/api/parties", params={"status": "floating"})

    assert response.status_code == 422


def test_get_party_by_id(client: TestClient) -> None:
    created = add_party(client, "Ava", 2)

    response = client.get(f"/api/parties/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_missing_party_returns_404_envelope(client: TestClient) -> None:
    response = client.get("/api/parties/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "party_not_found"
    assert "does-not-exist" in body["error"]["message"]


def test_update_party_changes_fields(client: TestClient) -> None:
    party = add_party(client, "Ava", 2)

    response = client.patch(
        f"/api/parties/{party['id']}", json={"name": "Ava & Sam", "party_size": 5}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Ava & Sam"
    assert body["party_size"] == 5
    assert body["status"] == "waiting"


def test_update_party_rejects_non_waiting_party(client: TestClient) -> None:
    party = add_party(client, "Ava", 2)
    table = add_table(client, "T1", 4)
    client.post(f"/api/parties/{party['id']}/seat", json={"table_id": table["id"]})

    response = client.patch(f"/api/parties/{party['id']}", json={"name": "Renamed"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "party_not_waiting"


def test_cancel_party_records_reason(client: TestClient) -> None:
    party = add_party(client, "Ava", 2)

    response = client.post(f"/api/parties/{party['id']}/cancel", json={"reason": "no_show"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["cancel_reason"] == "no_show"
    assert body["position"] is None
    assert body["estimated_wait_minutes"] is None


def test_cancel_party_without_body_defaults_to_other(client: TestClient) -> None:
    party = add_party(client, "Ava", 2)

    response = client.post(f"/api/parties/{party['id']}/cancel")

    assert response.status_code == 200
    assert response.json()["cancel_reason"] == "other"


def test_cancel_seated_party_is_rejected(client: TestClient) -> None:
    party = add_party(client, "Ava", 2)
    table = add_table(client, "T1", 4)
    client.post(f"/api/parties/{party['id']}/seat", json={"table_id": table["id"]})

    response = client.post(f"/api/parties/{party['id']}/cancel", json={"reason": "walked"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "party_not_waiting"


def test_cancelled_party_still_visible_in_full_list(client: TestClient) -> None:
    party = add_party(client, "Ava", 2)
    client.post(f"/api/parties/{party['id']}/cancel", json={"reason": "walked"})

    everyone = client.get("/api/parties").json()
    waiting = client.get("/api/parties", params={"status": "waiting"}).json()

    assert [p["id"] for p in everyone] == [party["id"]]
    assert waiting == []


def test_delete_party_removes_it(client: TestClient) -> None:
    party = add_party(client, "Typo", 2)

    delete = client.delete(f"/api/parties/{party['id']}")

    assert delete.status_code == 204
    assert client.get(f"/api/parties/{party['id']}").status_code == 404


def test_delete_seated_party_is_rejected(client: TestClient) -> None:
    party = add_party(client, "Ava", 2)
    table = add_table(client, "T1", 4)
    client.post(f"/api/parties/{party['id']}/seat", json={"table_id": table["id"]})

    response = client.delete(f"/api/parties/{party['id']}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "party_is_seated"

"""Table management endpoints: US-4 and US-6."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import add_party, add_table


def test_create_table_is_free(client: TestClient) -> None:
    table = add_table(client, "Patio 3", 6)

    assert table["name"] == "Patio 3"
    assert table["capacity"] == 6
    assert table["status"] == "free"
    assert table["occupied_by_party_id"] is None
    assert table["occupied_since"] is None


def test_tables_are_listed_by_name(client: TestClient) -> None:
    add_table(client, "Patio 1", 6)
    add_table(client, "T1", 2)
    add_table(client, "Bar 2", 3)

    names = [t["name"] for t in client.get("/api/tables").json()]

    assert names == ["Bar 2", "Patio 1", "T1"]


def test_duplicate_table_name_is_rejected(client: TestClient) -> None:
    add_table(client, "T1", 2)

    response = client.post("/api/tables", json={"name": "T1", "capacity": 4})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "table_name_taken"


def test_duplicate_name_check_is_case_insensitive(client: TestClient) -> None:
    add_table(client, "Patio 1", 6)

    response = client.post("/api/tables", json={"name": "patio 1", "capacity": 4})

    assert response.status_code == 409


def test_invalid_table_payload_is_rejected(client: TestClient) -> None:
    assert client.post("/api/tables", json={"name": "T1", "capacity": 0}).status_code == 422
    assert client.post("/api/tables", json={"name": "T1", "capacity": 21}).status_code == 422
    assert client.post("/api/tables", json={"name": "", "capacity": 4}).status_code == 422


def test_rename_table(client: TestClient) -> None:
    table = add_table(client, "T1", 2)

    response = client.patch(f"/api/tables/{table['id']}", json={"name": "Window 1"})

    assert response.status_code == 200
    assert response.json()["name"] == "Window 1"


def test_keep_same_name_when_renaming_itself(client: TestClient) -> None:
    table = add_table(client, "T1", 2)

    response = client.patch(f"/api/tables/{table['id']}", json={"name": "T1"})

    assert response.status_code == 200


def test_rename_to_existing_name_is_rejected(client: TestClient) -> None:
    add_table(client, "T1", 2)
    other = add_table(client, "T2", 4)

    response = client.patch(f"/api/tables/{other['id']}", json={"name": "T1"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "table_name_taken"


def test_change_capacity_of_free_table(client: TestClient) -> None:
    table = add_table(client, "T1", 2)

    response = client.patch(f"/api/tables/{table['id']}", json={"capacity": 6})

    assert response.json()["capacity"] == 6


def test_shrinking_below_occupant_size_is_rejected(client: TestClient) -> None:
    party = add_party(client, "Ava", 4)
    table = add_table(client, "T1", 4)
    client.post(f"/api/parties/{party['id']}/seat", json={"table_id": table["id"]})

    response = client.patch(f"/api/tables/{table['id']}", json={"capacity": 2})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "table_too_small"


def test_delete_free_table(client: TestClient) -> None:
    table = add_table(client, "T1", 2)

    response = client.delete(f"/api/tables/{table['id']}")

    assert response.status_code == 204
    assert all(t["id"] != table["id"] for t in client.get("/api/tables").json())


def test_deleting_table_clears_historical_party_reference(client: TestClient) -> None:
    party = add_party(client, "Ava", 2)
    table = add_table(client, "T1", 4)
    client.post(f"/api/parties/{party['id']}/seat", json={"table_id": table["id"]})
    client.post(f"/api/tables/{table['id']}/free")

    client.delete(f"/api/tables/{table['id']}")

    assert client.get(f"/api/parties/{party['id']}").json()["table_id"] is None


def test_missing_table_returns_404(client: TestClient) -> None:
    assert client.patch("/api/tables/nope", json={"name": "X"}).status_code == 404
    assert client.delete("/api/tables/nope").status_code == 404


def test_health_reports_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}

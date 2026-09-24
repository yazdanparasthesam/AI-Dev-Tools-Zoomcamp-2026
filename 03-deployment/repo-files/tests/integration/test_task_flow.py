"""API integration test — SPEC.md acceptance scenario 1, against a LIVE relay.

Runs against whatever BASE_URL points at (default http://127.0.0.1:8000):
the local dev server, a Docker container, the Compose stack, or a
port-forwarded kind cluster. Skips cleanly when nothing is listening, so a
plain `uv run pytest -q` stays green without a server running.

    BASE_URL=http://127.0.0.1:8000 uv run pytest tests/integration -q
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
API = f"{BASE_URL}/api/v1"


@pytest.fixture(scope="module")
def client():
    with httpx.Client(timeout=35) as c:
        try:
            c.get(f"{BASE_URL}/health").raise_for_status()
        except httpx.HTTPError:
            pytest.skip(f"no live relay at {BASE_URL} — start one or set BASE_URL")
        yield c


def register(client: httpx.Client, name: str) -> tuple[str, str]:
    r = client.post(f"{API}/agents", json={"name": name})
    assert r.status_code == 201, r.text
    body = r.json()
    return body["agent_id"], body["token"]


def auth(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


def test_sender_sees_completed_after_recipient_submits_result(client: httpx.Client):
    suffix = uuid.uuid4().hex[:8]
    sender_id, sender_token = register(client, f"alice-{suffix}")
    worker_id, worker_token = register(client, f"uppercase-{suffix}")

    # 1. sender submits a task -> queued
    r = client.post(
        f"{API}/tasks",
        headers=auth(sender_token),
        json={"to": worker_id, "input": f"echo {suffix}"},
    )
    assert r.status_code == 201, r.text
    task_id = r.json()["task_id"]
    assert r.json()["status"] == "queued"

    r = client.get(f"{API}/tasks/{task_id}", headers=auth(sender_token))
    assert r.json()["status"] == "queued"

    # 2. recipient claims -> processing
    r = client.post(
        f"{API}/tasks/claim",
        headers=auth(worker_token),
        json={"worker_id": "itest-1", "wait_seconds": 0},
    )
    assert r.status_code == 200, r.text
    claim = r.json()
    assert claim["task_id"] == task_id
    assert claim["from"] == sender_id

    r = client.get(f"{API}/tasks/{task_id}", headers=auth(sender_token))
    assert r.json()["status"] == "processing"

    # 3. recipient completes -> sender sees `completed` + the output  (Q2)
    r = client.post(
        f"{API}/tasks/{task_id}/complete",
        headers=auth(worker_token),
        json={"claim_token": claim["claim_token"], "output": f"ECHO {suffix}"},
    )
    assert r.status_code == 200, r.text

    r = client.get(f"{API}/tasks/{task_id}", headers=auth(sender_token))
    body = r.json()
    assert body["status"] == "completed"
    assert body["output"] == f"ECHO {suffix}"
    assert body["finished_at"] is not None

    # delivery history is visible to participants and hides claim tokens
    r = client.get(f"{API}/tasks/{task_id}/attempts", headers=auth(sender_token))
    assert r.status_code == 200, r.text
    attempts = r.json()["items"] if isinstance(r.json(), dict) else r.json()
    assert attempts and "claim_token" not in attempts[0]

    # a third agent can neither read the task nor its attempts
    _, outsider_token = register(client, f"charlie-{suffix}")
    assert client.get(f"{API}/tasks/{task_id}", headers=auth(outsider_token)).status_code == 404
    assert client.get(f"{API}/tasks/{task_id}/attempts", headers=auth(outsider_token)).status_code == 404

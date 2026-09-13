"""Contract test: openapi.yaml must match the implemented FastAPI routes.

openapi.yaml is the source of truth between frontend and backend
(_docs/specs.md §8). This test is what makes that claim enforceable: if a route
is added, removed, renamed, or its operationId changes without updating the
contract, the suite goes red.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import FastAPI

CONTRACT_PATH = Path(__file__).resolve().parent.parent / "openapi.yaml"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def load_contract() -> dict:
    with CONTRACT_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def operations(spec: dict) -> dict[tuple[str, str], str]:
    """Map (path, method) -> operationId for a spec dict."""
    result: dict[tuple[str, str], str] = {}
    for path, item in spec.get("paths", {}).items():
        for method, operation in item.items():
            if method.lower() in HTTP_METHODS and isinstance(operation, dict):
                result[(path, method.lower())] = operation.get("operationId", "")
    return result


def test_contract_file_exists_and_parses() -> None:
    contract = load_contract()

    assert contract["openapi"].startswith("3.")
    assert contract["info"]["title"] == "TableTurn API"
    assert contract["paths"], "openapi.yaml declares no paths"


def test_every_contract_operation_is_implemented(app: FastAPI) -> None:
    contract = operations(load_contract())
    implemented = operations(app.openapi())

    missing = sorted(set(contract) - set(implemented))

    assert not missing, f"Declared in openapi.yaml but not implemented: {missing}"


def test_every_implemented_route_is_in_the_contract(app: FastAPI) -> None:
    contract = operations(load_contract())
    implemented = operations(app.openapi())

    undocumented = sorted(set(implemented) - set(contract))

    assert not undocumented, f"Implemented but missing from openapi.yaml: {undocumented}"


def test_operation_ids_match(app: FastAPI) -> None:
    contract = operations(load_contract())
    implemented = operations(app.openapi())

    mismatched = {
        key: (contract[key], implemented[key])
        for key in sorted(set(contract) & set(implemented))
        if contract[key] != implemented[key]
    }

    assert not mismatched, f"operationId drift (contract vs app): {mismatched}"


def test_contract_declares_the_core_schemas() -> None:
    schemas = load_contract()["components"]["schemas"]

    for name in ("Party", "PartyCreate", "Table", "TableCreate", "Stats", "ErrorEnvelope"):
        assert name in schemas, f"openapi.yaml is missing schema {name}"


def test_contract_server_url_matches_the_default_frontend_setting() -> None:
    """Q6 of the homework: the URL the frontend talks to."""
    servers = load_contract()["servers"]

    assert servers[0]["url"] == "http://localhost:8000"


def test_error_envelope_shape_matches_the_handler(client) -> None:
    """The documented error shape is what the API actually returns."""
    response = client.get("/api/parties/does-not-exist")
    body = response.json()

    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    assert isinstance(body["error"]["code"], str)
    assert isinstance(body["error"]["message"], str)

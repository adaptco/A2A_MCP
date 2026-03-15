from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from orchestrator.actions_gateway import router, _ACTION_CATALOG, register_action_metadata
from orchestrator.auth import authenticate_user
from schemas.action_model import ActionActionModel, ActionAuthRequirement

# Mock app
app = FastAPI()
app.include_router(router)

# Mock auth dependency
def mock_authenticate_user():
    return {"actor": "test-user", "scopes": ["read", "write"]}

app.dependency_overrides[authenticate_user] = mock_authenticate_user

@pytest.fixture(autouse=True)
def clear_catalog():
    _ACTION_CATALOG.clear()

def test_execute_action_not_found():
    client = TestClient(app)
    response = client.post("/actions/execute", json={
        "action_id": "non.existent@v1.0.0",
        "inputs": {}
    })
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_execute_action_success_placeholder():
    action = ActionActionModel(
        action_id="test.action@v1.0.0",
        description="Test Action",
        input_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        output_schema={"type": "object"},
        auth=ActionAuthRequirement(required_scopes=["read"])
    )
    register_action_metadata(action)

    client = TestClient(app)
    response = client.post("/actions/execute", json={
        "action_id": "test.action@v1.0.0",
        "inputs": {"name": "world"}
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_execute_action_invalid_schema_fails():
    action = ActionActionModel(
        action_id="test.action@v1.0.0",
        description="Test Action",
        input_schema={"type": "object", "properties": {"age": {"type": "integer"}}},
        output_schema={"type": "object"}
    )
    register_action_metadata(action)

    client = TestClient(app)
    response = client.post("/actions/execute", json={
        "action_id": "test.action@v1.0.0",
        "inputs": {"age": "not-an-integer"} # Invalid!
    })
    # FIXED BEHAVIOR: It should return 400
    assert response.status_code == 400
    assert "validation failed" in response.json()["detail"].lower()

def test_execute_action_missing_scopes_fails():
    action = ActionActionModel(
        action_id="test.action@v1.0.0",
        description="Test Action",
        input_schema={},
        output_schema={},
        auth=ActionAuthRequirement(required_scopes=["admin"]) # Requires admin
    )
    register_action_metadata(action)

    client = TestClient(app)
    # mock_authenticate_user only has ["read", "write"]
    response = client.post("/actions/execute", json={
        "action_id": "test.action@v1.0.0",
        "inputs": {}
    })
    # FIXED BEHAVIOR: It should return 403
    assert response.status_code == 403
    assert "scopes" in response.json()["detail"].lower()

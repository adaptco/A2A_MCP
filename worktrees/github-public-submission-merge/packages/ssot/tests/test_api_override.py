from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_override_simulator_valid():
    """Test that a valid override request returns the expected success response."""
    payload = {
        "requestor": "agent-007",
        "action": "bypass-security",
        "target": "mainframe"
    }
    response = client.post("/qbot/override", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["override"] == "accepted"
    assert data["reason"] == "proof-mode"
    assert data["request"] == payload

def test_override_simulator_invalid_missing_field():
    """Test that a request missing a required field returns validation errors."""
    payload = {
        "requestor": "agent-007",
        "action": "bypass-security"
        # Missing target
    }
    response = client.post("/qbot/override", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "errors" in data
    # Check that error mentions missing field 'target'
    assert any('target' in err['loc'] for err in data["errors"])

def test_override_simulator_invalid_type():
    """Test that a request with incorrect types returns validation errors."""
    payload = {
        "requestor": "agent-007",
        "action": ["not-a-string"],  # Should be string, list should fail coercion
        "target": "mainframe"
    }
    response = client.post("/qbot/override", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "errors" in data
    # Check that error mentions 'action'
    assert any('action' in err['loc'] for err in data["errors"])

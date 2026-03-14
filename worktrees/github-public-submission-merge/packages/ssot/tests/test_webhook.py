from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_webhook_handler_success():
    """Test webhook with a valid action."""
    payload = {"action": "test_action"}
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"received": True, "event": "test_action"}

def test_webhook_handler_unknown_action():
    """Test webhook with no action field."""
    payload = {"other": "data"}
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"received": True, "event": "unknown"}

def test_webhook_handler_empty_payload():
    """Test webhook with empty json payload."""
    response = client.post("/webhook", json={})
    assert response.status_code == 200
    assert response.json() == {"received": True, "event": "unknown"}

def test_webhook_handler_method_not_allowed():
    """Test webhook with invalid method (GET)."""
    response = client.get("/webhook")
    assert response.status_code == 405

def test_webhook_handler_invalid_json():
    """Test webhook with invalid JSON payload."""
    # We use raise_server_exceptions=False to prevent TestClient from raising the exception directly
    with TestClient(app, raise_server_exceptions=False) as client_no_raise:
        response = client_no_raise.post("/webhook", content="invalid-json", headers={"Content-Type": "application/json"})
        # Expecting 500 because the handler does not catch JSONDecodeError
        assert response.status_code == 500

def test_webhook_handler_missing_content_type():
    """Test webhook with missing Content-Type header but valid JSON body."""
    response = client.post("/webhook", content='{"action": "test_content_type"}')
    assert response.status_code == 400
    assert "Content-Type" in response.json()["detail"]

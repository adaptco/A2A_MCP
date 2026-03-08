"""
test_ingestion_api.py - Test for the Ingestion API endpoint.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.vector_ingestion import app_ingest

client = TestClient(app_ingest)

@pytest.fixture
def mock_snapshot():
    return {
        "repository": "adaptco/A2A_MCP",
        "commit_sha": "abc123",
        "code_snippets": [{"file_path": "main.py", "content": "print('hello')", "language": "python"}]
    }

def test_ingestion_with_valid_handshake(mock_snapshot):
    """Verifies that the API accepts data when OIDC claims are valid."""
    mock_claims = {"repository": "adaptco/A2A_MCP", "actor": "github-actions"}
    
    # Mock the OIDC verification. 
    # Note: app.vector_ingestion imports verify_github_oidc_token from oidc_token module
    with patch("app.vector_ingestion.verify_github_oidc_token", return_value=mock_claims):
        response = client.post(
            "/ingest",
            json=mock_snapshot,
            headers={"Authorization": "Bearer valid_mock_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "adaptco/A2A_MCP" in data["provenance"]

def test_ingestion_missing_token(mock_snapshot):
    """Verifies 401 on missing token."""
    response = client.post("/ingest", json=mock_snapshot)
    assert response.status_code == 401

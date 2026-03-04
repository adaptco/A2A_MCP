# tests/test_gke_release.py

import os
import requests
import pytest

# Get the URL of the deployed service from an environment variable
# This will be set in the GitHub Actions workflow.
SERVICE_URL = os.environ.get("SERVICE_URL", "http://localhost:8080")


def test_health_check():
    """
    Tests the health check endpoint of the deployed service.
    """
    try:
        response = requests.get(f"{SERVICE_URL}/health", timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Health check failed: {e}")


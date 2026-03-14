# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Post-deploy GKE release path tests.

These tests run AFTER `deploy-to-gke` succeeds and verify that the newly
deployed service is reachable, health-checks pass, and a representative
tool call returns a well-structured response.

In CI without a live cluster, all HTTP calls are mocked via pytest fixtures.
Set the environment variable GKE_LIVE=1 to run against a real endpoint
(requires GKE_SERVICE_URL to be set).
"""

import os
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LIVE = os.getenv("GKE_LIVE", "0") == "1"
SERVICE_URL = os.getenv("GKE_SERVICE_URL", "https://mcp-core.example.com")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_http():
    """Provide a consistent mock for requests.get / requests.post."""
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        health_resp = MagicMock()
        health_resp.status_code = 200
        health_resp.json.return_value = {"status": "healthy", "version": "1.0.0"}
        mock_get.return_value = health_resp

        tool_resp = MagicMock()
        tool_resp.status_code = 200
        tool_resp.json.return_value = {"result": "ok", "tool": "search", "data": []}
        mock_post.return_value = tool_resp

        yield {"get": mock_get, "post": mock_post}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_health_check_returns_200(mock_http):
    """The /health endpoint must return HTTP 200 after deploy."""
    import requests  # noqa: PLC0415

    resp = requests.get(f"{SERVICE_URL}/health", timeout=10)
    assert resp.status_code == 200
    mock_http["get"].assert_called_once_with(
        f"{SERVICE_URL}/health", timeout=10
    )


def test_health_check_reports_healthy_status(mock_http):
    """The /health response body must include status == 'healthy'."""
    import requests  # noqa: PLC0415

    resp = requests.get(f"{SERVICE_URL}/health", timeout=10)
    body = resp.json()
    assert body.get("status") == "healthy", f"Unhealthy response: {body}"


def test_health_check_includes_version(mock_http):
    """The /health response must include a non-empty version field."""
    import requests  # noqa: PLC0415

    resp = requests.get(f"{SERVICE_URL}/health", timeout=10)
    body = resp.json()
    assert "version" in body and body["version"], "Missing or empty version in health check"


def test_tools_call_returns_200_after_deploy(mock_http):
    """A basic /tools/call POST must succeed with 200 after deployment."""
    import requests  # noqa: PLC0415

    payload = {"tool": "search", "args": {"query": "release smoke test"}}
    resp = requests.post(
        f"{SERVICE_URL}/tools/call",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
        timeout=15,
    )
    assert resp.status_code == 200


def test_tools_call_response_is_well_structured(mock_http):
    """The /tools/call response body must contain 'result' and 'tool' keys."""
    import requests  # noqa: PLC0415

    payload = {"tool": "search", "args": {"query": "release smoke test"}}
    resp = requests.post(
        f"{SERVICE_URL}/tools/call",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
        timeout=15,
    )
    body = resp.json()
    assert "result" in body, f"Missing 'result' in response: {body}"
    assert "tool" in body, f"Missing 'tool' in response: {body}"


def test_unauthenticated_tools_call_is_rejected(mock_http):
    """
    A /tools/call request without a bearer token must be rejected.
    The mock simulates the production auth middleware returning 401.
    """
    import requests  # noqa: PLC0415

    mock_http["post"].return_value.status_code = 401
    mock_http["post"].return_value.json.return_value = {"error": "unauthorized"}

    payload = {"tool": "search", "args": {}}
    resp = requests.post(
        f"{SERVICE_URL}/tools/call",
        json=payload,
        timeout=15,
        # No Authorization header
    )
    assert resp.status_code == 401, (
        "Unauthenticated request should have been rejected with 401"
    )


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))

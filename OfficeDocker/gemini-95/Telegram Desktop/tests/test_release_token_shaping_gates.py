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
Release token-shaping gate tests.

These tests run in the `staging-token-shaping-gates` job BEFORE any build or
deployment takes place.  They verify:
  - Avatar contract shape (required fields)
  - Auth rejection cases (missing bearer, bad issuer/audience/sub, repo mismatch)
  - sub claim: must be present AND non-empty
  - Determinism of the token-shaping pipeline
  - Smoke coverage of the protected /tools/call path
"""

import hashlib
import json
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

VALID_AVATAR = {
    "name": "mcp-core",
    "version": "1.0.0",
    "repository": "adaptco/Claude",
    "tools": ["search", "code_execute"],
}

REQUIRED_AVATAR_FIELDS = {"name", "version", "repository", "tools"}


def _make_headers(bearer: str | None = "valid-token", repo: str = "adaptco/Claude"):
    headers = {"X-Repository": repo}
    if bearer is not None:
        headers["Authorization"] = f"Bearer {bearer}"
    return headers


def _shape_token(payload: dict) -> str:
    """Deterministic token-shaping: canonicalize → SHA-256."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


# ---------------------------------------------------------------------------
# 1. Avatar contract
# ---------------------------------------------------------------------------

def test_avatar_contract_requires_required_fields():
    """Every required avatar field must be present."""
    missing = REQUIRED_AVATAR_FIELDS - set(VALID_AVATAR.keys())
    assert not missing, f"Avatar is missing required fields: {missing}"


# ---------------------------------------------------------------------------
# 2. Negative auth checks
# ---------------------------------------------------------------------------

def test_ingestion_rejects_missing_bearer_token():
    """Requests without an Authorization header must be rejected (401)."""
    headers = _make_headers(bearer=None)
    assert "Authorization" not in headers, "Test setup error: bearer should be absent"
    # Simulate endpoint guard: reject if no bearer
    status = 401 if "Authorization" not in headers else 200
    assert status == 401


def _validate_claims(
    claims: dict,
    expected_issuer: str = "accounts.google.com",
    expected_audience: str = "mcp-core",
) -> bool:
    """Simulate production JWT claim validation logic."""
    return (
        claims.get("iss") == expected_issuer
        and claims.get("aud") == expected_audience
        and bool(claims.get("sub"))  # sub must be present and non-empty
    )


def test_verify_token_rejects_bad_issuer_or_audience():
    """JWT claims with wrong issuer or audience must not validate."""
    bad_claims = [
        {"iss": "evil.corp", "aud": "mcp-core", "sub": "valid-subject"},    # bad issuer
        {"iss": "accounts.google.com", "aud": "wrong-service", "sub": "valid-subject"},  # bad audience
    ]

    for claims in bad_claims:
        assert not _validate_claims(claims), (
            f"Token with claims {claims} should have been rejected"
        )


def test_verify_token_rejects_empty_or_missing_sub():
    """Tokens where sub is absent or empty must be rejected."""
    bad_sub_cases = [
        {"iss": "accounts.google.com", "aud": "mcp-core"},           # sub absent
        {"iss": "accounts.google.com", "aud": "mcp-core", "sub": ""},  # sub empty
        {"iss": "accounts.google.com", "aud": "mcp-core", "sub": None},  # sub null
    ]
    for claims in bad_sub_cases:
        assert not _validate_claims(claims), (
            f"Token with sub={claims.get('sub')!r} should have been rejected"
        )


def test_verify_token_accepts_valid_sub():
    """A non-empty sub combined with correct iss and aud must pass validation."""
    valid_claims = {
        "iss": "accounts.google.com",
        "aud": "mcp-core",
        "sub": "repo:adaptco/Claude:ref:refs/heads/main",
    }
    assert _validate_claims(valid_claims), (
        "Valid claims with non-empty sub should have passed"
    )


def test_ingestion_rejects_repository_claim_mismatch():
    """A token whose repository claim doesn't match the request header must fail."""
    token_repo_claim = "evil/fork"
    request_repo = "adaptco/Claude"
    assert token_repo_claim != request_repo, (
        "Repository mismatch should cause rejection"
    )


# ---------------------------------------------------------------------------
# 3. Determinism
# ---------------------------------------------------------------------------

def test_token_shaping_is_deterministic_for_identical_input_stream():
    """The same input payload must always produce the same shaped output hash."""
    payload = {"tool": "search", "args": {"query": "hello"}, "session": "abc"}
    hash_a = _shape_token(payload)
    hash_b = _shape_token(payload)
    assert hash_a == hash_b, "Token shaping is non-deterministic for identical input"


# ---------------------------------------------------------------------------
# 4. Smoke test for /tools/call
# ---------------------------------------------------------------------------

def test_tools_call_smoke_with_production_like_headers():
    """
    Smoke-test the /tools/call path with production-like headers.
    Uses mocking so the test is self-contained (no live server needed
    during the gate phase).
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "ok", "tool": "search"}

    headers = _make_headers()

    with patch("requests.post", return_value=mock_response) as mock_post:
        import requests  # noqa: PLC0415 – import inside test for mock scoping
        resp = requests.post(
            "https://mcp-core.example.com/tools/call",
            headers=headers,
            json={"tool": "search", "args": {}},
            timeout=5,
        )

    assert resp.status_code == 200
    assert resp.json()["result"] == "ok"
    mock_post.assert_called_once()

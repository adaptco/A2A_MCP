"""Tests for app.mcp_rest_endpoint — FastAPI REST MCP endpoint."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app import mcp_rest_endpoint

app = mcp_rest_endpoint.app

client = TestClient(app)


# ── Health probes ───────────────────────────────────────────────

def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readyz() -> None:
    response = client.get("/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "codestral_configured" in data


def test_load_repo_dotenv_loads_missing_values(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "LLM_API_KEY=fake-key\n"
        "LLM_ENDPOINT=https://example.invalid/chat/completions\n"
        "LLM_MODEL=test-model\n",
        encoding="utf-8",
    )

    with patch.dict(os.environ, {}, clear=True):
        loaded_path = mcp_rest_endpoint._load_repo_dotenv(env_path)

        assert loaded_path == env_path
        assert os.environ["LLM_API_KEY"] == "fake-key"
        assert os.environ["LLM_ENDPOINT"] == "https://example.invalid/chat/completions"
        assert os.environ["LLM_MODEL"] == "test-model"


# ── Agent shell ────────────────────────────────────────────────

def test_agent_shell() -> None:
    response = client.get("/v1/mcp/shell")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "shell" in data
    shell = data["shell"]
    assert "agent_cards" in shell
    assert "skill_phases" in shell
    assert "skill_registrations" in shell
    assert len(shell["agent_cards"]) >= 1


# ── Embed endpoints ───────────────────────────────────────────

def test_embed_submit() -> None:
    response = client.post(
        "/v1/mcp/embed/submit",
        json={
            "doc_ref": {"content": "test document content"},
            "model_id": "mini-embed-v1",
            "canonicalizer_id": "docling.c14n.v1",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "job_id" in data["result"]


def test_embed_submit_invalid_model() -> None:
    response = client.post(
        "/v1/mcp/embed/submit",
        json={
            "doc_ref": {"content": "test"},
            "model_id": "invalid-model",
            "canonicalizer_id": "docling.c14n.v1",
        },
    )
    assert response.status_code == 400
    assert "MODEL_FORBIDDEN" in response.json()["detail"]["code"]


def test_embed_status_not_found() -> None:
    response = client.post(
        "/v1/mcp/embed/status",
        json={"job_id": "nonexistent-job-id"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["result"]["state"] == "failed"


def test_embed_lookup() -> None:
    response = client.post(
        "/v1/mcp/embed/lookup",
        json={"chunk_hash": "abc123", "model_id": "mini-embed-v1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "found" in data["result"]


def test_embed_submit_then_status() -> None:
    """Round-trip test: submit a doc, then check its status."""
    submit_resp = client.post(
        "/v1/mcp/embed/submit",
        json={
            "doc_ref": {"content": "round trip test"},
            "model_id": "mini-embed-v1",
            "canonicalizer_id": "docling.c14n.v1",
        },
    )
    job_id = submit_resp.json()["result"]["job_id"]

    status_resp = client.post(
        "/v1/mcp/embed/status",
        json={"job_id": job_id},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["result"]["state"] in ("queued", "running", "complete")


# ── Intent routing ─────────────────────────────────────────────

def test_intent_embed_document() -> None:
    response = client.post(
        "/v1/mcp/intent",
        json={
            "intent": "EMBED_DOCUMENT",
            "payload": {
                "doc_ref": {"content": "intent test"},
                "model_id": "mini-embed-v1",
                "canonicalizer_id": "docling.c14n.v1",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["result"]["tool"] == "embed.submit"


def test_intent_unknown() -> None:
    response = client.post(
        "/v1/mcp/intent",
        json={"intent": "UNKNOWN_INTENT", "payload": {}},
    )
    assert response.status_code == 400
    assert "UNKNOWN_INTENT" in response.json()["detail"]["code"]


# ── Avatar completion ──────────────────────────────────────────

def test_avatar_complete_not_configured() -> None:
    """Without a real API key, should return 503."""
    with patch.dict("os.environ", {"LLM_API_KEY": ""}, clear=False):
        response = client.post(
            "/v1/mcp/avatar/complete",
            json={
                "avatars": [
                    {"avatar_name": "TestAvatar", "system_prompt": "test prompt"}
                ]
            },
        )
        assert response.status_code == 503


def test_avatar_complete_with_mock() -> None:
    """With mocked Codestral client, should return structured results."""
    mock_response = {
        "choices": [{"message": {"content": '[{"action":"test","priority":1,"context":"ok"}]'}}],
        "model": "codestral-latest",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
    }

    with patch.dict("os.environ", {"LLM_API_KEY": "test-key", "LLM_ENDPOINT": "http://mock"}, clear=False):
        with patch("app.world_model_skill.CodestralClient.complete", new_callable=AsyncMock, return_value=mock_response):
            response = client.post(
                "/v1/mcp/avatar/complete",
                json={
                    "avatars": [
                        {"avatar_name": "MockAvatar", "system_prompt": "generate tokens"}
                    ]
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["result"]["completed"] == 1

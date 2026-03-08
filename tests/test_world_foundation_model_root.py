from __future__ import annotations

from world_foundation_model import build_world_foundation_model
from app.mcp_tooling import call_tool_by_name
from orchestrator.multimodal_worldline import build_worldline_block


def test_root_world_foundation_model_embeds_coding_agent_avatars():
    block = build_world_foundation_model(
        prompt="Build MCP runtime from local world foundation model",
        repository="adaptco/A2A_MCP",
        commit_sha="abc123",
        actor="tester",
        cluster_count=4,
    )
    avatars = block["infrastructure_agent"]["coding_agent_avatars"]
    assert avatars
    assert any(item["agent_name"] == "CoderAgent" for item in avatars)
    assert all("avatar_id" in item for item in avatars)


def test_orchestrator_worldline_shim_uses_root_foundation_model():
    block = build_worldline_block(
        prompt="Refactor world foundation model",
        repository="adaptco/A2A_MCP",
        commit_sha="abc123",
        actor="tester",
        cluster_count=3,
    )
    assert "coding_agent_avatars" in block["infrastructure_agent"]


def test_mcp_tooling_exposes_world_foundation_model_tool():
    result = call_tool_by_name(
        tool_name="build_local_world_foundation_model",
        arguments={
            "prompt": "Create MCP server payload from local world model",
            "repository": "adaptco/A2A_MCP",
            "commit_sha": "abc123",
            "actor": "tester",
            "cluster_count": 4,
        },
    )
    assert result["ok"] is True
    assert result["data"]["pipeline"] == "qube-multimodal-worldline"

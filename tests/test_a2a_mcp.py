"""
Test module for A2A MCP.
"""
try:
    import torch
except ImportError:
    from unittest.mock import MagicMock, PropertyMock
    torch = MagicMock()
    # Mock randn to return an object with a .shape attribute for compatibility
    torch.randn.return_value = MagicMock()
    type(torch.randn.return_value).shape = PropertyMock(return_value=(1, 4096))
import pytest
from a2a_mcp.runtime import MCPADKRuntime  # pylint: disable=import-error,no-name-in-module
from a2a_mcp.event_store import PostgresEventStore  # pylint: disable=import-error,no-name-in-module
from a2a_mcp.core import A2AMCP  # pylint: disable=import-error,no-name-in-module

@pytest.mark.asyncio
async def test_end_to_end_orchestration():
    """Test end to end orchestration."""
    runtime = MCPADKRuntime(use_real_llm=False)
    ci_cd_embeddings = torch.randn(2, 4096)
    result = await runtime.orchestrate(ci_cd_embeddings, "Test Task")

    assert "mcp_token" in result
    assert "wasm_artifact" in result
    assert len(result["wasm_artifact"]) > 0
    assert result["runtime_ready"] is True

@pytest.mark.asyncio
async def test_event_store_integrity():
    """Test event store integrity."""
    store = PostgresEventStore()
    await store.append_event("T1", "E1", "TEST", {"data": 1})
    await store.append_event("T1", "E1", "TEST", {"data": 2})

    # Initial integrity check
    assert await store.verify_integrity() is True

    # Tamper with data
    store.events[0]["payload"]["data"] = 999

    # Integrity check should now fail
    assert await store.verify_integrity() is False

def test_token_generation():
    """Test token generation."""
    mcp = A2AMCP()
    embeddings = torch.randn(5, 4096)
    token = mcp.ci_cd_embedding_to_token(embeddings)

    assert token.embedding.shape == (1, 4096)
    assert token.phase_diagram.shape == (128, 256)
    assert len(token.arbitration_scores) == 10

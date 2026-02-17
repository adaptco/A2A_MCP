import torch
import pytest
import asyncio
from a2a_mcp.runtime import MCPADKRuntime
from a2a_mcp.event_store import PostgresEventStore
from a2a_mcp.core import A2AMCP

@pytest.mark.asyncio
async def test_end_to_end_orchestration():
    runtime = MCPADKRuntime(use_real_llm=False)
    ci_cd_embeddings = torch.randn(2, 4096)
    result = await runtime.orchestrate(ci_cd_embeddings, "Test Task")
    
    assert "mcp_token" in result
    assert "wasm_artifact" in result
    assert len(result["wasm_artifact"]) > 0
    assert result["runtime_ready"] is True

@pytest.mark.asyncio
async def test_event_store_integrity():
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
    mcp = A2AMCP()
    embeddings = torch.randn(5, 4096)
    token = mcp.ci_cd_embedding_to_token(embeddings)
    
    assert token.embedding.shape == (1, 4096)
    assert token.phase_diagram.shape == (128, 256)
    assert len(token.arbitration_scores) == 10

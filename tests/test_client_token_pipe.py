import pytest

torch = pytest.importorskip("torch")

from a2a_mcp.client_token_pipe import (
    ClientContext,
    ClientTokenPipe,
    ContaminationError,
    InMemoryEventStore,
)
from a2a_mcp.mcp_core import MCPCore


@pytest.mark.asyncio
async def test_client_token_pipe_maintains_namespace_isolation():
    torch.manual_seed(17)
    core = MCPCore()
    raw = torch.randn(1, 4096)

    ctx_a = ClientContext(tenant_id="tenant-a", tenant_vector=torch.ones(4096))
    ctx_b = ClientContext(
        tenant_id="tenant-b",
        tenant_vector=torch.cat([torch.ones(2048), torch.zeros(2048)]),
    )

    pipe_a = ClientTokenPipe(ctx=ctx_a, core=core, store=InMemoryEventStore())
    pipe_b = ClientTokenPipe(ctx=ctx_b, core=core, store=InMemoryEventStore())

    result_a = await pipe_a.process(raw)
    result_b = await pipe_b.process(raw)

    assert result_a["tenant_id"] != result_b["tenant_id"]
    assert result_a["sovereignty_hash"] != result_b["sovereignty_hash"]
    assert result_a["mcp_tensor"] != result_b["mcp_tensor"]


@pytest.mark.asyncio
async def test_client_token_pipe_quarantines_on_drift_violation():
    torch.manual_seed(23)
    core = MCPCore()
    store = InMemoryEventStore()
    ctx = ClientContext(tenant_id="tenant-q", tenant_vector=torch.ones(4096))
    pipe = ClientTokenPipe(ctx=ctx, core=core, store=store, contamination_threshold=0.01)

    _ = await pipe.process(torch.randn(1, 4096))

    with pytest.raises(ContaminationError):
        await pipe.process(-torch.randn(1, 4096))

    assert pipe.is_quarantined is True


@pytest.mark.asyncio
async def test_client_token_pipe_commits_event_payload():
    torch.manual_seed(29)
    core = MCPCore()
    store = InMemoryEventStore()
    ctx = ClientContext(tenant_id="tenant-events", tenant_vector=torch.ones(4096))
    pipe = ClientTokenPipe(ctx=ctx, core=core, store=store)

    result = await pipe.process(torch.randn(1, 4096))

    assert result["tenant_id"] == "tenant-events"
    assert len(store.events) == 1
    event = store.events[0]
    assert event["state"] == "MCP_PROCESSED"
    assert event["tenant_id"] == "tenant-events"
    assert "mcp_result_hash" in event["payload"]
    assert "drift_score" in event["payload"]
    assert "arbitration_top_roles" in event["payload"]

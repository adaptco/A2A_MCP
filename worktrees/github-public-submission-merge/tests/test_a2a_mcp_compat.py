import pytest

torch = pytest.importorskip("torch")

from a2a_mcp import (
    ClientContext,
    ClientTokenPipe,
    InMemoryEventStore,
    MCPCore,
    namespace_project_embedding,
)


def test_a2a_mcp_namespace_exports_work():
    core = MCPCore(input_dim=4096, hidden_dim=128, n_roles=32)
    raw = torch.randn(1, 4096)
    tenant_vec = torch.randn(4096)
    namespaced = namespace_project_embedding(raw, tenant_vec)
    assert tuple(namespaced.shape) == (1, 4096)

    ctx = ClientContext(tenant_id="tenant-z")
    pipe = ClientTokenPipe(ctx=ctx, store=InMemoryEventStore())
    assert pipe.ctx.tenant_id == "tenant-z"
    assert core.hidden_dim == 128

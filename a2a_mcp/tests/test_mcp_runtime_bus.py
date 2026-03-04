import pytest
from mcp.kernel.kernel import HardenedKernel, ExecutionEvent, TransitionType, Lineage
from mcp.kernel.store import InMemoryStore


@pytest.mark.asyncio
async def test_v02_finalization_enforcement():
    kernel = HardenedKernel(InMemoryStore())
    t_id, e_id = "tenant_42", "exec_888"

    # 1. Start and Finalize
    kernel.store.append(ExecutionEvent(
        tenant_id=t_id, execution_id=e_id,
        transition=TransitionType.FINALIZED, version=1, payload={}
    ))

    # 2. Attempt to dispatch after finalization
    with pytest.raises(PermissionError) as exc:
        await kernel.dispatch_tool(t_id, e_id, "transfer_funds", {"amount": 100})

    assert "is FINALIZED" in str(exc.value)

def test_v02_lineage_isolation():
    # Ensure hash(Tenant A, Exec 1) != hash(Tenant B, Exec 1) even with identical payloads
    payload = {"data": "same"}
    h1 = Lineage.generate("Tenant_A", "E1", "START", payload, 1).state_hash
    h2 = Lineage.generate("Tenant_B", "E1", "START", payload, 1).state_hash

    assert h1 != h2, "Cross-tenant hash collision detected!"

import pytest
from orchestrator.main import MCPHub
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_healing_loop_convergence():
    """
    Validates the Phase 2 'Self-Healing' logic.
    Tests if the hub can successfully transition from a FAIL to a PASS state.
    """
    hub = MCPHub()
    
    # Mocking the agents to simulate a failure then a success
    hub.coder.generate_solution = AsyncMock()
    hub.tester.validate = AsyncMock()

    # 1. First iteration: Tester finds a bug (FAIL)
    # 2. Second iteration: Tester verifies the fix (PASS)
    hub.tester.validate.side_effect = [
        AsyncMock(status="FAIL", critique="Syntax error on line 5"),
        AsyncMock(status="PASS", critique="Logic verified")
    ]

    # Mock coder artifacts for each iteration
    mock_art_v1 = AsyncMock(artifact_id="art-v1", agent_name="CoderAgent-Alpha")
    mock_art_v2 = AsyncMock(artifact_id="art-v2", agent_name="CoderAgent-Alpha")
    hub.coder.generate_solution.side_effect = [mock_art_v1, mock_art_v2]

    # Execute the loop
    task = "Implement secure file-deletion"
    final_result = await hub.run_healing_loop(task, max_retries=2)

    # Assertions
    assert final_result.artifact_id == "art-v2"
    assert hub.tester.validate.call_count == 2
    print(f"✓ Self-healing loop converged on artifact: {final_result.artifact_id}")

if __name__ == "__main__":
    pytest.main([__file__])

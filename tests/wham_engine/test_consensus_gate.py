import pytest
import asyncio
from wham_engine.gates.consensus import LLMConsensusGate, MockMCPProvider

@pytest.mark.asyncio
async def test_consensus_quorum_met():
    """Test that consensus is reached when enough providers pass."""
    gate = LLMConsensusGate(required_quorum=0.66)

    # 2 out of 3 pass (66%)
    gate.register_provider(MockMCPProvider("model-a", should_pass=True))
    gate.register_provider(MockMCPProvider("model-b", should_pass=True))
    gate.register_provider(MockMCPProvider("model-c", should_pass=False))

    receipt = await gate.validate_invariant({"id": "artifact-1"}, "C5 symmetry")

    assert receipt["verified"] is True
    assert receipt["quorum_achieved"] == "2/3"
    assert len(receipt["providers"]) == 3
    assert receipt["merkle_root"] != ""

@pytest.mark.asyncio
async def test_consensus_quorum_failed():
    """Test that consensus fails when quorum is not met."""
    gate = LLMConsensusGate(required_quorum=0.66)

    # 1 out of 3 pass (33%)
    gate.register_provider(MockMCPProvider("model-a", should_pass=True))
    gate.register_provider(MockMCPProvider("model-b", should_pass=False))
    gate.register_provider(MockMCPProvider("model-c", should_pass=False))

    receipt = await gate.validate_invariant({"id": "artifact-1"}, "RSM finish")

    assert receipt["verified"] is False
    assert receipt["quorum_achieved"] == "1/3"

@pytest.mark.asyncio
async def test_no_providers():
    """Test behavior with no providers registered."""
    gate = LLMConsensusGate()
    receipt = await gate.validate_invariant({}, "spec")

    assert receipt["verified"] is False
    assert "error" in receipt

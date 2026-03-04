"""
LoRA Test Harness
Validates LoRA training data synthesis, instruction format, and style adaptation.
"""

import pytest
import uuid
from schemas.model_artifact import ModelArtifact, AgentLifecycleState, LoRAConfig
from mlops.data_prep import synthesize_lora_training_data


# --- Simulated LoRA Components ---


# --- Fixtures ---

@pytest.fixture
def recovery_nodes():
    """Simulated vector nodes from the knowledge store."""
    return [
        {
            "text": "Connection timeout on port 5432. Retry with exponential backoff.",
            "metadata": {"type": "recovery_logic", "agent": "TesterAgent-Alpha"}
        },
        {
            "text": "NULL reference in storage layer. Add null-safety guard.",
            "metadata": {"type": "recovery_logic", "agent": "TesterAgent-Alpha"}
        },
        {
            "text": "Implement retry mechanism for transient failures.",
            "metadata": {"type": "code_solution", "agent": "CoderAgent-Alpha"}
        },
        {
            "text": "Architecture overview of MCP protocol.",
            "metadata": {"type": "research_doc", "agent": "Researcher_v1"}
        },
    ]


@pytest.fixture
def lora_config():
    return LoRAConfig(rank=8, alpha=16.0, target_modules=["q_proj", "v_proj"])


# --- Tests ---

class TestLoRADataSynthesis:
    """Test LoRA training data generation."""

    def test_synthesize_from_recovery_nodes(self, recovery_nodes):
        """Should generate training pairs from recovery_logic nodes."""
        data = synthesize_lora_training_data(recovery_nodes)
        
        # Only recovery_logic and code_solution nodes produce training data
        assert len(data) == 3  # 2 recovery + 1 code_solution
        print(f"✓ Synthesized {len(data)} training pairs")

    def test_instruction_format(self, recovery_nodes):
        """Each pair should have 'instruction' and 'output' keys."""
        data = synthesize_lora_training_data(recovery_nodes)
        
        for pair in data:
            assert "instruction" in pair
            assert "output" in pair
            assert pair["instruction"].startswith("SYSTEM:")
            assert pair["output"].startswith("ACTION:")
        
        print("✓ All pairs have correct format")

    def test_empty_nodes_produce_empty_data(self):
        """No matching nodes should produce empty training set."""
        data = synthesize_lora_training_data([])
        assert data == []
        
        # Nodes with wrong type should also produce empty
        data = synthesize_lora_training_data([
            {"text": "irrelevant", "metadata": {"type": "research_doc"}}
        ])
        assert data == []
        print("✓ Empty/unmatched nodes handled")

    def test_deterministic_synthesis(self, recovery_nodes):
        """Same nodes should produce identical training data."""
        data_1 = synthesize_lora_training_data(recovery_nodes)
        data_2 = synthesize_lora_training_data(recovery_nodes)
        
        assert data_1 == data_2
        print("✓ Deterministic synthesis verified")


class TestLoRAConfig:
    """Test LoRA configuration validation."""

    def test_default_config(self):
        """Default config should have standard values."""
        config = LoRAConfig()
        assert config.rank == 8
        assert config.alpha == 16.0
        assert "q_proj" in config.target_modules
        print("✓ Default LoRA config valid")

    def test_custom_config(self):
        """Custom rank/alpha should be accepted."""
        config = LoRAConfig(rank=16, alpha=32.0)
        # training_samples is likely not in __init__ but a field added later or optional
        config.training_samples = 100
        assert config.rank == 16
        assert config.training_samples == 100
        print("✓ Custom LoRA config valid")


class TestLoRAWithStateTransition:
    """Test LoRA adaptation within the agent lifecycle."""

    def test_lora_adapt_state(self, recovery_nodes, lora_config):
        """Artifact should transition to LORA_ADAPT with config attached."""
        artifact = ModelArtifact(
            artifact_id=str(uuid.uuid4()),
            model_id="sentence-transformers/all-mpnet-base-v2",
            weights_hash="sha256:4509c1ee",
            embedding_dim=768
        )
        
        # Walk to LORA_ADAPT
        artifact = artifact.transition(AgentLifecycleState.EMBEDDING)
        artifact = artifact.transition(AgentLifecycleState.RAG_QUERY)
        
        # Attach LoRA config
        training_data = synthesize_lora_training_data(recovery_nodes)
        lora_config.training_samples = len(training_data)
        artifact = artifact.model_copy(update={"lora_config": lora_config})
        
        artifact = artifact.transition(AgentLifecycleState.LORA_ADAPT)
        
        assert artifact.state == AgentLifecycleState.LORA_ADAPT
        assert artifact.lora_config.training_samples == 3
        print(f"✓ LORA_ADAPT with {artifact.lora_config.training_samples} training samples")

    def test_full_lifecycle_with_lora(self, recovery_nodes, lora_config):
        """Full lifecycle: INIT → ... → CONVERGED with LoRA."""
        artifact = ModelArtifact(
            artifact_id=str(uuid.uuid4()),
            model_id="sentence-transformers/all-mpnet-base-v2",
            weights_hash="sha256:4509c1ee",
            embedding_dim=768,
            lora_config=lora_config
        )
        
        states = [
            AgentLifecycleState.EMBEDDING,
            AgentLifecycleState.RAG_QUERY,
            AgentLifecycleState.LORA_ADAPT,
            AgentLifecycleState.HEALING,
            AgentLifecycleState.CONVERGED,
        ]
        
        for state in states:
            artifact = artifact.transition(state)
        
        assert artifact.state == AgentLifecycleState.CONVERGED
        assert artifact.lora_config is not None
        print("✓ Full lifecycle with LoRA converged")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

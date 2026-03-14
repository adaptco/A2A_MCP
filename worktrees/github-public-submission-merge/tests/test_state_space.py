import pytest
from schemas.model_artifact import ModelArtifact, AgentLifecycleState, LoRAConfig
from datetime import datetime

class TestStateSpace:
    def test_initialization(self):
        """Test that artifacts start in HANDSHAKE state."""
        artifact = ModelArtifact(
            artifact_id="test-1",
            model_id="mistralai/Mistral-7B-v0.1",
            weights_hash="sha256:1234567890abcdef",
            embedding_dim=4096,
            content="Initial model config"
        )
        assert artifact.state == AgentLifecycleState.HANDSHAKE
        assert artifact.version == "1.0.0"
        assert artifact.parent_artifact_id is None

    def test_legal_transitions(self):
        """Test valid state transitions."""
        artifact = ModelArtifact(
            artifact_id="test-1",
            model_id="mistralai/Mistral-7B-v0.1",
            weights_hash="sha256:1234567890abcdef",
            embedding_dim=4096,
            content="Initial model config"
        )
        
        # HANDSHAKE -> INIT
        init_artifact = artifact.transition(AgentLifecycleState.INIT)
        assert init_artifact.state == AgentLifecycleState.INIT
        assert init_artifact.parent_artifact_id == artifact.artifact_id
        assert init_artifact.artifact_id == artifact.artifact_id  # ID stays same, but new instance
        assert init_artifact is not artifact

        # INIT -> EMBEDDING
        next_artifact = init_artifact.transition(AgentLifecycleState.EMBEDDING)
        assert next_artifact.state == AgentLifecycleState.EMBEDDING
        assert next_artifact.parent_artifact_id == init_artifact.artifact_id

        # EMBEDDING -> RAG_QUERY
        rag_artifact = next_artifact.transition(AgentLifecycleState.RAG_QUERY)
        assert rag_artifact.state == AgentLifecycleState.RAG_QUERY

    def test_illegal_transitions(self):
        """Test invalid state transitions raise ValueError."""
        artifact = ModelArtifact(
            artifact_id="test-1",
            model_id="mistralai/Mistral-7B-v0.1",
            weights_hash="sha256:1234567890abcdef",
            embedding_dim=4096,
            content="Initial model config"
        )
        
        # HANDSHAKE -> CONVERGED (skip steps) is illegal
        with pytest.raises(ValueError) as excinfo:
            artifact.transition(AgentLifecycleState.CONVERGED)
        assert "Invalid transition" in str(excinfo.value)

    def test_immutability(self):
        """Ensure transitions return new instances."""
        artifact = ModelArtifact(
            artifact_id="test-1",
            model_id="mistralai/Mistral-7B-v0.1",
            weights_hash="sha256:1234567890abcdef",
            embedding_dim=4096,
            content="Initial model config"
        )
        
        init_artifact = artifact.transition(AgentLifecycleState.INIT)
        transitioned = init_artifact.transition(AgentLifecycleState.EMBEDDING)

        # Original should be unchanged
        assert artifact.state == AgentLifecycleState.HANDSHAKE
        assert init_artifact.state == AgentLifecycleState.INIT
        assert transitioned.state == AgentLifecycleState.EMBEDDING

        # Timestamps should differ (if slow enough, but at least exist)
        assert transitioned.timestamp >= init_artifact.timestamp

    def test_lora_config(self):
        """Test LoRA configuration handling."""
        lora_config = LoRAConfig(r=16, lora_alpha=64)
        artifact = ModelArtifact(
            artifact_id="test-lora",
            model_id="mistralai/Mistral-7B-v0.1",
            weights_hash="sha256:lora",
            embedding_dim=4096,
            content="LoRA model",
            lora_config=lora_config
        )
        
        assert artifact.lora_config.r == 16
        assert artifact.lora_config.lora_alpha == 64
        
        # Transition should preserve LoRA config
        init_artifact = artifact.transition(AgentLifecycleState.INIT)
        next_artifact = init_artifact.transition(AgentLifecycleState.EMBEDDING)
        assert next_artifact.lora_config.r == 16

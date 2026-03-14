import pytest
from schemas.model_artifact import ModelArtifact, AgentLifecycleState, LoRAConfig

class TestCICDPipeline:
    def test_end_to_end_lifecycle(self):
        """
        Verify the complete agent lifecycle from initialization to convergence.
        """
        # 1. Pipeline Start: HANDSHAKE
        agent = ModelArtifact(
            artifact_id="release-v1",
            model_id="mistralai/Mistral-7B-v0.1",
            weights_hash="hash:123",
            embedding_dim=4096,
            content="Agent configuration v1"
        )
        assert agent.state == AgentLifecycleState.HANDSHAKE

        # 2. Handshake complete -> INIT
        agent = agent.transition(AgentLifecycleState.INIT)
        assert agent.state == AgentLifecycleState.INIT
        
        # 3. Embedding Generation
        # Simulate successful embedding
        agent = agent.transition(AgentLifecycleState.EMBEDDING)
        assert agent.state == AgentLifecycleState.EMBEDDING
        assert agent.parent_artifact_id == "release-v1"
        
        # 4. RAG Query
        # Simulate retrieval of context
        agent = agent.transition(AgentLifecycleState.RAG_QUERY)
        assert agent.state == AgentLifecycleState.RAG_QUERY
        
        # 5. LoRA Adaptation
        # Attach LoRA config
        lora_cfg = LoRAConfig(r=8, lora_alpha=16)
        # In a real pipeline, the adapter step adds this config
        agent = agent.model_copy(update={"lora_config": lora_cfg})
        agent = agent.transition(AgentLifecycleState.LORA_ADAPT)
        
        assert agent.state == AgentLifecycleState.LORA_ADAPT
        assert agent.lora_config.r == 8
        
        # 6. Healing / Self-Correction
        agent = agent.transition(AgentLifecycleState.HEALING)
        assert agent.state == AgentLifecycleState.HEALING
        
        # 7. Convergence
        agent = agent.transition(AgentLifecycleState.CONVERGED)
        assert agent.state == AgentLifecycleState.CONVERGED

    def test_pipeline_failure_recovery(self):
        """Verify pipeline can handle failures and rollback."""
        agent = ModelArtifact(
            artifact_id="release-fail",
            model_id="mistralai/Mistral-7B-v0.1",
            weights_hash="hash:123",
            embedding_dim=4096,
            state=AgentLifecycleState.EMBEDDING
        )
        
        # Simulate failure during step
        failed = agent.transition(AgentLifecycleState.FAILED)
        assert failed.state == AgentLifecycleState.FAILED
        
        # Recover to INIT for retry
        recovered = failed.transition(AgentLifecycleState.INIT)
        assert recovered.state == AgentLifecycleState.INIT
        assert recovered.parent_artifact_id == failed.artifact_id

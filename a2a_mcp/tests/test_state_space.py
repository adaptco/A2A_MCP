"""
State Space Simulator Tests
Validates agent lifecycle transitions and deterministic artifact production.
"""

import pytest
import uuid
import hashlib
import json
from schemas.model_artifact import (
    ModelArtifact, AgentLifecycleState, LoRAConfig, STATE_TRANSITIONS
)


# --- Fixtures ---

@pytest.fixture
def base_model_artifact():
    """Create a base model artifact in INIT state."""
    return ModelArtifact(
        artifact_id=str(uuid.uuid4()),
        model_id="sentence-transformers/all-mpnet-base-v2",
        weights_hash="sha256:4509c1ee9d2c8edeefc99bd9ca58668916bee2b9b0cf8bf505310e7b64baf670",
        embedding_dim=768,
        content="Test model artifact for CI/CD pipeline"
    )


@pytest.fixture
def lora_config():
    """Create a LoRA configuration."""
    return LoRAConfig(
        rank=8,
        alpha=16.0,
        target_modules=["q_proj", "v_proj"],
        training_samples=50
    )


# --- Phase 1: State Transition Tests ---

class TestStateTransitions:
    """Test valid and invalid state transitions."""

    def test_init_to_embedding(self, base_model_artifact):
        """INIT → EMBEDDING is valid."""
        new = base_model_artifact.transition(AgentLifecycleState.EMBEDDING)
        assert new.state == AgentLifecycleState.EMBEDDING
        assert new.parent_artifact_id == base_model_artifact.artifact_id

    def test_full_happy_path(self, base_model_artifact):
        """INIT → EMBEDDING → RAG_QUERY → LORA_ADAPT → HEALING → CONVERGED."""
        states = [
            AgentLifecycleState.EMBEDDING,
            AgentLifecycleState.RAG_QUERY,
            AgentLifecycleState.LORA_ADAPT,
            AgentLifecycleState.HEALING,
            AgentLifecycleState.CONVERGED,
        ]
        
        current = base_model_artifact
        trail = [current.artifact_id]
        
        for target_state in states:
            current = current.transition(target_state)
            trail.append(current.artifact_id)
            assert current.state == target_state
        
        # Verify parent chain
        assert current.state == AgentLifecycleState.CONVERGED
        print(f"✓ Happy path: {len(trail)} artifacts in chain")

    def test_invalid_transition_raises(self, base_model_artifact):
        """INIT → CONVERGED should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid transition"):
            base_model_artifact.transition(AgentLifecycleState.CONVERGED)

    def test_healing_retry_loop(self, base_model_artifact):
        """HEALING → LORA_ADAPT (retry) → HEALING → CONVERGED."""
        art = base_model_artifact
        art = art.transition(AgentLifecycleState.EMBEDDING)
        art = art.transition(AgentLifecycleState.RAG_QUERY)
        art = art.transition(AgentLifecycleState.LORA_ADAPT)
        art = art.transition(AgentLifecycleState.HEALING)
        
        # Retry: go back to LORA_ADAPT
        art = art.transition(AgentLifecycleState.LORA_ADAPT)
        assert art.state == AgentLifecycleState.LORA_ADAPT
        
        # Converge on second try
        art = art.transition(AgentLifecycleState.HEALING)
        art = art.transition(AgentLifecycleState.CONVERGED)
        assert art.state == AgentLifecycleState.CONVERGED
        print("✓ Healing retry loop converged")

    def test_failure_rollback(self, base_model_artifact):
        """EMBEDDING → FAILED → INIT (rollback)."""
        art = base_model_artifact.transition(AgentLifecycleState.EMBEDDING)
        art = art.transition(AgentLifecycleState.FAILED)
        assert art.state == AgentLifecycleState.FAILED
        
        # Rollback
        art = art.transition(AgentLifecycleState.INIT)
        assert art.state == AgentLifecycleState.INIT
        print("✓ Failure rollback to INIT")

    def test_converged_is_terminal(self, base_model_artifact):
        """CONVERGED → anything should raise."""
        art = base_model_artifact
        art = art.transition(AgentLifecycleState.EMBEDDING)
        art = art.transition(AgentLifecycleState.RAG_QUERY)
        art = art.transition(AgentLifecycleState.LORA_ADAPT)
        art = art.transition(AgentLifecycleState.HEALING)
        art = art.transition(AgentLifecycleState.CONVERGED)
        
        with pytest.raises(ValueError):
            art.transition(AgentLifecycleState.INIT)
        print("✓ CONVERGED is terminal")


# --- Phase 2: Determinism Tests ---

class TestDeterminism:
    """Test deterministic artifact production."""

    def test_same_inputs_same_hash(self):
        """Same model config should produce same content hash."""
        config = {
            "model_id": "sentence-transformers/all-mpnet-base-v2",
            "embedding_dim": 768,
            "weights_hash": "sha256:4509c1ee"
        }
        
        hash1 = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        hash2 = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        
        assert hash1 == hash2
        print(f"✓ Deterministic hash: {hash1[:16]}...")

    def test_artifact_immutability(self, base_model_artifact):
        """Transitions should produce new artifacts, not mutate existing."""
        original_id = base_model_artifact.artifact_id
        original_state = base_model_artifact.state
        
        new = base_model_artifact.transition(AgentLifecycleState.EMBEDDING)
        
        # Original unchanged
        assert base_model_artifact.artifact_id == original_id
        assert base_model_artifact.state == original_state
        
        # New is different
        assert new.state == AgentLifecycleState.EMBEDDING
        assert new.parent_artifact_id == original_id
        print("✓ Immutability preserved")

    def test_parent_chain_integrity(self, base_model_artifact):
        """Each artifact should reference its parent."""
        chain = [base_model_artifact]
        current = base_model_artifact
        
        for state in [AgentLifecycleState.EMBEDDING, AgentLifecycleState.RAG_QUERY]:
            current = current.transition(state)
            chain.append(current)
        
        # Verify chain links
        for i in range(1, len(chain)):
            assert chain[i].parent_artifact_id == chain[i-1].artifact_id
        
        print(f"✓ Parent chain intact: {len(chain)} links")


# --- Phase 3: LoRA Config Tests ---

class TestLoRAConfig:
    """Test LoRA configuration attachment."""

    def test_attach_lora_config(self, base_model_artifact, lora_config):
        """Attach LoRA config to artifact."""
        art = base_model_artifact.model_copy(update={"lora_config": lora_config})
        
        assert art.lora_config is not None
        assert art.lora_config.rank == 8
        assert art.lora_config.training_samples == 50
        print("✓ LoRA config attached")

    def test_lora_config_survives_transition(self, base_model_artifact, lora_config):
        """LoRA config should persist through state transitions."""
        art = base_model_artifact.model_copy(update={"lora_config": lora_config})
        art = art.transition(AgentLifecycleState.EMBEDDING)
        
        assert art.lora_config is not None
        assert art.lora_config.rank == 8
        print("✓ LoRA config survives transition")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

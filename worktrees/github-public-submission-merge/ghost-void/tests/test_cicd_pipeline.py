"""
CI/CD Pipeline Runner Tests
End-to-end test: Model Artifact → Embedding → RAG → LoRA → Self-Healing → Converged
"""

import pytest
import uuid
import hashlib
import json
from schemas.model_artifact import ModelArtifact, AgentLifecycleState, LoRAConfig


# --- Simulated Pipeline Components ---

class PipelineStage:
    """Represents a stage in the CI/CD pipeline."""
    
    def __init__(self, name: str, target_state: AgentLifecycleState):
        self.name = name
        self.target_state = target_state
        self.executed = False
        self.artifact_id = None
    
    def execute(self, artifact: ModelArtifact) -> ModelArtifact:
        new_artifact = artifact.transition(self.target_state)
        self.executed = True
        self.artifact_id = new_artifact.artifact_id
        return new_artifact


class CICDPipelineRunner:
    """
    Orchestrates the full CI/CD pipeline for model artifacts.
    Each stage produces a traceable artifact with parent chain.
    """
    
    def __init__(self):
        self.stages = [
            PipelineStage("Embedding", AgentLifecycleState.EMBEDDING),
            PipelineStage("RAG Query", AgentLifecycleState.RAG_QUERY),
            PipelineStage("LoRA Adapt", AgentLifecycleState.LORA_ADAPT),
            PipelineStage("Healing", AgentLifecycleState.HEALING),
            PipelineStage("Convergence", AgentLifecycleState.CONVERGED),
        ]
        self.artifact_chain = []
        self.execution_log = []
    
    def run(self, initial_artifact: ModelArtifact) -> ModelArtifact:
        """Run the full pipeline."""
        current = initial_artifact
        self.artifact_chain.append(current)
        
        for stage in self.stages:
            try:
                current = stage.execute(current)
                self.artifact_chain.append(current)
                self.execution_log.append({
                    "stage": stage.name,
                    "state": current.state.value,
                    "artifact_id": current.artifact_id,
                    "parent_id": current.parent_artifact_id,
                    "status": "SUCCESS"
                })
            except Exception as e:
                self.execution_log.append({
                    "stage": stage.name,
                    "status": "FAILED",
                    "error": str(e)
                })
                raise
        
        return current
    
    def verify_chain_integrity(self) -> bool:
        """Verify parent-child chain across all artifacts."""
        for i in range(1, len(self.artifact_chain)):
            if self.artifact_chain[i].parent_artifact_id != self.artifact_chain[i-1].artifact_id:
                return False
        return True
    
    def get_execution_report(self) -> dict:
        """Generate pipeline execution report."""
        return {
            "total_stages": len(self.stages),
            "executed_stages": sum(1 for s in self.stages if s.executed),
            "artifact_count": len(self.artifact_chain),
            "chain_intact": self.verify_chain_integrity(),
            "final_state": self.artifact_chain[-1].state.value if self.artifact_chain else None,
            "log": self.execution_log
        }


# --- Fixtures ---

@pytest.fixture
def model_artifact():
    """Create a pipeline-ready model artifact."""
    return ModelArtifact(
        artifact_id=str(uuid.uuid4()),
        model_id="sentence-transformers/all-mpnet-base-v2",
        weights_hash="sha256:4509c1ee9d2c8edeefc99bd9ca58668916bee2b9b0cf8bf505310e7b64baf670",
        embedding_dim=768,
        version="1.0.0",
        lora_config=LoRAConfig(rank=8, alpha=16.0, training_samples=50),
        content="CI/CD pipeline test artifact"
    )


@pytest.fixture
def pipeline():
    return CICDPipelineRunner()


# --- Tests ---

class TestCICDPipeline:
    """End-to-end CI/CD pipeline tests."""

    def test_full_pipeline_run(self, pipeline, model_artifact):
        """Full pipeline should converge successfully."""
        result = pipeline.run(model_artifact)
        
        assert result.state == AgentLifecycleState.CONVERGED
        report = pipeline.get_execution_report()
        assert report["executed_stages"] == 5
        assert report["chain_intact"] is True
        
        print("✓ Full CI/CD pipeline converged")
        print(f"  Artifacts in chain: {report['artifact_count']}")

    def test_artifact_traceability(self, pipeline, model_artifact):
        """Each stage should produce a traceable artifact."""
        pipeline.run(model_artifact)
        
        report = pipeline.get_execution_report()
        
        # Every log entry should have artifact_id and parent_id
        for entry in report["log"]:
            assert entry["status"] == "SUCCESS"
            assert "artifact_id" in entry
            assert "parent_id" in entry
        
        print(f"✓ All {len(report['log'])} stages traceable")

    def test_chain_integrity(self, pipeline, model_artifact):
        """Parent-child chain should be intact."""
        pipeline.run(model_artifact)
        
        assert pipeline.verify_chain_integrity() is True
        
        # Verify manually
        chain = pipeline.artifact_chain
        for i in range(1, len(chain)):
            assert chain[i].parent_artifact_id == chain[i-1].artifact_id
        
        print(f"✓ Chain integrity verified: {len(chain)} links")

    def test_lora_config_persists(self, pipeline, model_artifact):
        """LoRA config should survive all pipeline stages."""
        result = pipeline.run(model_artifact)
        
        assert result.lora_config is not None
        assert result.lora_config.rank == 8
        assert result.lora_config.training_samples == 50
        print("✓ LoRA config persisted through pipeline")

    def test_deterministic_replay(self, model_artifact):
        """Two runs with same input should produce same state sequence."""
        pipeline_1 = CICDPipelineRunner()
        pipeline_2 = CICDPipelineRunner()
        
        result_1 = pipeline_1.run(model_artifact)
        result_2 = pipeline_2.run(model_artifact)
        
        # Same final state
        assert result_1.state == result_2.state
        
        # Same state sequence
        states_1 = [a.state.value for a in pipeline_1.artifact_chain]
        states_2 = [a.state.value for a in pipeline_2.artifact_chain]
        assert states_1 == states_2
        
        print(f"✓ Deterministic replay: {states_1}")

    def test_weights_hash_preserved(self, pipeline, model_artifact):
        """Model weights hash should be identical at every stage."""
        pipeline.run(model_artifact)
        
        original_hash = model_artifact.weights_hash
        for artifact in pipeline.artifact_chain:
            assert artifact.weights_hash == original_hash
        
        print(f"✓ Weights hash preserved: {original_hash[:20]}...")

    def test_execution_report_format(self, pipeline, model_artifact):
        """Report should have all required fields."""
        pipeline.run(model_artifact)
        report = pipeline.get_execution_report()
        
        required_keys = [
            "total_stages", "executed_stages", "artifact_count",
            "chain_intact", "final_state", "log"
        ]
        for key in required_keys:
            assert key in report
        
        assert report["final_state"] == "CONVERGED"
        print("✓ Execution report format valid")


class TestPipelineFailure:
    """Tests for pipeline failure handling."""

    def test_invalid_initial_state(self):
        """Starting from wrong state should fail at first stage."""
        bad_artifact = ModelArtifact(
            artifact_id=str(uuid.uuid4()),
            model_id="test",
            weights_hash="sha256:bad",
            embedding_dim=768,
            state=AgentLifecycleState.CONVERGED  # Already terminal
        )
        
        pipeline = CICDPipelineRunner()
        with pytest.raises(ValueError, match="Invalid transition"):
            pipeline.run(bad_artifact)
        
        print("✓ Pipeline correctly rejects invalid initial state")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

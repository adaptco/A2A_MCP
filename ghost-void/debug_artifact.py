
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    from schemas.model_artifact import ModelArtifact, AgentLifecycleState
    
    print("Import successful.")
    
    try:
        artifact = ModelArtifact(
            artifact_id="t1", 
            model_id="tetris", 
            weights_hash="h1",
            embedding_dim=1,
            category="gaming", 
            state=AgentLifecycleState.SCORE_FINALIZED, 
            content="score event",
            metadata={"score": 100}
        )
        print("Instantiation successful.")
        print(f"Artifact metadata: {artifact.metadata}")
    except Exception as e:
        print(f"Instantiation failed: {e}")
        import traceback
        traceback.print_exc()

except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()

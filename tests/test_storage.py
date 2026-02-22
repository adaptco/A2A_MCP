import pytest
from orchestrator.storage import DBManager
from schemas.agent_artifacts import MCPArtifact
import json
import uuid
import json

def test_artifact_persistence_lifecycle():
    """
    Validates the 'Schematic Rigor' directive by testing 
    the full Save -> Retrieve cycle.
    """
    db = DBManager()
    test_id = str(uuid.uuid4())
    
    # 1. Setup Mock Artifact
    artifact_content = {"status": "verified"}
    artifact = MCPArtifact(
        artifact_id=test_id,
        type="unit_test_artifact",
        content="{\"status\": \"verified\"}"
    )

    # 2. Test Save (Persistence Directive)
    db.save_artifact(artifact)

    # 3. Test Retrieval (Traceability Directive)
    retrieved = db.get_artifact(test_id)
    
    assert retrieved is not None
    assert retrieved.agent_name == "TestAgent"
    content_payload = json.loads(retrieved.content)
    assert content_payload["status"] == "verified"
    print(f"✓ Persistence Lifecycle Verified for ID: {test_id}")

if __name__ == "__main__":
    test_artifact_persistence_lifecycle()

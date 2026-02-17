import json
import pytest
from orchestrator.storage import DBManager
from schemas.agent_artifacts import MCPArtifact
import json
import uuid
<<<<<<< HEAD
from types import SimpleNamespace
=======
import json
>>>>>>> 117e2e444ff3d500482857ebf717156179fbdeed

def test_artifact_persistence_lifecycle():
    """
    Validates the 'Schematic Rigor' directive by testing 
    the full Save -> Retrieve cycle.
    """
    db = DBManager()
    test_id = str(uuid.uuid4())
    
    # Use SimpleNamespace to create an object with the attributes that
    # DBManager.save_artifact reads via getattr (agent_name, version, etc.)
    artifact = SimpleNamespace(
        artifact_id=test_id,
        parent_artifact_id="root-node",
        agent_name="TestAgent",
        version="1.0.0",
        type="unit_test_artifact",
<<<<<<< HEAD
        content='{"status": "verified"}',
=======
        content="{\"status\": \"verified\"}"
>>>>>>> 117e2e444ff3d500482857ebf717156179fbdeed
    )

    # Test Save (Persistence Directive)
    db.save_artifact(artifact)

    # Test Retrieval (Traceability Directive)
    retrieved = db.get_artifact(test_id)
    
    assert retrieved is not None
    assert retrieved.agent_name == "TestAgent"
<<<<<<< HEAD
<<<<<<< HEAD
    assert '"status"' in retrieved.content
=======
    content_payload = json.loads(retrieved.content)
    assert content_payload["status"] == "verified"
>>>>>>> 117e2e444ff3d500482857ebf717156179fbdeed
=======
    content = json.loads(retrieved.content) if isinstance(retrieved.content, str) else retrieved.content
    assert content["status"] == "verified"
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe
    print(f"✓ Persistence Lifecycle Verified for ID: {test_id}")

if __name__ == "__main__":
    test_artifact_persistence_lifecycle()

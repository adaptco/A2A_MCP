import pytest
from orchestrator.rag_store import RAGVectorStore
from orchestrator.storage import DBManager
from schemas.hmlsl import HMLSLArtifact, StructuralNode, BehavioralTraceNode

class MockDBManager:
    """Mock DB manager for testing."""
    def __init__(self):
        self.artifacts = {}

    def save_artifact(self, artifact):
        self.artifacts[artifact.id] = artifact

@pytest.fixture
def rag_store():
    db = MockDBManager()
    return RAGVectorStore(db)

def test_hmlsl_ingestion_and_search(rag_store):
    plan_id = "plan-rag-test"
    artifact = HMLSLArtifact(
        id=f"hmlsl-{plan_id}",
        structural_nodes=[
            StructuralNode(type="StructuralNode", contract_type="MCP_TOOL", definition={"name": "unity_render"})
        ],
        behavioral_traces=[
            BehavioralTraceNode(type="BehavioralTraceNode", step_description="Render scene with Unity", tool_invocation={"tool_name": "unity"}),
            BehavioralTraceNode(type="BehavioralTraceNode", step_description="Analyze logic", tool_invocation={"tool_name": "reasoning"})
        ]
    )

    rag_store.ingest_hmlsl_artifact(artifact)

    # Test 1: Search for "Unity"
    results = rag_store.search("unity", top_k=5)
    assert len(results) > 0

    # Test 2: Search with cluster filter (structural)
    structural_results = rag_store.search("unity", top_k=5, cluster_filter="structural")
    assert all(r["cluster"] == "structural" for r in structural_results)
    assert len(structural_results) > 0

    # Test 3: Search with cluster filter (behavioral)
    behavioral_results = rag_store.search("unity", top_k=5, cluster_filter="behavioral")
    assert all(r["cluster"] == "behavioral" for r in behavioral_results)
    assert len(behavioral_results) > 0

def test_hierarchy_indexing(rag_store):
    plan_id = "plan-hierarchy-test"
    artifact = HMLSLArtifact(
        id=f"hmlsl-{plan_id}",
        structural_nodes=[
            StructuralNode(type="StructuralNode", contract_type="A2A", definition={"name": "handshake"})
        ]
    )

    rag_store.ingest_hmlsl_artifact(artifact)

    # Test retrieving hierarchy by plan_id
    hierarchy = rag_store.get_context_hierarchy(plan_id)
    assert "structural" in hierarchy
    assert len(hierarchy["structural"]) == 1
    assert hierarchy["structural"][0] == artifact.structural_nodes[0].id

import pytest
from orchestrator.rag_store import RAGVectorStore

@pytest.fixture
def store():
    return RAGVectorStore()

def test_ingest_valid(store):
    valid_data = {
        "nodes": [{"id": "n1", "type": "Structural"}],
        "edges": []
    }

    result = store.ingest(valid_data)

    assert result["status"] == "INDEXED"
    assert result["receipt"].verdict == "ACCEPTED"
    assert result["id"] in store.index

def test_ingest_rejected(store):
    invalid_data = {
        "nodes": [{"id": "n1", "type": "Invalid"}],
        "edges": []
    }

    result = store.ingest(invalid_data)

    assert result["status"] == "REJECTED"
    assert len(store.index) == 0

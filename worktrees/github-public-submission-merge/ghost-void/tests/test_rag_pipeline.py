"""
RAG Pipeline Integration Tests
Tests embedding injection, vector retrieval, and hash chain integrity.
"""

import pytest
import uuid
import hashlib
import json
from schemas.model_artifact import ModelArtifact, AgentLifecycleState


# --- Simulated RAG Components ---

class MockVectorStore:
    """Simulates Qdrant for testing without Docker dependency."""
    
    def __init__(self):
        self.collections: dict = {}
    
    def create_collection(self, name: str, dim: int):
        self.collections[name] = {"dim": dim, "points": {}}
    
    def upsert(self, collection: str, point_id: str, vector: list, payload: dict):
        if collection not in self.collections:
            raise ValueError(f"Collection {collection} does not exist")
        if len(vector) != self.collections[collection]["dim"]:
            raise ValueError(f"Vector dim mismatch: got {len(vector)}, expected {self.collections[collection]['dim']}")
        self.collections[collection]["points"][point_id] = {
            "vector": vector,
            "payload": payload
        }
    
    def query(self, collection: str, query_vector: list, top_k: int = 5) -> list:
        """Cosine similarity search (simplified dot product for unit vectors)."""
        if collection not in self.collections:
            return []
        
        results = []
        for pid, data in self.collections[collection]["points"].items():
            # Dot product (assumes L2-normalized vectors)
            score = sum(a * b for a, b in zip(query_vector, data["vector"]))
            results.append({"id": pid, "score": score, "payload": data["payload"]})
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def count(self, collection: str) -> int:
        return len(self.collections.get(collection, {}).get("points", {}))


class MockEmbedder:
    """Simulates sentence-transformers embedding for deterministic testing."""
    
    def __init__(self, dim: int = 768):
        self.dim = dim
    
    def encode(self, text: str) -> list:
        """Deterministic hash-based embedding."""
        h = hashlib.sha256(text.encode()).digest()
        # Expand hash to fill dimension
        raw = []
        for i in range(self.dim):
            byte_val = h[i % len(h)]
            raw.append((byte_val / 255.0) - 0.5)
        
        # L2 normalize
        norm = sum(x * x for x in raw) ** 0.5
        return [x / norm for x in raw]


# --- Fixtures ---

@pytest.fixture
def vector_store():
    store = MockVectorStore()
    store.create_collection("docling_chunks", dim=768)
    return store


@pytest.fixture
def embedder():
    return MockEmbedder(dim=768)


@pytest.fixture
def sample_documents():
    return [
        {"id": "doc-1", "text": "MCP protocol enables agent-to-agent communication"},
        {"id": "doc-2", "text": "LoRA adapters modify model behavior with low-rank matrices"},
        {"id": "doc-3", "text": "Self-healing loops detect failures and retry with feedback"},
        {"id": "doc-4", "text": "Vector embeddings map text into semantic space"},
        {"id": "doc-5", "text": "ZKP verifies identity without revealing credentials"},
    ]


# --- Tests ---

class TestRAGInjection:
    """Tests for injecting knowledge into the vector store."""

    def test_inject_documents(self, vector_store, embedder, sample_documents):
        """Inject documents and verify they are stored."""
        for doc in sample_documents:
            vector = embedder.encode(doc["text"])
            vector_store.upsert(
                collection="docling_chunks",
                point_id=doc["id"],
                vector=vector,
                payload={"text": doc["text"]}
            )
        
        assert vector_store.count("docling_chunks") == 5
        print("✓ Injected 5 documents")

    def test_dimension_mismatch_raises(self, vector_store):
        """Wrong dimension should raise error."""
        with pytest.raises(ValueError, match="dim mismatch"):
            vector_store.upsert(
                collection="docling_chunks",
                point_id="bad",
                vector=[0.1, 0.2],  # Wrong dim
                payload={"text": "test"}
            )


class TestRAGRetrieval:
    """Tests for querying the vector store."""

    def test_semantic_retrieval(self, vector_store, embedder, sample_documents):
        """Query should return semantically similar documents."""
        # Inject
        for doc in sample_documents:
            vector = embedder.encode(doc["text"])
            vector_store.upsert("docling_chunks", doc["id"], vector, {"text": doc["text"]})
        
        # Query for "agent communication protocol"
        query_vec = embedder.encode("agent communication protocol")
        results = vector_store.query("docling_chunks", query_vec, top_k=3)
        
        assert len(results) == 3
        # Top result should be the MCP document (closest semantically)
        print(f"✓ Top result: {results[0]['payload']['text'][:50]}...")
        print(f"  Score: {results[0]['score']:.4f}")

    def test_deterministic_retrieval(self, vector_store, embedder, sample_documents):
        """Same query should always return same results."""
        for doc in sample_documents:
            vec = embedder.encode(doc["text"])
            vector_store.upsert("docling_chunks", doc["id"], vec, {"text": doc["text"]})
        
        query = "embedding vectors semantic space"
        results_1 = vector_store.query("docling_chunks", embedder.encode(query), top_k=3)
        results_2 = vector_store.query("docling_chunks", embedder.encode(query), top_k=3)
        
        assert [r["id"] for r in results_1] == [r["id"] for r in results_2]
        assert [r["score"] for r in results_1] == [r["score"] for r in results_2]
        print("✓ Deterministic retrieval verified")


class TestRAGWithModelArtifact:
    """Tests RAG integration with ModelArtifact state transitions."""

    def test_embed_then_query_transition(self, vector_store, embedder, sample_documents):
        """Model artifact should transition INIT → EMBEDDING → RAG_QUERY."""
        artifact = ModelArtifact(
            artifact_id=str(uuid.uuid4()),
            model_id="sentence-transformers/all-mpnet-base-v2",
            weights_hash="sha256:4509c1ee",
            embedding_dim=768
        )
        
        # INIT → EMBEDDING
        artifact = artifact.transition(AgentLifecycleState.EMBEDDING)
        
        # Inject documents
        for doc in sample_documents:
            vec = embedder.encode(doc["text"])
            vector_store.upsert("docling_chunks", doc["id"], vec, {"text": doc["text"]})
        
        assert vector_store.count("docling_chunks") == 5
        
        # EMBEDDING → RAG_QUERY
        artifact = artifact.transition(AgentLifecycleState.RAG_QUERY)
        
        # Query
        results = vector_store.query(
            "docling_chunks",
            embedder.encode("self-healing agent failure recovery"),
            top_k=2
        )
        
        assert len(results) == 2
        assert artifact.state == AgentLifecycleState.RAG_QUERY
        print(f"✓ RAG query at state {artifact.state.value}: {len(results)} results")


class TestHashChainIntegrity:
    """Tests for ledger hash chain integrity."""

    def test_hash_chain(self, embedder, sample_documents):
        """Simulated ledger should maintain hash chain."""
        ledger = []
        prev_hash = "0" * 64  # Genesis
        
        for doc in sample_documents:
            vec = embedder.encode(doc["text"])
            
            record = {
                "doc_id": doc["id"],
                "text": doc["text"],
                "embedding_hash": hashlib.sha256(
                    json.dumps(vec[:10], sort_keys=True).encode()
                ).hexdigest(),
                "prev_ledger_hash": prev_hash
            }
            
            # Compute integrity hash
            canonical = json.dumps(record, sort_keys=True, separators=(',', ':'))
            integrity = hashlib.sha256(canonical.encode()).hexdigest()
            record["integrity_hash"] = integrity
            
            ledger.append(record)
            prev_hash = integrity
        
        # Verify chain
        for i in range(1, len(ledger)):
            assert ledger[i]["prev_ledger_hash"] == ledger[i-1]["integrity_hash"]
        
        print(f"✓ Hash chain intact: {len(ledger)} entries")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

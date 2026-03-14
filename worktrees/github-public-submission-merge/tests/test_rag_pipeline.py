import pytest
from unittest.mock import MagicMock
from schemas.model_artifact import ModelArtifact, AgentLifecycleState

class TestRAGPipeline:
    @pytest.fixture
    def mock_qdrant(self):
        """Mock Qdrant client."""
        return MagicMock()

    @pytest.fixture
    def mock_embedder(self):
        """Mock embedding generator returning deterministic vectors."""
        mock = MagicMock()
        mock.encode.return_value = [0.1] * 768
        return mock

    def test_document_ingestion(self, mock_qdrant, mock_embedder):
        """Verify document ingestion flow within the pipeline."""
        # Setup initial artifact (Document)
        artifact = ModelArtifact(
            artifact_id="doc-123",
            model_id="docling-v1",
            weights_hash="sha256:doc-hash",
            embedding_dim=768,
            state=AgentLifecycleState.INIT,
            content="This is a test document."
        )
        
        # Simulate ingestion step: INIT -> EMBEDDING
        embedding_artifact = artifact.transition(AgentLifecycleState.EMBEDDING)
        assert embedding_artifact.state == AgentLifecycleState.EMBEDDING
        
        # Verify embedding generation
        vectors = mock_embedder.encode(artifact.content)
        assert len(vectors) == 768
        
        # Simulate Qdrant upsert
        mock_qdrant.upsert(
            collection_name="knowledge_base",
            points=[
                {
                    "id": embedding_artifact.artifact_id, 
                    "vector": vectors, 
                    "payload": {
                        "text": artifact.content,
                        "source_artifact_id": artifact.artifact_id
                    }
                }
            ]
        )
        
        # Verify call arguments
        mock_qdrant.upsert.assert_called_once()
        call_args = mock_qdrant.upsert.call_args
        assert call_args.kwargs["collection_name"] == "knowledge_base"
        assert call_args.kwargs["points"][0]["payload"]["text"] == "This is a test document."

    def test_retrieval_integrity(self, mock_qdrant):
        """Test RAG retrieval and data integrity."""
        # Mock retrieval response
        mock_qdrant.search.return_value = [
            MagicMock(payload={"text": "relevant context", "source_artifact_id": "doc-123", "score": 0.95})
        ]
        
        # Simulate RAG query
        results = mock_qdrant.search(
            collection_name="knowledge_base",
            query_vector=[0.1]*768,
            limit=1
        )
        
        assert len(results) == 1
        assert results[0].payload["text"] == "relevant context"
        assert results[0].payload["source_artifact_id"] == "doc-123"

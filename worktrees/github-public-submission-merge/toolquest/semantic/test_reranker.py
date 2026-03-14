import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from toolquest.semantic.reranker import VectorReranker
from toolquest.semantic.schemas import AttractorRerankRequest, SearchResult


class TestVectorReranker(unittest.TestCase):
    
    @patch('toolquest.semantic.reranker.SentenceTransformer')
    @patch('toolquest.semantic.reranker.QdrantClient')
    def setUp(self, mock_qdrant, mock_transformer):
        self.mock_qdrant_client = mock_qdrant.return_value
        self.mock_model = mock_transformer.return_value
        self.reranker = VectorReranker()
        
    def test_generate_context_vector(self):
        # Mock embeddings for "drift" and "speed"
        # Let's say vector dim is 2 for simplicity
        v1 = np.array([1.0, 0.0])
        v2 = np.array([0.0, 1.0])
        self.mock_model.encode.return_value = np.array([v1, v2])
        
        centroid = self.reranker.generate_context_vector(["drift", "speed"])
        
        # Expected centroid is [0.5, 0.5], normalized -> [0.707, 0.707]
        expected = np.array([0.5, 0.5])
        expected = expected / np.linalg.norm(expected)
        
        np.testing.assert_array_almost_equal(centroid, expected.tolist())
        
    def test_rerank_tools(self):
        # Setup request
        request = AttractorRerankRequest(
            attractor_name="Supra Drift",
            vector_queries=["drift", "slide"],
            limit=5
        )
        
        # Mock centroid generation (bypassing the logic tested above)
        self.reranker.generate_context_vector = MagicMock(return_value=[0.1, 0.2])
        
        # Mock Qdrant search result
        mock_hit = MagicMock()
        mock_hit.id = "tool_123"
        mock_hit.score = 0.95
        mock_hit.payload = {
            "tool_name": "DriftCalc",
            "description": "Calculates slide angle",
            "category": ["physics"],
            "popularity_score": 0.8,
            "difficulty_tier": 2
        }
        self.mock_qdrant_client.search.return_value = [mock_hit]
        
        results = self.reranker.rerank_tools(request)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].tool.tool_name, "DriftCalc")
        self.assertEqual(results[0].similarity_score, 0.95)
        self.mock_qdrant_client.search.assert_called_once()

if __name__ == '__main__':
    unittest.main()

"""
Vector Reranker module.
Implements the logic to rerank vectors based on Feature Attractors.
"""
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

from toolquest.semantic.schemas import AttractorRerankRequest, SearchResult, ToolEmbedding


class VectorReranker:
    """
    Reranks tool vectors based on a high-level Feature Attractor.
    Calculates a centroid from multiple query vectors and sorts results.
    """
    
    def __init__(
        self,
        model_id: str = "sentence-transformers/all-mpnet-base-v2",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        collection_name: str = "toolquest_tools"
    ):
        self.model = SentenceTransformer(model_id)
        self.qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.collection_name = collection_name

    def generate_context_vector(self, queries: List[str]) -> List[float]:
        """
        Generates a single context vector by averaging the embeddings of multiple queries.
        """
        embeddings = self.model.encode(queries)
        # Calculate mean vector (centroid)
        centroid = np.mean(embeddings, axis=0)
        # Normalize to unit length for cosine similarity
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm
        return centroid.tolist()

    def rerank_tools(self, request: AttractorRerankRequest) -> List[SearchResult]:
        """
        Reranks tools based on the attractor's vector context.
        """
        # 1. Compute context vector from queries
        context_vector = self.generate_context_vector(request.vector_queries)
        
        # 2. Query Qdrant with the centroid
        search_results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=context_vector,
            limit=request.limit
        )
        
        # 3. Format results
        results = []
        for rank, hit in enumerate(search_results, start=1):
            tool = ToolEmbedding(
                tool_id=hit.id,
                tool_name=hit.payload["tool_name"],
                description=hit.payload["description"],
                category=hit.payload.get("category", []),
                usage_examples=[], # Omit for brevity in list view
                error_patterns=[],
                embedding_vector=[], # Omit
                popularity_score=hit.payload.get("popularity_score", 0.5),
                difficulty_tier=hit.payload.get("difficulty_tier", 1)
            )
            
            results.append(SearchResult(
                tool=tool,
                similarity_score=hit.score,
                rank=rank
            ))
            
        return results

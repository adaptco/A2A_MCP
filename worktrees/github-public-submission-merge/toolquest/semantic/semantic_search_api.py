"""
Semantic search API for ToolQuest.
Provides endpoints for tool discovery and similarity search.
"""
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from schemas import SearchQuery, SearchResult, ToolEmbedding, SemanticChallenge, ChallengeRequest, AttractorRerankRequest
from challenge_generator import ChallengeGenerator
from reranker import VectorReranker

app = FastAPI(
    title="ToolQuest Semantic Search API",
    description="Semantic tool discovery for ToolQuest Pro",
    version="0.1.0"
)

# CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
qdrant = QdrantClient(host="localhost", port=6333)
COLLECTION_NAME = "toolquest_tools"
challenge_gen = ChallengeGenerator(qdrant, COLLECTION_NAME)
reranker = VectorReranker(qdrant_host="localhost", qdrant_port=6333, collection_name=COLLECTION_NAME)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": "all-mpnet-base-v2",
        "collection": COLLECTION_NAME
    }

# ... (omitted existing endpoints for brevity) ...

@app.post("/api/semantic/rerank", response_model=List[SearchResult])
async def rerank_tools(request: AttractorRerankRequest):
    """
    Rerank tools based on a high-level Feature Attractor.
    Takes a list of weighted keywords, computes a centroid, and finds nearest tools.
    """
    try:
        results = reranker.rerank_tools(request)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/semantic/search", response_model=List[SearchResult])
async def semantic_search(query: SearchQuery):
    """
    Perform semantic search for tools.
    
    Args:
        query: Search query with filters
    
    Returns:
        List of ranked search results
    """
    # Generate query embedding
    query_vector = model.encode(query.query_text).tolist()
    
    # Build Qdrant filter
    search_filter = None
    if query.category_filter or query.difficulty_filter:
        conditions = []
        
        if query.category_filter:
            conditions.append({
                "key": "category",
                "match": {"any": query.category_filter}
            })
        
        if query.difficulty_filter:
            conditions.append({
                "key": "difficulty_tier",
                "match": {"any": query.difficulty_filter}
            })
        
        search_filter = {"must": conditions} if conditions else None
    
    # Search Qdrant
    try:
        search_results = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=query.limit,
            query_filter=search_filter
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    
    # Format results
    results = []
    for rank, hit in enumerate(search_results, start=1):
        tool = ToolEmbedding(
            tool_id=hit.id,
            tool_name=hit.payload["tool_name"],
            description=hit.payload["description"],
            category=hit.payload.get("category", []),
            usage_examples=[],  # Not stored in payload for size
            error_patterns=[],
            embedding_vector=[],  # Don't return full vector
            popularity_score=hit.payload.get("popularity_score", 0.5),
            difficulty_tier=hit.payload.get("difficulty_tier", 1)
        )
        
        results.append(SearchResult(
            tool=tool,
            similarity_score=hit.score,
            rank=rank
        ))
    
    return results


@app.get("/api/tools/{tool_id}", response_model=ToolEmbedding)
async def get_tool(tool_id: str):
    """Retrieve a specific tool by ID."""
    try:
        result = qdrant.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[tool_id]
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Tool not found")
        
        point = result[0]
        return ToolEmbedding(
            tool_id=point.id,
            tool_name=point.payload["tool_name"],
            description=point.payload["description"],
            category=point.payload.get("category", []),
            usage_examples=[],
            error_patterns=[],
            embedding_vector=[],
            popularity_score=point.payload.get("popularity_score", 0.5),
            difficulty_tier=point.payload.get("difficulty_tier", 1)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tools/{tool_id}/similar", response_model=List[SearchResult])
async def find_similar_tools(
    tool_id: str,
    limit: int = 5
):
    """Find tools similar to a given tool."""
    try:
        # Get the tool's vector
        result = qdrant.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[tool_id],
            with_vectors=True
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Tool not found")
        
        tool_vector = result[0].vector
        
        # Search for similar tools
        search_results = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=tool_vector,
            limit=limit + 1  # +1 to exclude self
        )
        
        # Filter out the query tool itself
        search_results = [r for r in search_results if r.id != tool_id][:limit]
        
        # Format results
        results = []
        for rank, hit in enumerate(search_results, start=1):
            tool = ToolEmbedding(
                tool_id=hit.id,
                tool_name=hit.payload["tool_name"],
                description=hit.payload["description"],
                category=hit.payload.get("category", []),
                usage_examples=[],
                error_patterns=[],
                embedding_vector=[],
                popularity_score=hit.payload.get("popularity_score", 0.5),
                difficulty_tier=hit.payload.get("difficulty_tier", 1)
            )
            
            results.append(SearchResult(
                tool=tool,
                similarity_score=hit.score,
                rank=rank
            ))
        
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/challenges/generate", response_model=Optional[SemanticChallenge])
async def generate_challenge(request: ChallengeRequest):
    """
    Generate a semantic challenge based on a target tool.
    Finds similar tools and constructs an exploratory task.
    """
    try:
        challenge = challenge_gen.generate_challenge(
            target_tool_id=request.target_tool_id,
            user_history=request.user_history
        )
        
        if not challenge:
            raise HTTPException(status_code=404, detail="Could not generate challenge (no neighbors found)")
            
        return challenge
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/challenges/generate", response_model=SemanticChallenge)
async def generate_challenge_endpoint(tool_id: str):
    """
    Generate an AI challenge for a specific tool.
    """
    try:
        challenge = challenge_gen.generate_challenge(tool_id)
        if not challenge:
            raise HTTPException(status_code=404, detail="Tool not found or context insufficient")
        return challenge
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)


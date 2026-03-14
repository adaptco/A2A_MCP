"""
Tool metadata schema for semantic search.
Defines the structure for tools, work orders, and challenges.
"""
from typing import List, Literal
from pydantic import BaseModel, Field


class ToolEmbedding(BaseModel):
    """Embedded tool metadata for semantic search."""
    tool_id: str = Field(..., description="Unique tool identifier")
    tool_name: str = Field(..., description="Tool name (e.g., 'grep', 'find')")
    description: str = Field(..., description="What the tool does")
    category: List[str] = Field(default_factory=list, description="Tool categories")
    usage_examples: List[str] = Field(default_factory=list, description="Example commands")
    error_patterns: List[str] = Field(default_factory=list, description="Common error messages")
    embedding_vector: List[float] = Field(..., description="768-dim embedding")
    popularity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    difficulty_tier: Literal[1, 2, 3, 4, 5] = Field(default=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "tool_id": "grep_001",
                "tool_name": "grep",
                "description": "Search for patterns in files using regular expressions",
                "category": ["text-processing", "search"],
                "usage_examples": [
                    "grep 'pattern' file.txt",
                    "grep -r 'pattern' directory/"
                ],
                "error_patterns": [
                    "No such file or directory",
                    "Invalid regular expression"
                ],
                "embedding_vector": [0.1] * 768,
                "popularity_score": 0.95,
                "difficulty_tier": 2
            }
        }


class WorkOrderEmbedding(BaseModel):
    """Embedded work order for challenge generation."""
    order_id: str
    task_description: str
    required_tools: List[str] = Field(default_factory=list)
    common_errors: List[str] = Field(default_factory=list)
    embedding_vector: List[float]
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    avg_time_seconds: int = Field(default=0, ge=0)
    difficulty_tier: Literal[1, 2, 3, 4, 5] = Field(default=1)


class SemanticChallenge(BaseModel):
    """AI-generated challenge based on semantic neighbors."""
    challenge_id: str
    generated_task: str
    semantic_neighbors: List[str] = Field(
        default_factory=list,
        description="Tool IDs of similar tools"
    )
    required_tools: List[str] = Field(default_factory=list)
    difficulty_score: float = Field(ge=0.0, le=1.0)
    xp_reward: int = Field(ge=0)
    time_limit_seconds: int = Field(ge=0)
    novelty_factor: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How different this is from known patterns"
    )


class SearchQuery(BaseModel):
    """Semantic search query."""
    query_text: str = Field(..., description="Natural language query")
    category_filter: List[str] = Field(
        default_factory=list,
        description="Filter by categories"
    )
    difficulty_filter: List[int] = Field(
        default_factory=list,
        description="Filter by difficulty tiers"
    )
    limit: int = Field(default=10, ge=1, le=100)


class SearchResult(BaseModel):
    """Semantic search result."""
    tool: ToolEmbedding
    similarity_score: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=1)


class ChallengeRequest(BaseModel):
    """Request payload for generating a challenge."""
    target_tool_id: str = Field(..., description="ID of the tool to center the challenge around")
    user_history: List[str] = Field(default_factory=list, description="List of previously used tool IDs")


class AttractorRerankRequest(BaseModel):
    """Request to rerank tools based on a Feature Attractor."""
    attractor_name: str = Field(..., description="Name of the feature attractor")
    vector_queries: List[str] = Field(..., min_items=1, description="Keywords to form the context vector")
    limit: int = Field(default=10, ge=1, le=100)



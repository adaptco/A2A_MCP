"""
Embedding pipeline for tool metadata.
Generates semantic embeddings for tools, work orders, and error patterns.
"""
import os
from typing import List, Dict
import torch
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from schemas import ToolEmbedding, WorkOrderEmbedding


class EmbeddingPipeline:
    """Pipeline for generating and storing tool embeddings."""
    
    def __init__(
        self,
        model_id: str = "sentence-transformers/all-mpnet-base-v2",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333
    ):
        self.model = SentenceTransformer(model_id)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        self.qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.collection_name = "toolquest_tools"
        
        # Ensure collection exists
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Create Qdrant collection if it doesn't exist."""
        try:
            self.qdrant.get_collection(self.collection_name)
        except Exception:
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embedding = self.model.encode(text, convert_to_tensor=True)
        return embedding.cpu().tolist()
    
    def embed_tool(self, tool_data: Dict) -> ToolEmbedding:
        """
        Generate embedding for a tool.
        Combines name, description, and usage examples.
        """
        # Combine text fields for richer embedding
        combined_text = f"{tool_data['tool_name']}: {tool_data['description']}"
        
        if tool_data.get('usage_examples'):
            examples = " ".join(tool_data['usage_examples'][:3])
            combined_text += f" Examples: {examples}"
        
        # Generate embedding
        embedding_vector = self.embed_text(combined_text)
        
        return ToolEmbedding(
            tool_id=tool_data['tool_id'],
            tool_name=tool_data['tool_name'],
            description=tool_data['description'],
            category=tool_data.get('category', []),
            usage_examples=tool_data.get('usage_examples', []),
            error_patterns=tool_data.get('error_patterns', []),
            embedding_vector=embedding_vector,
            popularity_score=tool_data.get('popularity_score', 0.5),
            difficulty_tier=tool_data.get('difficulty_tier', 1)
        )
    
    def index_tool(self, tool: ToolEmbedding):
        """Store tool embedding in Qdrant."""
        point = PointStruct(
            id=tool.tool_id,
            vector=tool.embedding_vector,
            payload={
                "tool_name": tool.tool_name,
                "description": tool.description,
                "category": tool.category,
                "popularity_score": tool.popularity_score,
                "difficulty_tier": tool.difficulty_tier
            }
        )
        
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
    
    def index_tools_batch(self, tools: List[ToolEmbedding], batch_size: int = 32):
        """Index multiple tools in batches."""
        for i in range(0, len(tools), batch_size):
            batch = tools[i:i + batch_size]
            points = [
                PointStruct(
                    id=tool.tool_id,
                    vector=tool.embedding_vector,
                    payload={
                        "tool_name": tool.tool_name,
                        "description": tool.description,
                        "category": tool.category,
                        "popularity_score": tool.popularity_score,
                        "difficulty_tier": tool.difficulty_tier
                    }
                )
                for tool in batch
            ]
            
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=points
            )
    
    def embed_work_order(self, order_data: Dict) -> WorkOrderEmbedding:
        """Generate embedding for a work order."""
        combined_text = order_data['task_description']
        
        if order_data.get('required_tools'):
            tools = ", ".join(order_data['required_tools'])
            combined_text += f" Tools: {tools}"
        
        embedding_vector = self.embed_text(combined_text)
        
        return WorkOrderEmbedding(
            order_id=order_data['order_id'],
            task_description=order_data['task_description'],
            required_tools=order_data.get('required_tools', []),
            common_errors=order_data.get('common_errors', []),
            embedding_vector=embedding_vector,
            completion_rate=order_data.get('completion_rate', 0.0),
            avg_time_seconds=order_data.get('avg_time_seconds', 0),
            difficulty_tier=order_data.get('difficulty_tier', 1)
        )


def load_sample_tools() -> List[Dict]:
    """Load sample tool metadata for testing."""
    return [
        {
            "tool_id": "grep_001",
            "tool_name": "grep",
            "description": "Search for patterns in files using regular expressions",
            "category": ["text-processing", "search"],
            "usage_examples": [
                "grep 'pattern' file.txt",
                "grep -r 'pattern' directory/",
                "grep -i 'case-insensitive' file.txt"
            ],
            "error_patterns": ["No such file or directory", "Invalid regular expression"],
            "popularity_score": 0.95,
            "difficulty_tier": 2
        },
        {
            "tool_id": "find_001",
            "tool_name": "find",
            "description": "Search for files and directories in a directory hierarchy",
            "category": ["file-management", "search"],
            "usage_examples": [
                "find . -name '*.txt'",
                "find /path -type f -size +10M",
                "find . -mtime -7"
            ],
            "error_patterns": ["Permission denied", "No such file or directory"],
            "popularity_score": 0.90,
            "difficulty_tier": 3
        },
        {
            "tool_id": "awk_001",
            "tool_name": "awk",
            "description": "Pattern scanning and text processing language",
            "category": ["text-processing", "scripting"],
            "usage_examples": [
                "awk '{print $1}' file.txt",
                "awk -F: '{print $1, $3}' /etc/passwd",
                "awk '/pattern/ {print $0}' file.txt"
            ],
            "error_patterns": ["Syntax error", "Division by zero"],
            "popularity_score": 0.75,
            "difficulty_tier": 4
        },
        {
            "tool_id": "sed_001",
            "tool_name": "sed",
            "description": "Stream editor for filtering and transforming text",
            "category": ["text-processing", "editing"],
            "usage_examples": [
                "sed 's/old/new/g' file.txt",
                "sed -i 's/pattern/replacement/' file.txt",
                "sed -n '1,10p' file.txt"
            ],
            "error_patterns": ["Invalid command", "Unterminated address regex"],
            "popularity_score": 0.80,
            "difficulty_tier": 3
        },
        {
            "tool_id": "jq_001",
            "tool_name": "jq",
            "description": "Command-line JSON processor",
            "category": ["json", "text-processing"],
            "usage_examples": [
                "jq '.' file.json",
                "jq '.key' file.json",
                "jq '.[] | select(.name == \"value\")' file.json"
            ],
            "error_patterns": ["Parse error", "Cannot index"],
            "popularity_score": 0.85,
            "difficulty_tier": 3
        }
    ]


if __name__ == "__main__":
    # Initialize pipeline
    pipeline = EmbeddingPipeline()
    
    # Load and embed sample tools
    sample_tools = load_sample_tools()
    embedded_tools = [pipeline.embed_tool(tool) for tool in sample_tools]
    
    # Index in Qdrant
    pipeline.index_tools_batch(embedded_tools)
    
    print(f"Indexed {len(embedded_tools)} tools successfully!")
    print(f"Collection: {pipeline.collection_name}")
    print(f"Embedding dimension: {pipeline.embedding_dim}")

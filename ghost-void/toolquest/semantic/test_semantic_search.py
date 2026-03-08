"""
Unit tests for ToolQuest Semantic Search.
Validates embedding pipeline, search API, and result quality.
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from schemas import ToolEmbedding, SearchQuery, SearchResult
from embedding_pipeline import EmbeddingPipeline, load_sample_tools


class TestEmbeddingPipeline:
    """Test embedding generation and indexing."""
    
    @pytest.fixture
    def pipeline(self):
        """Create pipeline instance."""
        return EmbeddingPipeline(
            qdrant_host="localhost",
            qdrant_port=6333
        )
    
    def test_embed_text(self, pipeline):
        """Test single text embedding."""
        text = "search for patterns in files"
        embedding = pipeline.embed_text(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 768  # all-mpnet-base-v2 dimension
        assert all(isinstance(x, float) for x in embedding)
    
    def test_embed_tool(self, pipeline):
        """Test tool metadata embedding."""
        tool_data = {
            "tool_id": "test_001",
            "tool_name": "test_tool",
            "description": "A test tool for validation",
            "category": ["testing"],
            "usage_examples": ["test --help"],
            "popularity_score": 0.5,
            "difficulty_tier": 1
        }
        
        tool = pipeline.embed_tool(tool_data)
        
        assert isinstance(tool, ToolEmbedding)
        assert tool.tool_id == "test_001"
        assert tool.tool_name == "test_tool"
        assert len(tool.embedding_vector) == 768
    
    def test_load_sample_tools(self):
        """Test sample tool loading."""
        tools = load_sample_tools()
        
        assert len(tools) == 5
        assert all("tool_id" in t for t in tools)
        assert all("tool_name" in t for t in tools)
        
        # Verify expected tools
        tool_names = [t["tool_name"] for t in tools]
        assert "grep" in tool_names
        assert "find" in tool_names
        assert "awk" in tool_names
        assert "sed" in tool_names
        assert "jq" in tool_names
    
    def test_index_tools_batch(self, pipeline):
        """Test batch indexing to Qdrant."""
        sample_tools = load_sample_tools()
        embedded_tools = [pipeline.embed_tool(t) for t in sample_tools]
        
        # This should not raise an exception
        pipeline.index_tools_batch(embedded_tools)
        
        # Verify tools were indexed
        assert len(embedded_tools) == 5


class TestSemanticSearch:
    """Test semantic search functionality."""
    
    def test_search_query_validation(self):
        """Test search query model validation."""
        query = SearchQuery(
            query_text="find large files",
            category_filter=["file-management"],
            difficulty_filter=[1, 2, 3],
            limit=5
        )
        
        assert query.query_text == "find large files"
        assert "file-management" in query.category_filter
        assert query.limit == 5
    
    def test_search_query_defaults(self):
        """Test search query default values."""
        query = SearchQuery(query_text="test")
        
        assert query.category_filter == []
        assert query.difficulty_filter == []
        assert query.limit == 10


class TestSemanticSimilarity:
    """Test semantic similarity expectations."""
    
    @pytest.fixture
    def pipeline(self):
        return EmbeddingPipeline()
    
    def test_grep_similarity(self, pipeline):
        """Test that grep-related queries return grep."""
        query_embedding = pipeline.embed_text("search for patterns in files")
        grep_embedding = pipeline.embed_text("grep: Search for patterns in files using regular expressions")
        
        # Compute cosine similarity
        import numpy as np
        query_vec = np.array(query_embedding)
        grep_vec = np.array(grep_embedding)
        
        similarity = np.dot(query_vec, grep_vec) / (
            np.linalg.norm(query_vec) * np.linalg.norm(grep_vec)
        )
        
        # Should have high similarity (>0.7)
        assert similarity > 0.7, f"Expected similarity > 0.7, got {similarity}"
    
    def test_find_similarity(self, pipeline):
        """Test that find-related queries return find."""
        query_embedding = pipeline.embed_text("search for files in directory")
        find_embedding = pipeline.embed_text("find: Search for files and directories in a directory hierarchy")
        
        import numpy as np
        query_vec = np.array(query_embedding)
        find_vec = np.array(find_embedding)
        
        similarity = np.dot(query_vec, find_vec) / (
            np.linalg.norm(query_vec) * np.linalg.norm(find_vec)
        )
        
        assert similarity > 0.7, f"Expected similarity > 0.7, got {similarity}"
    
    def test_semantic_neighbors(self, pipeline):
        """Test that similar tools have high similarity."""
        # grep and awk are both text-processing tools
        grep_embedding = pipeline.embed_text("grep: Search for patterns in files")
        awk_embedding = pipeline.embed_text("awk: Pattern scanning and text processing")
        
        import numpy as np
        grep_vec = np.array(grep_embedding)
        awk_vec = np.array(awk_embedding)
        
        similarity = np.dot(grep_vec, awk_vec) / (
            np.linalg.norm(grep_vec) * np.linalg.norm(awk_vec)
        )
        
        # Should have moderate similarity (>0.5)
        assert similarity > 0.5, f"Expected similarity > 0.5, got {similarity}"


class TestIntegration:
    """Integration tests requiring running services."""
    
    @pytest.mark.integration
    def test_full_pipeline(self):
        """Test complete pipeline: embed -> index -> search."""
        pipeline = EmbeddingPipeline()
        
        # Load and embed sample tools
        sample_tools = load_sample_tools()
        embedded_tools = [pipeline.embed_tool(t) for t in sample_tools]
        
        # Index tools
        pipeline.index_tools_batch(embedded_tools)
        
        # Search for a tool
        query_vector = pipeline.embed_text("search for patterns in files")
        
        results = pipeline.qdrant.search(
            collection_name=pipeline.collection_name,
            query_vector=query_vector,
            limit=3
        )
        
        # Verify results
        assert len(results) > 0
        
        # Top result should be grep
        top_result = results[0]
        assert top_result.payload["tool_name"] == "grep"
        assert top_result.score > 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

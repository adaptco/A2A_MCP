"""
Standalone unit tests that don't require Qdrant service.
Tests embedding generation, schema validation, and semantic similarity.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from schemas import ToolEmbedding, SearchQuery, WorkOrderEmbedding, SemanticChallenge
from embedding_pipeline import load_sample_tools


def test_schema_validation():
    """Test Pydantic schema validation."""
    print("Testing schema validation...")
    
    # Test ToolEmbedding
    tool = ToolEmbedding(
        tool_id="test_001",
        tool_name="test",
        description="A test tool",
        embedding_vector=[0.1] * 768,
        popularity_score=0.8,
        difficulty_tier=2
    )
    assert tool.tool_id == "test_001"
    assert len(tool.embedding_vector) == 768
    print("✓ ToolEmbedding validation passed")
    
    # Test SearchQuery
    query = SearchQuery(
        query_text="find files",
        limit=5
    )
    assert query.limit == 5
    assert query.category_filter == []
    print("✓ SearchQuery validation passed")
    
    # Test WorkOrderEmbedding
    order = WorkOrderEmbedding(
        order_id="order_001",
        task_description="Search for large files",
        embedding_vector=[0.2] * 768,
        completion_rate=0.75,
        avg_time_seconds=120
    )
    assert order.completion_rate == 0.75
    print("✓ WorkOrderEmbedding validation passed")
    
    # Test SemanticChallenge
    challenge = SemanticChallenge(
        challenge_id="challenge_001",
        generated_task="Find all files larger than 100MB",
        difficulty_score=0.6,
        xp_reward=100,
        time_limit_seconds=300,
        novelty_factor=0.7
    )
    assert challenge.xp_reward == 100
    print("✓ SemanticChallenge validation passed")


def test_sample_tools_loading():
    """Test sample tool data loading."""
    print("\nTesting sample tools loading...")
    
    tools = load_sample_tools()
    
    assert len(tools) == 5, f"Expected 5 tools, got {len(tools)}"
    print(f"✓ Loaded {len(tools)} sample tools")
    
    # Verify expected tools
    tool_names = {t["tool_name"] for t in tools}
    expected = {"grep", "find", "awk", "sed", "jq"}
    assert tool_names == expected, f"Expected {expected}, got {tool_names}"
    print(f"✓ Tool names: {', '.join(sorted(tool_names))}")
    
    # Verify structure
    for tool in tools:
        assert "tool_id" in tool
        assert "tool_name" in tool
        assert "description" in tool
        assert "category" in tool
        assert "usage_examples" in tool
        assert "difficulty_tier" in tool
    print("✓ All tools have required fields")


def test_embedding_generation():
    """Test embedding generation without Qdrant."""
    print("\nTesting embedding generation...")
    
    try:
        from embedding_pipeline import EmbeddingPipeline
        
        # Create pipeline (will fail to connect to Qdrant, but that's OK for this test)
        try:
            pipeline = EmbeddingPipeline()
        except Exception as e:
            print(f"⚠ Qdrant connection failed (expected): {e}")
            # Create pipeline without Qdrant connection check
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
            
            # Test embedding generation
            text = "search for patterns in files"
            embedding = model.encode(text).tolist()
            
            assert isinstance(embedding, list)
            assert len(embedding) == 768
            assert all(isinstance(x, float) for x in embedding)
            print(f"✓ Generated embedding: {len(embedding)} dimensions")
            
            # Test tool embedding
            tool_data = load_sample_tools()[0]  # grep
            combined_text = f"{tool_data['tool_name']}: {tool_data['description']}"
            tool_embedding = model.encode(combined_text).tolist()
            
            assert len(tool_embedding) == 768
            print(f"✓ Tool embedding for '{tool_data['tool_name']}': {len(tool_embedding)} dimensions")
            
            return True
    except ImportError as e:
        print(f"⚠ Skipping embedding test (dependencies not installed): {e}")
        return False


def test_semantic_similarity():
    """Test semantic similarity calculations."""
    print("\nTesting semantic similarity...")
    
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        
        model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
        
        # Test grep similarity
        query = "search for patterns in files"
        grep_desc = "grep: Search for patterns in files using regular expressions"
        
        query_emb = model.encode(query)
        grep_emb = model.encode(grep_desc)
        
        similarity = np.dot(query_emb, grep_emb) / (
            np.linalg.norm(query_emb) * np.linalg.norm(grep_emb)
        )
        
        print(f"✓ Query '{query}' vs grep: {similarity:.4f}")
        assert similarity > 0.6, f"Expected similarity > 0.6, got {similarity}"
        
        # Test find similarity
        find_query = "search for files in directory"
        find_desc = "find: Search for files and directories in a directory hierarchy"
        
        find_query_emb = model.encode(find_query)
        find_desc_emb = model.encode(find_desc)
        
        find_similarity = np.dot(find_query_emb, find_desc_emb) / (
            np.linalg.norm(find_query_emb) * np.linalg.norm(find_desc_emb)
        )
        
        print(f"✓ Query '{find_query}' vs find: {find_similarity:.4f}")
        assert find_similarity > 0.6, f"Expected similarity > 0.6, got {find_similarity}"
        
        # Test semantic neighbors (grep vs awk)
        awk_desc = "awk: Pattern scanning and text processing"
        awk_emb = model.encode(awk_desc)
        
        grep_awk_similarity = np.dot(grep_emb, awk_emb) / (
            np.linalg.norm(grep_emb) * np.linalg.norm(awk_emb)
        )
        
        print(f"✓ grep vs awk (semantic neighbors): {grep_awk_similarity:.4f}")
        assert grep_awk_similarity > 0.4, f"Expected similarity > 0.4, got {grep_awk_similarity}"
        
        return True
    except ImportError as e:
        print(f"⚠ Skipping similarity test (dependencies not installed): {e}")
        return False


def run_all_tests():
    """Run all standalone tests."""
    print("=" * 60)
    print("ToolQuest Semantic Search - Standalone Unit Tests")
    print("=" * 60)
    
    results = {
        "Schema Validation": False,
        "Sample Tools Loading": False,
        "Embedding Generation": False,
        "Semantic Similarity": False
    }
    
    try:
        test_schema_validation()
        results["Schema Validation"] = True
    except Exception as e:
        print(f"✗ Schema validation failed: {e}")
    
    try:
        test_sample_tools_loading()
        results["Sample Tools Loading"] = True
    except Exception as e:
        print(f"✗ Sample tools loading failed: {e}")
    
    try:
        if test_embedding_generation():
            results["Embedding Generation"] = True
    except Exception as e:
        print(f"✗ Embedding generation failed: {e}")
    
    try:
        if test_semantic_similarity():
            results["Semantic Similarity"] = True
    except Exception as e:
        print(f"✗ Semantic similarity failed: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return all(results.values())


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

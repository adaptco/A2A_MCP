"""Tests for the VectorGate semantic retrieval mechanism."""

import pytest
from datetime import datetime, timezone
from orchestrator.vector_gate import VectorGate, VectorGateDecision, VectorMatch
from schemas.world_model import WorldModel, VectorToken

@pytest.fixture
def empty_world_model():
    return WorldModel(model_id="test-world-model")

@pytest.fixture
def vector_gate():
    return VectorGate(min_similarity=0.5, top_k=2)

def test_initialization():
    """Test that VectorGate initializes with correct defaults and custom values."""
    gate = VectorGate()
    assert gate.min_similarity == 0.2
    assert gate.top_k == 3

    custom_gate = VectorGate(min_similarity=0.8, top_k=5)
    assert custom_gate.min_similarity == 0.8
    assert custom_gate.top_k == 5

def test_evaluate_empty_world_model(vector_gate, empty_world_model):
    """Test evaluation with an empty world model."""
    decision = vector_gate.evaluate(
        node="test_node",
        query="test query",
        world_model=empty_world_model
    )
    assert decision.is_open is False
    assert decision.node == "test_node"
    assert len(decision.matches) == 0

def test_evaluate_exact_match(vector_gate, empty_world_model):
    """Test evaluation with an exact match token."""
    query = "test query"
    # Create a token with the exact vector of the query
    query_vector = vector_gate._deterministic_embedding(query, dimensions=16)

    token = VectorToken(
        token_id="token-1",
        source_artifact_id="artifact-1",
        vector=query_vector,
        text="This is a test token matching the query.",
        timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc)
    )
    empty_world_model.add_token(token)

    decision = vector_gate.evaluate(
        node="test_node",
        query=query,
        world_model=empty_world_model
    )

    assert decision.is_open is True
    assert len(decision.matches) == 1
    match = decision.matches[0]
    assert match.token_id == "token-1"
    assert match.score == pytest.approx(1.0)

def test_evaluate_filtering(vector_gate, empty_world_model):
    """Test that tokens below the similarity threshold result in a closed gate."""
    query = "test query"
    query_vector = vector_gate._deterministic_embedding(query, dimensions=16)

    # Create a vector that is orthogonal or opposite to the query to ensure low score
    # Simple way: negate the vector (score -1.0)
    low_score_vector = [-x for x in query_vector]

    token = VectorToken(
        token_id="token-low",
        source_artifact_id="artifact-low",
        vector=low_score_vector,
        text="Low similarity token.",
        timestamp=datetime.now(timezone.utc)
    )
    empty_world_model.add_token(token)

    decision = vector_gate.evaluate(
        node="test_node",
        query=query,
        world_model=empty_world_model
    )

    # The gate should be closed
    assert decision.is_open is False
    # Matches might still be returned (VectorGate returns top_k regardless of score)
    # But the top score should be low
    assert decision.top_score < vector_gate.min_similarity

def test_evaluate_top_k(vector_gate, empty_world_model):
    """Test that only top k matches are returned."""
    query = "test query"
    query_vector = vector_gate._deterministic_embedding(query, dimensions=16)

    # Add 3 identical tokens (all perfect matches)
    for i in range(3):
        token = VectorToken(
            token_id=f"token-{i}",
            source_artifact_id=f"artifact-{i}",
            vector=query_vector,
            text=f"Match {i}",
            timestamp=datetime.now(timezone.utc)
        )
        empty_world_model.add_token(token)

    # Gate is configured with top_k=2
    decision = vector_gate.evaluate(
        node="test_node",
        query=query,
        world_model=empty_world_model
    )

    assert len(decision.matches) == 2
    assert decision.is_open is True

def test_dimension_mismatch_robustness(vector_gate, empty_world_model):
    """Test that tokens with incorrect vector dimensions are skipped gracefully."""
    query = "test query"

    # 1. Add a valid token to establish the expected dimension (16)
    valid_vector = vector_gate._deterministic_embedding(query, dimensions=16)
    valid_token = VectorToken(
        token_id="token-valid",
        source_artifact_id="artifact-valid",
        vector=valid_vector,
        text="Valid dimension token.",
        timestamp=datetime.now(timezone.utc)
    )
    empty_world_model.add_token(valid_token)

    # 2. Add an invalid token with wrong dimensions
    wrong_dim_vector = [0.1] * 10  # 10 dimensions instead of 16
    invalid_token = VectorToken(
        token_id="token-wrong-dim",
        source_artifact_id="artifact-wrong",
        vector=wrong_dim_vector,
        text="Wrong dimension token.",
        timestamp=datetime.now(timezone.utc)
    )
    empty_world_model.add_token(invalid_token)

    decision = vector_gate.evaluate(
        node="test_node",
        query=query,
        world_model=empty_world_model
    )

    # The valid token should be matched
    assert len(decision.matches) == 1
    assert decision.matches[0].token_id == "token-valid"

def test_format_prompt_context(vector_gate, empty_world_model):
    """Test the string formatting of the gate decision."""
    query = "test query"
    query_vector = vector_gate._deterministic_embedding(query, dimensions=16)

    token = VectorToken(
        token_id="token-1",
        source_artifact_id="artifact-1",
        vector=query_vector,
        text="Short text snippet.",
        timestamp=datetime.now(timezone.utc)
    )
    empty_world_model.add_token(token)

    decision = vector_gate.evaluate(
        node="test_node",
        query=query,
        world_model=empty_world_model
    )

    formatted = vector_gate.format_prompt_context(decision)

    assert "[VECTOR_GATE node=test_node state=OPEN" in formatted
    assert "token=token-1" in formatted
    assert "text=Short text snippet." in formatted

def test_format_prompt_context_truncation(vector_gate, empty_world_model):
    """Test that long text snippets are truncated in the prompt context."""
    query = "test query"
    query_vector = vector_gate._deterministic_embedding(query, dimensions=16)

    long_text = "A" * 300
    token = VectorToken(
        token_id="token-long",
        source_artifact_id="artifact-long",
        vector=query_vector,
        text=long_text,
        timestamp=datetime.now(timezone.utc)
    )
    empty_world_model.add_token(token)

    decision = vector_gate.evaluate(
        node="test_node",
        query=query,
        world_model=empty_world_model
    )

    formatted = vector_gate.format_prompt_context(decision)

    # Check for truncation indicator "..."
    assert "..." in formatted
    # Ensure the full text is not present
    assert long_text not in formatted

def test_cosine_similarity_zero_vector(vector_gate):
    """Test cosine similarity with zero vectors to ensure no division by zero."""
    # Both zero
    assert vector_gate._cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0
    # One zero
    assert vector_gate._cosine_similarity([1.0, 1.0], [0.0, 0.0]) == 0.0
    assert vector_gate._cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0

def test_evaluate_empty_query(vector_gate, empty_world_model):
    """Test evaluation with an empty query string."""
    # Add a token so there is something to potentially match
    token = VectorToken(
        token_id="token-1",
        source_artifact_id="artifact-1",
        vector=vector_gate._deterministic_embedding("some text", dimensions=16),
        text="Some text",
        timestamp=datetime.now(timezone.utc)
    )
    empty_world_model.add_token(token)

    decision = vector_gate.evaluate(
        node="test_node",
        query="",
        world_model=empty_world_model
    )

    # An empty query is valid but might not match well depending on hash.
    # Just ensure it doesn't crash and returns a decision.
    assert isinstance(decision, VectorGateDecision)
    assert decision.query == ""

def test_evaluate_top_k_zero(empty_world_model):
    """Test evaluation with top_k=0."""
    gate = VectorGate(top_k=0)

    # Add a token
    token = VectorToken(
        token_id="token-1",
        source_artifact_id="artifact-1",
        vector=gate._deterministic_embedding("match me", dimensions=16),
        text="match me",
        timestamp=datetime.now(timezone.utc)
    )
    empty_world_model.add_token(token)

    decision = gate.evaluate(
        node="test_node",
        query="match me",
        world_model=empty_world_model
    )

    # Should return empty matches list
    assert len(decision.matches) == 0
    assert decision.is_open is False

def test_unicode_stability(vector_gate):
    """Test that deterministic embedding handles unicode consistently."""
    text1 = "Hello World"
    text2 = "Hello World"
    text3 = "Hëllö Wörld" # Different unicode

    vec1 = vector_gate._deterministic_embedding(text1)
    vec2 = vector_gate._deterministic_embedding(text2)
    vec3 = vector_gate._deterministic_embedding(text3)

    assert vec1 == vec2
    assert vec1 != vec3

    # Test emoji and exotic characters
    exotic = "🦄✨🔥"
    vec_exotic = vector_gate._deterministic_embedding(exotic)
    assert len(vec_exotic) == 16 # default dim
    assert all(isinstance(x, float) for x in vec_exotic)

def test_format_prompt_context_boundary(vector_gate):
    """Test context formatting boundaries."""
    match1 = VectorMatch(token_id="t1", source_artifact_id="s1", score=0.9, text="A" * 10)
    match2 = VectorMatch(token_id="t2", source_artifact_id="s2", score=0.8, text="B" * 10)

    decision = VectorGateDecision(
        node="test",
        is_open=True,
        query="q",
        threshold=0.5,
        top_score=0.9,
        matches=[match1, match2]
    )

    # Check output with ample space
    full_output = vector_gate.format_prompt_context(decision, max_chars=1000)
    lines = full_output.split("\n")
    header = lines[0]
    line1 = lines[1]

    # So max_chars is the TOTAL budget for match lines. The header is pre-added regardless of budget.
    formatted_limited = vector_gate.format_prompt_context(decision, max_chars=len(line1) + 5)
    assert "token=t1" in formatted_limited
    assert "token=t2" not in formatted_limited

def test_cosine_similarity_values(vector_gate):
    """Test cosine similarity value correctness for known vectors."""
    # Orthogonal
    assert vector_gate._cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)
    # Parallel
    assert vector_gate._cosine_similarity([1, 1], [2, 2]) == pytest.approx(1.0) # approx due to float
    # Opposite
    assert vector_gate._cosine_similarity([1, 2], [-1, -2]) == pytest.approx(-1.0)

import pytest
<<<<<<< HEAD
import torch
from a2a_mcp.mcp_core import MCPCore, MCPResult

# Constants for testing
INPUT_DIM = 128
HIDDEN_DIM = 64
N_ROLES = 16

@pytest.fixture(scope="module")
def mcp_core_model():
    """Provides a reusable instance of MCPCore for testing."""
    model = MCPCore(input_dim=INPUT_DIM, hidden_dim=HIDDEN_DIM, n_roles=N_ROLES)
    model.eval()  # Set the model to evaluation mode for consistent results
    return model

@pytest.fixture
def sample_embedding():
    """Provides a sample input tensor."""
    return torch.randn(1, INPUT_DIM)

def test_mcp_core_initialization(mcp_core_model: MCPCore):
    """Tests if the MCPCore model initializes with the correct parameters."""
    assert mcp_core_model.input_dim == INPUT_DIM
    assert mcp_core_model.hidden_dim == HIDDEN_DIM
    assert mcp_core_model.n_roles == N_ROLES
    assert isinstance(mcp_core_model.feature_extractor, torch.nn.Sequential)
    assert isinstance(mcp_core_model.arbitration_head, torch.nn.Sequential)
    assert isinstance(mcp_core_model.similarity_head, torch.nn.Linear)

def test_forward_pass_output_structure(mcp_core_model: MCPCore, sample_embedding: torch.Tensor):
    """Tests the structure and types of the MCPResult from a forward pass."""
    with torch.no_grad():
        result = mcp_core_model(sample_embedding)

    assert isinstance(result, MCPResult)
    assert isinstance(result.processed_embedding, torch.Tensor)
    assert isinstance(result.arbitration_scores, torch.Tensor)
    assert isinstance(result.protocol_features, dict)
    assert isinstance(result.execution_hash, str)

def test_forward_pass_output_shapes(mcp_core_model: MCPCore, sample_embedding: torch.Tensor):
    """Tests the output shapes from a forward pass."""
    with torch.no_grad():
        result = mcp_core_model(sample_embedding)

    assert result.processed_embedding.shape == (1, HIDDEN_DIM)
    assert result.arbitration_scores.shape == (N_ROLES,)

def test_forward_pass_input_shape_validation(mcp_core_model: MCPCore):
    """Tests that the forward pass raises a ValueError for incorrect input shapes."""
    wrong_shape_embedding = torch.randn(1, INPUT_DIM + 1)
    with pytest.raises(ValueError, match="Expected namespaced embedding shape"):
        mcp_core_model(wrong_shape_embedding)

    wrong_dims_embedding = torch.randn(2, INPUT_DIM)
    with pytest.raises(ValueError, match="Expected namespaced embedding shape"):
        mcp_core_model(wrong_dims_embedding)

def test_arbitration_scores_sum_to_one(mcp_core_model: MCPCore, sample_embedding: torch.Tensor):
    """Tests that arbitration scores are a valid probability distribution (sum to 1)."""
    with torch.no_grad():
        result = mcp_core_model(sample_embedding)
    
    assert torch.isclose(torch.sum(result.arbitration_scores), torch.tensor(1.0), atol=1e-6)

def test_processed_embedding_is_normalized(mcp_core_model: MCPCore, sample_embedding: torch.Tensor):
    """Tests that the processed_embedding is L2 normalized."""
    with torch.no_grad():
        result = mcp_core_model(sample_embedding)

    norm = torch.norm(result.processed_embedding.squeeze())
    assert torch.isclose(norm, torch.tensor(1.0), atol=1e-6)

def test_execution_hash_is_deterministic(mcp_core_model: MCPCore, sample_embedding: torch.Tensor):
    """Tests that the execution_hash is deterministic for the same input."""
    with torch.no_grad():
        result1 = mcp_core_model(sample_embedding)
        result2 = mcp_core_model(sample_embedding)

    assert result1.execution_hash == result2.execution_hash
    assert len(result1.execution_hash) == 64

def test_compute_protocol_similarity(mcp_core_model: MCPCore, sample_embedding: torch.Tensor):
    """Tests the protocol similarity computation."""
    emb1 = sample_embedding
    emb2 = torch.randn(1, INPUT_DIM)

    # Similarity with itself should be close to 1
    with torch.no_grad():
        similarity_same = mcp_core_model.compute_protocol_similarity(emb1, emb1.clone())
    assert isinstance(similarity_same, float)
    assert pytest.approx(similarity_same, 1.0)

    # Similarity with a different embedding should be between -1 and 1
    with torch.no_grad():
        similarity_different = mcp_core_model.compute_protocol_similarity(emb1, emb2)
    assert isinstance(similarity_different, float)
    assert -1.0 <= similarity_different <= 1.0
=======

torch = pytest.importorskip("torch")

from a2a_mcp.mcp_core import MCPCore, MCPResult


def test_mcp_core_forward_shapes_and_hash():
    torch.manual_seed(7)
    core = MCPCore(hidden_dim=128, n_roles=32)
    namespaced = torch.randn(1, 4096)

    result = core(namespaced)

    assert isinstance(result, MCPResult)
    assert result.processed_embedding.shape == (1, 128)
    assert result.arbitration_scores.shape == (32,)
    assert result.protocol_features["feature_norm"] > 0.0
    assert len(result.execution_hash) == 64

    norm = float(torch.norm(result.processed_embedding, dim=-1).item())
    assert abs(norm - 1.0) < 1e-5


def test_protocol_similarity_returns_cosine_range():
    torch.manual_seed(11)
    core = MCPCore()
    emb = torch.randn(1, 4096)

    sim_same = core.compute_protocol_similarity(emb, emb.clone())
    assert -1.0 <= sim_same <= 1.0
    assert sim_same > 0.99
>>>>>>> origin/main

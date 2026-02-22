import pytest
from unittest.mock import MagicMock, patch
import sys
import importlib

@pytest.fixture(scope="function")
def mock_dependencies():
    """
    Mocks system modules to allow importing mcp_server without 
    initializing the actual FastMCP server or database connections.
    """
    with patch.dict(sys.modules):
        # Mock dependencies
        mock_bootstrap = MagicMock()
        mock_fastmcp_mod = MagicMock()
        mock_storage = MagicMock()
        mock_schemas = MagicMock()
        
        # Setup FastMCP class and instance
        mock_mcp_instance = MagicMock()
        
        # Configure @mcp.tool() decorator to be a transparent passthrough
        def tool_decorator():
            def wrapper(func):
                return func
            return wrapper
        mock_mcp_instance.tool.side_effect = tool_decorator
        
        # Link class to instance
        mock_fastmcp_mod.FastMCP.return_value = mock_mcp_instance
        
        # Apply mocks to sys.modules
        sys.modules["bootstrap"] = mock_bootstrap
        sys.modules["fastmcp"] = mock_fastmcp_mod
        sys.modules["mcp.server.fastmcp"] = mock_fastmcp_mod
        sys.modules["orchestrator.storage"] = mock_storage
        sys.modules["schemas.database"] = mock_schemas
        
        # Import (or reload) the module under test with mocks active
        import mcp_server
        importlib.reload(mcp_server)
        
        yield mcp_server

def test_get_artifact_trace(mock_dependencies):
    """Test retrieval of artifact traces with mocked DB."""
    mcp_server = mock_dependencies
    
    # Setup Mock DB Session
    mock_db = MagicMock()
    mcp_server.SessionLocal.return_value = mock_db
    
    # Setup Mock Artifacts
    a1 = MagicMock(agent_name="Researcher", type="plan", id="root-1")
    a2 = MagicMock(agent_name="Coder", type="code", id="child-1")
    
    # Configure Query Chain: db.query().filter().all()
    mock_db.query.return_value.filter.return_value.all.return_value = [a1, a2]
    
    # Execute
    result = mcp_server.get_artifact_trace("root-1")
    
    # Verify
    assert len(result) == 2
    assert "Researcher: plan (ID: root-1)" in result[0]
    assert "Coder: code (ID: child-1)" in result[1]
    mock_db.close.assert_called_once()

def test_trigger_new_research(mock_dependencies):
    """Test triggering research via requests mock."""
    mcp_server = mock_dependencies
    
    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = {"status": "ok", "plan_id": "123"}
        
        result = mcp_server.trigger_new_research("build a game")
        
        assert result == {"status": "ok", "plan_id": "123"}
        mock_post.assert_called_once_with(
            "http://localhost:8000/orchestrate",
            params={"user_query": "build a game"}
        )
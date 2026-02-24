import pytest
import json
import requests
from unittest.mock import MagicMock, patch
from adapters.mcp_adapter import MCPToolAdapter
from schemas.events import RuntimeEvent, EventPayload, EventMetadata
from requests.exceptions import Timeout, HTTPError

# Helper to simulate the RuntimeEvent structure without needing the actual schema classes
class MockEvent:
    def __init__(self, tool_name, arguments, trace_id="test-trace-123"):
        self.payload = MagicMock()
        self.payload.data = {"tool_name": tool_name, "arguments": arguments}
        self.metadata = MagicMock()
        self.metadata.trace_id = trace_id

@pytest.fixture
def mcp_client():
    """Mock the external MCP client."""
    return MagicMock()

@pytest.fixture
def adapter(mcp_client):
    return MCPToolAdapter(mcp_client)

@pytest.fixture
def runtime_event():
    """Provides a sample RuntimeEvent for testing."""
    return RuntimeEvent(
        metadata=EventMetadata(source="test_runner"),
        payload=EventPayload(
            type="EXECUTE_TOOL",
            data={"tool_name": "render_vehicle_asset", "arguments": {"vehicle_model": "Toyota Supra A90"}}
        )
    )

def test_render_tool_enforces_physical_constants(adapter):
    """
    Verifies that render_vehicle_asset tool calls have their arguments mutated
    to enforce C5 symmetry, specific wheels, and paint finishes for target models.
    """
    # Setup: Arguments that have 'drifted' from the strict requirements
    tool_name = "render_vehicle_asset"
    drifted_args = {
        "vehicle_model": "Toyota Supra A90",
        "wheels": {
            "model": "Stock",
            "geometry": "10-spoke"
        },
        "symmetry_mode": "approximate",
        "paint_finish": "Matte Grey"
    }
    event = MockEvent(tool_name, drifted_args)

    # Execute: Patch EventPayload to inspect the return value
    with patch("adapters.mcp_adapter.EventPayload"), \
         patch("adapters.mcp_adapter.requests.post") as mock_post:
        
        mock_post.return_value.content = b'{"status": "ok"}'
        mock_post.return_value.status_code = 200
        
        adapter.execute(event)

    # Verify: The requests.post should be called with the MUTATED arguments in canonical JSON
    call_args = mock_post.call_args
    sent_data = json.loads(call_args[1]["data"])
    
    tool_called = sent_data["tool_name"]
    args_passed = sent_data["arguments"]

    assert tool_called == tool_name
    
    # Check Enforcements
    assert args_passed["symmetry_mode"] == "C5_SYMMETRY"
    
    # Check Wheels (Strict Advan GT Beyond enforcement)
    assert args_passed["wheels"]["model"] == "Advan GT Beyond"
    assert args_passed["wheels"]["geometry"] == "5-spoke"
    assert args_passed["wheels"]["finish"] == "Racing Sand Metallic (RSM)"
    assert args_passed["wheels"]["allowed_variations"] == []
    
    # Check Paint Finish (Supra should trigger Obsidian/Nocturnal Black)
    assert args_passed["paint_finish"] == "Obsidian/Nocturnal Black"

def test_render_tool_generic_vehicle_no_paint_override(adapter):
    """
    Verifies that non-target vehicles still get wheel/symmetry enforcement
    but do NOT get the specific paint finish override.
    """
    event = MockEvent("render_vehicle_asset", {
        "vehicle_model": "Generic Sedan",
        "paint_finish": "Midnight Blue"
    })

    with patch("adapters.mcp_adapter.EventPayload"), \
         patch("adapters.mcp_adapter.requests.post") as mock_post:
        
        mock_post.return_value.content = b'{"status": "ok"}'
        mock_post.return_value.status_code = 200
        adapter.execute(event)

    args_passed = json.loads(mock_post.call_args[1]["data"])["arguments"]
    
    # Geometry still enforced
    assert args_passed["symmetry_mode"] == "C5_SYMMETRY"
    # Paint preserved because "Generic Sedan" is not in the target list
    assert args_passed["paint_finish"] == "Midnight Blue"

def test_non_render_tool_passthrough(adapter):
    """
    Verifies that tools other than render_vehicle_asset are passed through untouched.
    """
    tool_name = "calculate_physics"
    original_args = {"mass": 1000, "velocity": 20}
    event = MockEvent(tool_name, original_args.copy())

    with patch("adapters.mcp_adapter.EventPayload"), \
         patch("adapters.mcp_adapter.requests.post") as mock_post:
        
        mock_post.return_value.content = b'{"status": "ok"}'
        mock_post.return_value.status_code = 200
        adapter.execute(event)

    # Arguments should be identical to input
    sent_data = json.loads(mock_post.call_args[1]["data"])
    assert sent_data["arguments"] == original_args

@pytest.mark.parametrize("tool_name", ["render_vehicle_asset", "any_other_tool"])
def test_execute_handles_timeout(adapter, runtime_event, tool_name):
    """
    Verifies that a timeout during the MCP call results in a proper ERROR payload.
    """
    runtime_event.payload.data["tool_name"] = tool_name
    
    with patch("adapters.mcp_adapter.requests.post", side_effect=Timeout("Connection timed out")):
        result_payload = adapter.execute(runtime_event)

    # Verify the payload indicates an error
    assert result_payload.type == "TOOL_RESULT"
    assert result_payload.data["status"] == "ERROR"
    assert "error" in result_payload.data["result"]
    assert "Connection timed out" in result_payload.data["result"]["error"]
    
    # Verify the receipt is correctly formed for an error
    receipt = result_payload.data["receipt"]
    assert receipt["status"] == "ERROR"
    assert receipt["response_hash"] is None
    assert receipt["tool_name"] == tool_name

def test_execute_http_error(adapter, runtime_event):
    """
    Verifies that the adapter handles HTTP errors (non-timeout) gracefully.
    """
    runtime_event.payload.data["tool_name"] = "render_vehicle_asset"
    
    # Mock response that raises HTTPError
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = HTTPError("500 Server Error")
    mock_response.content = b"Internal Server Error"

    with patch("adapters.mcp_adapter.requests.post", return_value=mock_response):
        result_payload = adapter.execute(runtime_event)

    # Assertions
    assert result_payload.type == "TOOL_RESULT"
    assert result_payload.data["status"] == "ERROR"
    assert "500 Server Error" in result_payload.data["result"]["error"]
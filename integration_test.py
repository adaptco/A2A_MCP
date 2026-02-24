import sys
import os
import logging
from uuid import uuid4

# Ensure we can import modules from the current directory
sys.path.append(os.getcwd())

try:
    from adapters.mcp_adapter import MCPToolAdapter
    from schemas.events import RuntimeEvent, EventPayload, EventMetadata
except ImportError as e:
    print(f"Critical Import Error: {e}")
    print("Ensure you are running this from the project root inside the container.")
    sys.exit(1)

# Configure logging to see adapter output
logging.basicConfig(level=logging.INFO)

def main():
    print("🚀 Starting Integration Test: Orchestrator -> MCP Adapter -> Node.js Server")

    # 1. Initialize Adapter
    # This will read MCP_SERVER_URL from the environment (http://mcp-server:8080)
    adapter = MCPToolAdapter()
    print(f"ℹ️  Adapter configured for: {adapter.server_url}")

    # 2. Prepare Test Data
    # We intentionally use 'drifted' arguments to verify the adapter enforces rules
    trace_id = str(uuid4())
    tool_name = "render_vehicle_asset"
    input_args = {
        "vehicle_model": "Aston Martin Vantage",
        "symmetry_mode": "approximate",  # Should be forced to C5_SYMMETRY
        "wheels": {"model": "stock"},    # Should be forced to Advan GT
        "paint_finish": "Matte Black"    # Should be forced to Obsidian/Nocturnal Black
    }

    print(f"📝 Sending Request [Trace: {trace_id}]")
    print(f"   Tool: {tool_name}")
    print(f"   Input Args: {input_args}")

    # 3. Construct Event
    event = RuntimeEvent(
        metadata=EventMetadata(trace_id=trace_id, source="integration_test"),
        payload=EventPayload(
            type="EXECUTE_TOOL",
            data={
                "tool_name": tool_name,
                "arguments": input_args
            }
        )
    )

    # 4. Execute
    try:
        response = adapter.execute(event)
        
        status = response.data.get("status")
        result = response.data.get("result", {})
        receipt = response.data.get("receipt", {})

        print(f"\nRESULTS: {status}")
        
        if status == "SUCCESS":
            print("✅ MCP Call Successful")
            
            # Verify Logic Enforcement
            returned_specs = result.get("specs", {})
            if returned_specs.get("symmetry_mode") == "C5_SYMMETRY":
                print("✅ Physical Constants Enforced: Symmetry is C5_SYMMETRY")
            else:
                print(f"❌ Enforcement Failed: Symmetry is {returned_specs.get('symmetry_mode')}")

            if "Advan GT Beyond" in str(returned_specs.get("wheels", {})):
                print("✅ Wheel Specs Enforced")
            else:
                print("❌ Wheel Specs Failed")

            # Verify Receipt
            if receipt.get("request_hash") and receipt.get("response_hash"):
                print(f"✅ Receipt Generated: {receipt['request_hash'][:8]}... -> {receipt['response_hash'][:8]}...")
            else:
                print("❌ Receipt Missing Hashes")
                
            print(f"\n📂 Render Path: {result.get('render_path')}")
            
        else:
            print("❌ MCP Call Failed")
            print(f"Error: {result}")

    except Exception as e:
        print(f"💥 Exception: {e}")

if __name__ == "__main__":
    main()
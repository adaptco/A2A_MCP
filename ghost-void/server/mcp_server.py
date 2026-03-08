import sys
import os
import json
import logging
import asyncio
from typing import Any, Sequence
from mcp.server import Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
from mcp.server.stdio import stdio_server

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("ghost-void-mcp")

# Ensure ADK CLI is in path for validation imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from adk.cli.validator import validate_file, load_schema
    import jsonschema
except ImportError:
    logger.warning("ADK CLI not found. Validation disabled.")

# Initialize MCP Server
app = Server("ghost-void-mcp")

# Global Engine State (Mocked for Scaffolding)
# In a real implementation, this would read from the engine process stdout
ENGINE_STATE = {
    "status": "ready",
    "position": {"x": 0, "y": 0},
    "entities": []
}

@app.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="ghost-void://state",
            name="Engine State",
            mimeType="application/json",
            description="Current state of the Ghost Void engine"
        )
    ]

@app.read_resource()
async def read_resource(uri: str) -> str | bytes:
    if uri == "ghost-void://state":
        return json.dumps(ENGINE_STATE, indent=2)
    raise ValueError(f"Unknown resource: {uri}")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="control_engine",
            description="Send a command to the Ghost Void engine. Validated against ADK schema.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": ["move_left", "move_right", "jump", "crouch", "interact"]
                    },
                    "payload": {
                        "type": "object",
                        "properties": {
                            "force": {"type": "number"},
                            "duration_ms": {"type": "integer"}
                        }
                    }
                },
                "required": ["command"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    if name == "control_engine":
        # 1. ADK Validation Logic
        # We manually validate against the mcp_protocol schema to prove integration
        schema = load_schema("https://adk.io/schemas/v0/mcp_protocol.schema.json")
        if schema:
            try:
                jsonschema.validate(instance=arguments, schema=schema)
            except jsonschema.ValidationError as e:
                return [TextContent(type="text", text=f"ADK Validation Failed: {e.message}")]
        
        # 2. Update State (Mock Engine Interaction)
        cmd = arguments.get("command")
        if cmd == "move_left":
            ENGINE_STATE["position"]["x"] -= 1
        elif cmd == "move_right":
            ENGINE_STATE["position"]["x"] += 1
        
        return [TextContent(type="text", text=f"Command '{cmd}' executed. New Position: {ENGINE_STATE['position']}")]
        
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

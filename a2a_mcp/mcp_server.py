"""Stdio MCP server compatibility entrypoint.

Canonical networked MCP runtime is `app.mcp_gateway:app` (`/mcp`, `/tools/call`).
This module is retained for local/CLI MCP clients that use stdio transport.
"""

from bootstrap import bootstrap_paths

bootstrap_paths()

from mcp.server.fastmcp import FastMCP
from app.mcp_tooling import register_tools

# Initialize FastMCP Server
mcp = FastMCP("A2A_Orchestrator")
register_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport="stdio")

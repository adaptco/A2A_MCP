from bootstrap import bootstrap_paths

bootstrap_paths()

from mcp.server.fastmcp import FastMCP
from app.mcp_tooling import register_tools

# Initialize FastMCP Server
mcp = FastMCP("A2A_Orchestrator")
register_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport="stdio")

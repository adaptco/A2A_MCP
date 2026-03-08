import asyncio
import sys
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run():
    # Configure the server parameters to run mcp_server.py
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["mcp_server.py"],
        env=dict(os.environ)  # Inherit environment
    )

    print("🔌 Connecting to MCP Server...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()
            print("✅ Connected to MCP Server")

            # List Tools
            tools = await session.list_tools()
            print(f"🛠️  Available Tools: {[t.name for t in tools.tools]}")

            # Call Tool
            print("🚀 Calling 'launch_game_instance'...")
            try:
                # Use --simulate to force the launcher to fallback
                result = await session.call_tool(
                    "launch_game_instance",
                    arguments={"server_url": "ws://localhost:8080", "simulate_fallback": True}
                )
                print("\n🎉 Tool Result:")
                # MCP results are list of content objects (TextContent, ImageContent, etc)
                print(result.content[0].text)
            except Exception as e:
                print(f"\n❌ Tool Call Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run())

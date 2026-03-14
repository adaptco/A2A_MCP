import torch
import asyncio
import sys
import os

# Add parent directory to path to import a2a_mcp
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a2a_mcp.runtime import MCPADKRuntime

async def main():
    print("🚀 Starting Basic Orchestration Demo...")
    
    # Initialize runtime
    runtime = MCPADKRuntime(use_real_llm=False)
    
    # Simulate CI/CD pipeline embeddings [10 artifacts, 4096 dims]
    ci_cd_embeddings = torch.randn(10, 4096)
    
    # Execute full pipeline
    result = await runtime.orchestrate(
        ci_cd_embeddings=ci_cd_embeddings,
        task="WHAM game orchestration for autonomous car",
        modalities=["text", "code"]
    )
    
    print("\n✅ Orchestration Complete!")
    print(f"  • MCP Token ID: {result['mcp_token'].token_id}")
    print(f"  • Skill Manifold Shape: {result['manifold'].shape}")
    print(f"  • MCP Tensor Size: {result['mcp_tensor'].shape[0]} floats")
    print(f"  • WASM Artifact Size: {len(result['wasm_artifact'])} bytes")
    
    print("\n📝 Generated Agent Wrapper Snippet:")
    print("-" * 40)
    # Print first few lines of generated code
    print("\n".join(result['agent_code'].split("\n")[:10]))
    print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())

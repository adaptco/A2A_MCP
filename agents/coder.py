from schemas.agent_artifacts import MCPArtifact
import uuid

class CoderAgent:
    def __init__(self):
        self.name = "Coder_v1"

    async def run(self, research_artifact: MCPArtifact) -> MCPArtifact:
        """
        Consumes a research artifact and produces a code artifact.
        """
        print(f"[{self.name}] Developing solution based on: {research_artifact.artifact_id}...")
        
        # Logic to extract content from the previous agent's work
        context = research_artifact.content
        
        # Simulate code generation
        code_content = f"""
        # Auto-generated Implementation
        # Based on Research: {research_artifact.artifact_id}
        
        def main():
            print("Executing strategy: {context.split('Execution Strategy: ')[-1].strip()}")
            
        if __name__ == "__main__":
            main()
        """
        
        return MCPArtifact(
            artifact_id=f"cod-{uuid.uuid4().hex[:8]}",
            type="code_solution",
            content=code_content,
            metadata={
                "agent": self.name,
                "parent_artifact": research_artifact.artifact_id,
                "language": "python"
            }
        )

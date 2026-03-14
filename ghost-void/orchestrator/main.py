import asyncio
from orchestrator.storage import DBManager
from orchestrator.llm_util import LLMService
from agents.coder import CoderAgent
from agents.tester import TesterAgent
<<<<<<< HEAD
from agents.gemini_agent import GeminiAgent
from middleware.runtime import AgenticRuntime
=======
>>>>>>> origin/main

class MCPHub:
    def __init__(self):
        self.db = DBManager()
<<<<<<< HEAD
        self.runtime = AgenticRuntime()
        self.coder = CoderAgent()
        self.tester = TesterAgent()
        self.gemini = GeminiAgent(runtime=self.runtime)

    async def run_healing_loop(self, task_description: str, max_retries=3):
        """
        Phase 2 Logic: Orchestrates the Research -> Code -> Test flow 
        with automatic self-correction loops.
        """
        iteration = 0
        current_parent_id = "initial_research"
        
        # Initial Generation
        artifact = await self.coder.generate_solution(current_parent_id, task_description)
        
        while iteration < max_retries:
            print(f"--- Iteration {iteration + 1}: Testing Artifact {artifact.artifact_id} ---")
            
            # Tester evaluates the artifact
            report = await self.tester.validate(artifact.artifact_id)
            
            if report.status == "PASS":
                print("✓ System Healthy: Solution Verified.")
                return artifact

            # Phase 2 Self-Healing: Route feedback back to Coder
            print(f"✗ Failure Detected: {report.critique}")
            artifact = await self.coder.generate_solution(
                parent_id=artifact.artifact_id, 
                feedback=report.critique
            )
            iteration += 1

        print("!! Max retries reached. Human intervention required.")
        return None

    async def run_gemini_rag(self, task_goal: str, query_vector=None, knowledge_base: dict = None):
        """
        Phase 8: Orchestrate Gemini Model Cluster for RAG-based LoRA distillation.
        Results are emitted via AgenticRuntime (and dual-written to FossilChain).
        """
        return await self.gemini.distill_context_for_lora(
            task_goal=task_goal,
            query_vector=query_vector or [],
            knowledge_base=knowledge_base or {}
        )

if __name__ == "__main__":
    hub = MCPHub()
    asyncio.run(hub.run_healing_loop("Fix connection string in storage.py"))

=======
        self.coder = CoderAgent()
        self.tester = TesterAgent()
>>>>>>> origin/main

    async def run_healing_loop(self, task_description: str, max_retries=3):
        """
        Phase 2 Logic: Orchestrates the Research -> Code -> Test flow 
        with automatic self-correction loops.
        """
        iteration = 0
        current_parent_id = "initial_research"
        
        # Initial Generation
        artifact = await self.coder.generate_solution(current_parent_id, task_description)
        
        while iteration < max_retries:
            print(f"--- Iteration {iteration + 1}: Testing Artifact {artifact.artifact_id} ---")
            
            # Tester evaluates the artifact
            report = await self.tester.validate(artifact.artifact_id)
            
            if report.status == "PASS":
                print("✓ System Healthy: Solution Verified.")
                return artifact

            # Phase 2 Self-Healing: Route feedback back to Coder
            print(f"✗ Failure Detected: {report.critique}")
            artifact = await self.coder.generate_solution(
                parent_id=artifact.artifact_id, 
                feedback=report.critique
            )
            iteration += 1

        print("!! Max retries reached. Human intervention required.")
        return None

if __name__ == "__main__":
    hub = MCPHub()
    asyncio.run(hub.run_healing_loop("Fix connection string in storage.py"))

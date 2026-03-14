import asyncio
from orchestrator.storage import DBManager
from orchestrator.llm_util import LLMService
from middleware import AgenticRuntime, WhatsAppEventObserver, TetrisScoreAggregator
from middleware.genie_adapter import GenieAdapter
from agency_hub.genie_bridge import GenieBridge
from schemas.model_artifact import AgentLifecycleState
from agents.hub import AgentHub

from agency_hub.spokes.ghost_void_spoke import GhostVoidSpoke
from agency_hub.architect.locomotion import LocomotionController
from typing import Tuple, List, Any, Dict

class MCPHub:
    def __init__(self):
        self.db = DBManager()
        
        # Initialize Agentic Runtime Middleware with observers
        wa_observer = WhatsAppEventObserver()
        tetris_aggregator = TetrisScoreAggregator(wa_observer)
        self.runtime = AgenticRuntime(observers=[wa_observer, tetris_aggregator])
        
        # Centralized Agent Management
        self.agent_hub = AgentHub(runtime=self.runtime)
        self.coder = self.agent_hub.coder
        self.tester = self.agent_hub.tester
        self.gemini_agent = self.agent_hub.gemini
        
        # Locomotion Model Layer
        self.spoke = GhostVoidSpoke()
        self.locomotion = LocomotionController(self.spoke)

        # Project Genie Interactive Scaffolding
        self.genie_bridge = GenieBridge(self.spoke)
        self.genie = GenieAdapter(self.runtime, self.genie_bridge)

    async def process_movement_command(self, target_coords: Tuple[int, int]):
        """
        Bridge the conversation loop to the locomotion model.
        """
        print(f"MCPHub: Orchestrating movement to {target_coords}")
        success = await self.locomotion.move_to(target_coords, self.runtime)
        if success:
            print("MCPHub: Movement completed successfully.")
        else:
            print("MCPHub: Movement failed or timed out.")
        return success

    async def distill_knowledge_for_lora(self, task_goal: str, query_vector: Any, knowledge_base: Dict[str, Any]):
        """
        Use the Gemini Model Cluster to distill RAG context into a LoRA dataset.
        """
        print(f"MCPHub: Initiating knowledge distillation for: {task_goal}")
        artifact = await self.gemini_agent.distill_context_for_lora(task_goal, query_vector, knowledge_base)
        return artifact

    async def run_healing_loop(self, task_description: str, max_retries=3):
        """
        Phase 2 Logic: Orchestrates the Research -> Code -> Test flow 
        with automatic self-correction loops managed by the middleware.
        """
        iteration = 0
        current_parent_id = "initial_research"
        
        # Initial Generation
        artifact = await self.coder.generate_solution(current_parent_id, task_description)
        # Middleware handle event persistence and notification
        await self.runtime.emit_event(artifact)
        
        while iteration < max_retries:
            print(f"--- Iteration {iteration + 1}: Testing Artifact {artifact.artifact_id} ---")
            
            # Tester evaluates the artifact
            report = await self.tester.validate(artifact.artifact_id)
            
            if report.status == "PASS":
                # Middleware handle transition and persistence
                try:
                    artifact = await self.runtime.transition_and_emit(artifact, AgentLifecycleState.CONVERGED)
                    print(f"✓ System Healthy: Solution Verified. Transitioned to {AgentLifecycleState.CONVERGED.value}")
                except Exception as e:
                    print(f"✓ System Healthy: Solution Verified. (Transition Warning: {e})")
                
                return artifact

            # Phase 2 Self-Healing
            print(f"✗ Failure Detected: {report.critique}")
            
            # Transition to HEALING state via Middleware
            try:
                artifact = await self.runtime.transition_and_emit(artifact, AgentLifecycleState.HEALING)
            except Exception:
                pass

            artifact = await self.coder.generate_solution(
                parent_id=artifact.artifact_id, 
                feedback=report.critique
            )
            # Notify runtime of new artifact version
            await self.runtime.emit_event(artifact)
            
            iteration += 1

        print("!! Max retries reached. Human intervention required.")
        # Final terminal state: FAILED
        try:
            artifact = await self.runtime.transition_and_emit(artifact, AgentLifecycleState.FAILED)
        except Exception:
            pass
                
        return None

if __name__ == "__main__":
    hub = MCPHub()
    # Mock run won't work without actual agents/LLM keys, but structure is correct.
    # asyncio.run(hub.run_healing_loop("Fix connection string in storage.py"))

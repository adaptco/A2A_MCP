import logging
from typing import Dict, Any, List, Optional
from agency_hub.experts.gemini_cluster import GeminiModelCluster
from agency_hub.architect.context_wrapper import GeminiContextWrapper
from middleware.runtime import AgenticRuntime
from schemas.model_artifact import AgentLifecycleState, ModelArtifact

logger = logging.getLogger(__name__)

class GeminiAgent:
    """
    Orchestrates the Gemini Model Cluster for intelligent RAG and LoRA distillation.
    Layers intelligence as an orchestration of abstractions.
    """
    def __init__(self, runtime: Optional[AgenticRuntime] = None):
        self.cluster = GeminiModelCluster()
        self.context = GeminiContextWrapper()
        self.runtime = runtime
        self.agent_name = "GeminiClusterAgent"

    async def distill_context_for_lora(self, task_goal: str, query_vector: Any, knowledge_base: Dict[str, Any]) -> ModelArtifact:
        """
        1. Injects RAG context into the unified wrapper.
        2. Adds the task goal.
        3. Executes inference via the Model Cluster.
        4. Records the distilled outcome in the Agentic Runtime.
        """
        # 1. Prepare Context
        self.context.clear()
        self.context.inject_rag_context(query_vector, knowledge_base)
        self.context.add_message("user", task_goal)
        
        prompt = self.context.format_for_inference()
        
        # 2. Inference via Cluster
        response = await self.cluster.infer(prompt, task_hint=task_goal)
        distilled_content = response["content"]
        
        # 3. Create Artifact
        artifact = ModelArtifact(
        artifact_id=f"gemini-{__import__('uuid').uuid4()}",
            model_id=response["model_used"],
            weights_hash="distilled-lora-context",
            embedding_dim=64, # Matches TensorField default
            state=AgentLifecycleState.CONVERGED, # Telemetry as converged distillation
            content=distilled_content,
            metadata={
                "task_goal": task_goal,
                "cluster_metadata": response["metadata"]
            },
            agent_name=self.agent_name
        )
        
        # 4. Record and Notify
        if self.runtime:
            await self.runtime.emit_event(artifact)
            
        logger.info(f"GeminiAgent: Successfully distilled context for LoRA using {response['model_used']}.")
        return artifact

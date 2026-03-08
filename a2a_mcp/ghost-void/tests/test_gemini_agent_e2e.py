import pytest
import numpy as np
from unittest.mock import MagicMock, AsyncMock
from agents.gemini_agent import GeminiAgent
from middleware.runtime import AgenticRuntime
from schemas.model_artifact import AgentLifecycleState, ModelArtifact

@pytest.mark.asyncio
class TestGeminiAgentE2E:
    async def test_gemini_model_selection(self):
        """Verify that the cluster selects appropriate models for different tasks."""
        agent = GeminiAgent()
        
        # Complex task
        model_pro = agent.cluster.select_model("Deeply refactor the manifold logic for complex reasoning")
        assert "pro" in model_pro
        
        # Simple task
        model_flash = agent.cluster.select_model("Quickly summarize current state")
        assert "flash" in model_flash

    async def test_rag_distillation_flow(self):
        """Verify the full E2E flow from RAG retrieval to converged artifact."""
        mock_runtime = MagicMock(spec=AgenticRuntime)
        mock_runtime.emit_event = AsyncMock()
        
        agent = GeminiAgent(runtime=mock_runtime)
        
        task_goal = "Create a LoRA for smooth motor control"
        query_vector = np.random.rand(64)
        knowledge_base = {
            "motor_smoothness": np.random.rand(64),
            "safety_envelope": np.random.rand(64)
        }
        
        artifact = await agent.distill_context_for_lora(task_goal, query_vector, knowledge_base)
        
        # Verify artifact properties
        assert isinstance(artifact, ModelArtifact)
        assert artifact.agent_name == "GeminiClusterAgent"
        assert artifact.state == AgentLifecycleState.CONVERGED
        assert "MOCK RESPONSE" in artifact.content
        assert artifact.metadata["task_goal"] == task_goal
        
        # Verify runtime recording
        mock_runtime.emit_event.assert_called_once_with(artifact)

    def test_context_wrapper_formatting(self):
        """Verify that context is correctly formatted for the cluster."""
        agent = GeminiAgent()
        agent.context.add_message("user", "Hello Gemini")
        agent.context.rag_memory = {"concept_A": 0.95}
        
        prompt = agent.context.format_for_inference()
        assert "[SYSTEM CONTEXT: RAG-AUGMENTED]" in prompt
        assert "concept_A: confidence 0.95" in prompt
        assert "USER: Hello Gemini" in prompt

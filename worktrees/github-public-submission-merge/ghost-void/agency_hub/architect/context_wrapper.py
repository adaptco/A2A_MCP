from typing import List, Dict, Any, Optional
import logging
from agency_hub.tensor_field import TensorField

logger = logging.getLogger(__name__)

class GeminiContextWrapper:
    """
    Manages the unified context for the Gemini AI Cluster.
    Integrates RAG retrieval and formats context for inference.
    """
    def __init__(self, tensor_field: Optional[TensorField] = None):
        self.tensor_field = tensor_field or TensorField(embedding_dim=64)
        self.message_history: List[Dict[str, str]] = []
        self.rag_memory: Dict[str, Any] = {}

    def add_message(self, role: str, content: str):
        """Add a turn to the conversation history."""
        self.message_history.append({"role": role, "parts": [{"text": content}]})

    def inject_rag_context(self, query_vector: Any, knowledge_base: Dict[str, Any]):
        """
        Retrieves relevant vectors from the knowledge base using the tensor field.
        """
        insights = self.tensor_field.rag_unify(query_vector, knowledge_base)
        self.rag_memory = insights
        logger.info(f"GeminiContext: Injected {len(insights)} RAG insights into context.")

    def format_for_inference(self) -> str:
        """
        Serializes the unified context (history + RAG) into a single prompt string.
        Optimized for Gemini model parsing.
        """
        prompt_parts = ["[SYSTEM CONTEXT: RAG-AUGMENTED]"]
        
        # Add RAG insights
        if self.rag_memory:
            prompt_parts.append("### Contextual Insights")
            for concept, weight in self.rag_memory.items():
                prompt_parts.append(f"- {concept}: confidence {weight:.2f}")
        
        # Add Conversation History
        prompt_parts.append("### Conversation History")
        for msg in self.message_history:
            role = msg["role"]
            text = msg["parts"][0]["text"]
            prompt_parts.append(f"{role.upper()}: {text}")

        prompt_parts.append("### Task")
        prompt_parts.append("Distill the above context to create a valid LoRA training dataset snippet.")
        
        return "\n".join(prompt_parts)

    def clear(self):
        """Reset the context."""
        self.message_history = []
        self.rag_memory = {}

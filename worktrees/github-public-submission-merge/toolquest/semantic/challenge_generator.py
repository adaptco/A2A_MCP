"""
Challenge Generator service for ToolQuest.
Synthesizes AI challenges based on semantic tool clusters.
"""
import random
from typing import List, Dict, Optional
from qdrant_client import QdrantClient

from schemas import SemanticChallenge, ToolEmbedding

class ChallengeGenerator:
    """Generates interactive challenges based on tool context."""
    
    def __init__(self, qdrant_client: QdrantClient, collection_name: str):
        self.qdrant = qdrant_client
        self.collection_name = collection_name
        
    def generate_challenge(self, tool_id: str) -> Optional[SemanticChallenge]:
        """
        Generate a challenge focused on a specific tool and its neighbors.
        """
        # 1. Retrieve the focus tool
        tools = self.qdrant.retrieve(
            collection_name=self.collection_name,
            ids=[tool_id],
            with_vectors=True
        )
        
        if not tools:
            return None
            
        focus_tool = tools[0]
        focus_tool_name = focus_tool.payload["tool_name"]
        
        # 2. Find semantic neighbors (Simulated Retrieval Augmentation)
        # We use the tool's vector to find what else is "conceptually close"
        neighbors = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=focus_tool.vector,
            limit=4  # Get 3 neighbors + self
        )
        
        # Filter out self and get neighbor metadata
        neighbor_tools = [
            n for n in neighbors 
            if n.id != tool_id and n.score > 0.6  # Only relevant neighbors
        ]
        
        # 3. Synthesize Scenario (Mocked LLM Generation)
        # In a real system, this would call an LLM with the tool descriptions
        scenario = self._generate_scenario_prompt(focus_tool.payload, neighbor_tools)
        
        # 4. Calculate difficulty dynamically
        difficulty_score = (focus_tool.payload.get("difficulty_tier", 1) * 0.2) + 0.3
        
        return SemanticChallenge(
            challenge_id=f"ch_{tool_id}_{random.randint(1000, 9999)}",
            generated_task=scenario["task"],
            semantic_neighbors=[n.payload["tool_name"] for n in neighbor_tools],
            required_tools=[focus_tool_name] + [n.payload["tool_name"] for n in neighbor_tools[:1]],
            difficulty_score=difficulty_score,
            xp_reward=int(difficulty_score * 1000),
            time_limit_seconds=300,
            novelty_factor=0.8
        )
    
    def _generate_scenario_prompt(self, focus_tool: Dict, neighbors: List) -> Dict:
        """
        Mock LLM generation of a scenario.
        Returns a dict with 'task' description.
        """
        tool_name = focus_tool["tool_name"]
        
        # Templates for different tool categories (simplified)
        templates = [
            f"You are a system administrator relying on '{tool_name}' to solve a critical issue. "
            f"Unexpectedly, you also need to combine it with related tools to process the output.",
            
            f"A junior developer has left a broken script using '{tool_name}'. "
            f"Debug the process and optimize it using modern alternatives found in the semantic cluster.",
            
            f"Security Audit: Usage of '{tool_name}' has flagged an anomaly. "
            f"Investigate the logs and filter the results."
        ]
        
        base_scenario = random.choice(templates)
        
        if neighbors:
            neighbor_names = [n.payload["tool_name"] for n in neighbors]
            base_scenario += f" Consider using: {', '.join(neighbor_names)}."
            
        return {"task": base_scenario}

"""
Agency Docking Shell (Hub Controller)
Orchestrates the Observe-Normalize-Unify-Act cycle.
"""

from typing import Dict, Any, List, Optional
import time
import numpy as np
from .spoke_adapter import SpokeAdapter
from .tensor_field import TensorField
from middleware import AgenticRuntime

class DockingShell:
    """
    The main agentic loop container.
    Connects to a Spoke (environment), maintains a TensorField (cognition),
    and executes the learning cycle.
    """
    
    def __init__(self, embedding_dim: int = 64, runtime: AgenticRuntime = None):
        self.tensor_field = TensorField(embedding_dim)
        self.spoke: Optional[SpokeAdapter] = None
        self.knowledge_base: Dict[str, np.ndarray] = {}
        self.history: List[Dict] = []
        self.runtime = runtime
        
    async def dock(self, spoke: SpokeAdapter, model_info: Dict = None):
        """
        Connect to a game environment and optionally trigger a handshake.
        model_info should contain: model_id, weights_hash, embedding_dim
        """
        self.spoke = spoke
        print(f"[DOCK] Connected to Spoke: {type(spoke).__name__}")
        
        if model_info and self.runtime:
            print(f"[HANDSHAKE] Initiating handshake for model: {model_info.get('model_id')}")
            await self.runtime.initiate_handshake(
                model_id=model_info['model_id'],
                weights_hash=model_info['weights_hash'],
                embedding_dim=model_info['embedding_dim'],
                metadata=model_info.get('metadata')
            )
        
    def inject_knowledge(self, concept: str, vector: List[float]):
        """Inject a known concept vector into the RAG memory."""
        self.knowledge_base[concept] = np.array(vector)
        
    def cycle(self) -> Dict[str, Any]:
        """
        Execute one agentic cycle:
        1. Observe (Spoke) -> Raw State
        2. Normalize (TensorField) -> Voxel Tensor -> Eigenstate
        3. Unify (TensorField) -> Retrieval Augmented Generation
        4. Act (Shell Policy) -> Action Token
        """
        if not self.spoke:
            raise RuntimeError("No Spoke docked!")
            
        # 1. Observe
        raw_state = self.spoke.observe()
        
        # 2. Normalize
        voxel_tensor = self.tensor_field.voxelize_state(raw_state)
        eigenstate = self.tensor_field.compute_eigenstate(voxel_tensor)
        
        # 3. Unify
        insights = self.tensor_field.rag_unify(eigenstate, self.knowledge_base)
        
        # 4. Act (Pattern Matching Policy)
        # In a real agent, this would be an LLM call or Neural Net inference
        token = self._synthesize_token(insights, raw_state)
        success = self.spoke.act(token)
        
        cycle_result = {
            "timestamp": time.time(),
            "eigenstate_norm": np.linalg.norm(eigenstate),
            "top_insight": max(insights, key=insights.get) if insights else None,
            "action": token,
            "success": success
        }
        self.history.append(cycle_result)
        return cycle_result
        
    def _synthesize_token(self, insights: Dict[str, float], raw_state: Dict) -> Dict:
        """
        Heuristic Policy:
        - If 'danger' insight is high -> FREEZE / EVADE
        - If 'reward' insight is high -> APPROACH
        - Else -> EXPLORE
        """
        # Simple hardcoded policy for scaffolding
        danger = insights.get("danger_vector", 0.0)
        reward = insights.get("reward_vector", 0.0)
        
        if danger > 0.5:
            return {"action": "evade", "params": {"urgency": danger}}
        elif reward > 0.5:
            return {"action": "approach", "params": {"target": "closest_entity"}}
        else:
            return {"action": "explore", "params": {"direction": "random"}}

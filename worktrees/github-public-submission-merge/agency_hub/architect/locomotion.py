from typing import Dict, Any, Tuple, List
import asyncio
import logging
import math
from agency_hub.spokes.ghost_void_spoke import GhostVoidSpoke
from middleware.runtime import AgenticRuntime
from schemas.model_artifact import AgentLifecycleState, ModelArtifact

class LocomotionController:
    """
    Orchestrates the Kinematic Loop from high-level movement goals.
    Bridges the Conversation Loop to the Simulation Spoke.
    """
    def __init__(self, spoke: GhostVoidSpoke):
        self.spoke = spoke
        self.logger = logging.getLogger("LocomotionController")

    async def move_to(self, target_pos: Tuple[int, int], runtime: AgenticRuntime) -> bool:
        """
        Orchestrate a series of kinematic steps to reach a target grid position.
        Records telemetry to the runtime at each step.
        """
        current_state = self.spoke.observe()
        current_pos = current_state.get("grid_pos", (0, 0))
        
        self.logger.info(f"Locomotion: Moving from {current_pos} to {target_pos}")
        
        # In a real scenario, this would be a pathfinding loop.
        # Here we simulate the kinematic progression towards the target.
        steps = 0
        max_steps = 10 # Safety limit
        
        while current_pos != target_pos and steps < max_steps:
            # Calculate next action (simple heuristic)
            action = self._calculate_next_action(current_pos, target_pos)
            
            # Execute kinematic step and get result state
            success, state = await self.kinematic_step(action, runtime)
            if not success:
                self.logger.error("Locomotion: Kinematic step failed.")
                return False
            
            # Update state from the returned observation
            current_pos = state.get("grid_pos")
            steps += 1
            
            # Small delay for simulation realism
            await asyncio.sleep(0.1)
            
        if current_pos == target_pos:
            self.logger.info(f"Locomotion: Reached target {target_pos} in {steps} steps.")
            return True
        else:
            self.logger.warning(f"Locomotion: Failed to reach target in {max_steps} steps. Last pos: {current_pos}")
            return False

    async def kinematic_step(self, action: Dict[str, Any], runtime: AgenticRuntime) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute a single simulation tick and record the telemetry.
        """
        # Execute action on spoke
        success = self.spoke.act(action)
        if not success:
            return False, {}
            
        # Observe result
        state = self.spoke.observe()
        
        # Create a telemetry artifact for the runtime
        # Each kinematic tick is an 'EMBEDDING' or 'HEALING' state update in the agent's memory
        telemetry = ModelArtifact(
        artifact_id=f"kinematic-{__import__('uuid').uuid4()}",
            model_id="locomotion-v1",
            weights_hash="kinematic-trace",
            embedding_dim=4,
            state=AgentLifecycleState.HEALING if state.get("drift_mode") == "DRIFT" else AgentLifecycleState.EMBEDDING,
            content=f"Kinematic Step Executed: action={action.get('action')}, result={state}",
            metadata={
                "grid_pos": state.get("grid_pos"),
                "energy": state.get("energy"),
                "drift_mode": state.get("drift_mode"),
                "similarity": state.get("similarity")
            }
        )
        
        await runtime.emit_event(telemetry)
        return True, state

    def _calculate_next_action(self, current: Tuple[int, int], target: Tuple[int, int]) -> Dict[str, Any]:
        """
        Heuristic for next move.
        Returns: {"action": "drive", "params": {"velocity": float, "steering": float, "prompt": str}}
        """
        dx = target[0] - current[0]
        dy = target[1] - current[1]
        
        # Very simple: move one grid unit at a time if delta is large
        # Map deltas to velocity and steering
        velocity = 0.5 if (abs(dx) > 0 or abs(dy) > 0) else 0.0
        
        # Simple steering logic
        if dx > 0: steer = 1.0   # Turn right
        elif dx < 0: steer = -1.0 # Turn left
        else: steer = 0.0
        
        if dy > 0 and dx == 0: steer = 0.5 # Slight veer
        
        return {
            "action": "drive",
            "params": {
                "velocity": velocity,
                "steering": steer,
                "prompt": f"Moving towards {target}"
            }
        }

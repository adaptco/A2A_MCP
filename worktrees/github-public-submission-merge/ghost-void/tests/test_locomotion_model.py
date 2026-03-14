import pytest
import asyncio
from typing import Tuple
from unittest.mock import MagicMock, AsyncMock
from agency_hub.architect.locomotion import LocomotionController
from agency_hub.spokes.ghost_void_spoke import GhostVoidSpoke
from middleware.runtime import AgenticRuntime
from schemas.model_artifact import AgentLifecycleState, ModelArtifact

@pytest.mark.asyncio
class TestLocomotionModel:
    async def test_kinematic_step_telemetry(self):
        """Verify that a single kinematic step emits telemetry and returns state."""
        mock_spoke = MagicMock(spec=GhostVoidSpoke)
        mock_spoke.act.return_value = True
        mock_spoke.observe.return_value = {
            "grid_pos": (6, 5),
            "energy": 99.0,
            "drift_mode": "GRIP",
            "similarity": 0.1
        }
        
        mock_runtime = MagicMock(spec=AgenticRuntime)
        mock_runtime.emit_event = AsyncMock()
        
        controller = LocomotionController(mock_spoke)
        
        action = {"action": "drive", "params": {"velocity": 0.5}}
        success, state = await controller.kinematic_step(action, mock_runtime)
        
        assert success is True
        assert state["grid_pos"] == (6, 5)
        mock_spoke.act.assert_called_once_with(action)
        mock_runtime.emit_event.assert_called_once()
        
        # Verify telemetry content
        telemetry = mock_runtime.emit_event.call_args[0][0]
        assert isinstance(telemetry, ModelArtifact)
        assert telemetry.state == AgentLifecycleState.EMBEDDING

    async def test_move_to_convergence(self):
        """Verify that move_to reaches the target through multiple steps."""
        mock_spoke = MagicMock(spec=GhostVoidSpoke)
        mock_spoke.act.return_value = True
        
        # Positions: Initial (5,5) -> steps to (6,5), (7,5), (8,5), (9,5), (10,5)
        positions = [(5, 5), (6, 5), (7, 5), (8, 5), (9, 5), (10, 5)]
        state_iter = iter([{"grid_pos": p, "energy": 100-i} for i, p in enumerate(positions)])
        
        # mock_spoke.observe will be called:
        # 1 time at start of move_to
        # 5 times inside move_to (via kinematic_step)
        mock_spoke.observe.side_effect = lambda: next(state_iter)
        
        mock_runtime = MagicMock(spec=AgenticRuntime)
        mock_runtime.emit_event = AsyncMock()
        
        controller = LocomotionController(mock_spoke)
        
        success = await controller.move_to((10, 5), mock_runtime)
        
        assert success is True
        assert mock_spoke.act.call_count == 5
        assert mock_runtime.emit_event.call_count == 5

    def test_calculate_next_action(self):
        """Verify the action heuristic."""
        mock_spoke = MagicMock(spec=GhostVoidSpoke)
        controller = LocomotionController(mock_spoke)
        
        action = controller._calculate_next_action((5, 5), (10, 5))
        assert action["params"]["velocity"] > 0
        assert action["params"]["steering"] == 1.0
        
        action = controller._calculate_next_action((5, 5), (5, 5))
        assert action["params"]["velocity"] == 0.0

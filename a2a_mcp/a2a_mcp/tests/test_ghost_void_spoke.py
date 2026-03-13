"""
Unit tests for agency_hub/spokes/ghost_void_spoke.py
"""

import pytest
import os
import subprocess
from unittest.mock import MagicMock, patch

from agency_hub.spokes.ghost_void_spoke import GhostVoidSpoke
from phase_space_tick import PhaseSpaceTick

@pytest.fixture
def sim_spoke():
    """Provides a GhostVoidSpoke instance in Python simulation mode."""
    return GhostVoidSpoke()

class TestGhostVoidSpokeSimulationMode:
    """Tests the GhostVoidSpoke class in its Python simulation fallback mode."""

    def test_initialization_simulation_mode(self, sim_spoke):
        """Verify that the spoke initializes in simulation mode without a binary."""
        assert isinstance(sim_spoke.world, PhaseSpaceTick)
        assert sim_spoke.process is None
        assert "Connected to PhaseSpaceTick" in sim_spoke.__str__() # A bit of a hack, but checks constructor print
        
    def test_get_state_schema(self, sim_spoke):
        """Test that the state schema is returned correctly."""
        schema = sim_spoke.get_state_schema()
        assert schema == {
            "energy": "float",
            "drift_mode": "string",
            "grid_pos": "tuple(int, int)",
            "similarity": "float"
        }

    def test_observe_initial_state(self, sim_spoke):
        """Test that observe() returns the correct initial state."""
        state = sim_spoke.observe()
        assert state["energy"] == 0.0
        assert state["drift_mode"] == "GRIP"
        assert state["grid_pos"] == (5, 5)

    def test_act_drive_updates_state(self, sim_spoke):
        """Test that the 'drive' action correctly updates the world state."""
        initial_state = sim_spoke.observe().copy()
        action_token = {"action": "drive", "params": {"velocity": 1.0, "steering": 0.5, "prompt": "test drive"}}
        
        result = sim_spoke.act(action_token)
        assert result is True
        
        new_state = sim_spoke.observe()
        assert new_state != initial_state
        assert new_state["energy"] > 0
        
    def test_act_reset_resets_state(self, sim_spoke):
        """Test that the 'reset' action reverts the state to its initial values."""
        # First, change the state
        sim_spoke.act({"action": "drive", "params": {"velocity": 1.0, "steering": 0.5, "prompt": "test drive"}})
        assert sim_spoke.observe()["energy"] > 0.0

        # Now, reset it
        reset_token = {"action": "reset"}
        result = sim_spoke.act(reset_token)
        assert result is True

        # Check if it's back to initial
        state = sim_spoke.observe()
        assert state["grid_pos"] == (5, 5)
        assert state["drift_mode"] == "GRIP"

    def test_act_unknown_action(self, sim_spoke):
        """Test that an unknown action is handled gracefully."""
        action_token = {"action": "fly", "params": {}}
        result = sim_spoke.act(action_token)
        assert result is False

class TestGhostVoidSpokeEngineMode:
    """Tests the GhostVoidSpoke class's C++ engine bridge functionality."""

    @patch('subprocess.Popen')
    def test_initialization_engine_mode(self, mock_popen):
        """Verify that the spoke attempts to start the C++ engine when a binary path is provided."""
        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = "Engine Ready"
        mock_popen.return_value = mock_proc
        
        # Create a dummy file to simulate the binary
        dummy_path = "dummy_engine.exe"
        with open(dummy_path, "w") as f:
            f.write("dummy")

        spoke = GhostVoidSpoke(binary_path=dummy_path)

        mock_popen.assert_called_with(
            [dummy_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        assert spoke.process is not None
        
        os.remove(dummy_path)
    
    @patch('subprocess.Popen')
    def test_act_sends_json_to_engine(self, mock_popen):
        """Test that the 'act' method sends a correct JSON command to the engine."""
        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = '{"status": "ok"}'
        mock_popen.return_value = mock_proc
        
        dummy_path = "dummy_engine.exe"
        with open(dummy_path, "w") as f:
            f.write("dummy")

        spoke = GhostVoidSpoke(binary_path=dummy_path)
        
        action_token = {"action": "drive", "params": {"velocity": 1.0, "steering": 0.5, "prompt": "test drive"}}
        spoke.act(action_token)
        
        # Verify that the correct JSON was written to the process's stdin
        written_data = spoke.process.stdin.write.call_args[0][0]
        assert '"action": "drive"' in written_data
        assert '"velocity": 1.0' in written_data
        
        os.remove(dummy_path)

    def test_fallback_to_simulation_if_binary_not_found(self):
        """Test that the spoke falls back to simulation mode if the binary path is invalid."""
        spoke = GhostVoidSpoke(binary_path="non_existent_binary.exe")
        assert isinstance(spoke.world, PhaseSpaceTick)
        assert spoke.process is None

import torch
import pytest
import numpy as np
from a2a_mcp.game_engine import WHAMGameEngine

class TestWHAMGameEngine:

    @pytest.fixture
    def mock_vector_store(self):
        # Create a tensor with a known mean for predictable multiplier
        # Mean of [2.0, 2.0] is 2.0
        return torch.tensor([2.0, 2.0])

    @pytest.fixture
    def engine(self, mock_vector_store):
        return WHAMGameEngine(mock_vector_store)

    def test_initialization(self, engine, mock_vector_store):
        assert engine.fps == 60
        assert engine.frame_time == 1.0 / 60
        assert torch.equal(engine.vector_store, mock_vector_store)

    @pytest.mark.asyncio
    async def test_run_frame_movement_d(self, engine):
        initial_state = {"pos_x": 0.0, "pos_y": 0.0}
        # Multiplier is 2.0
        # Action "D" increases pos_x by 1.0 * multiplier = 2.0
        result = await engine.run_frame("D", initial_state)

        assert result["status"] == "success"
        assert "timestamp" in result
        assert result["frame_state"]["pos_x"] == 2.0
        assert result["frame_state"]["pos_y"] == 0.0

    @pytest.mark.asyncio
    async def test_run_frame_movement_a(self, engine):
        initial_state = {"pos_x": 0.0, "pos_y": 0.0}
        # Multiplier is 2.0
        # Action "A" decreases pos_x by 1.0 * multiplier = -2.0
        result = await engine.run_frame("A", initial_state)

        assert result["frame_state"]["pos_x"] == -2.0
        assert result["frame_state"]["pos_y"] == 0.0

    @pytest.mark.asyncio
    async def test_run_frame_movement_w(self, engine):
        initial_state = {"pos_x": 0.0, "pos_y": 0.0}
        # Action "W" increases pos_y by 1.0 * multiplier = 2.0
        result = await engine.run_frame("W", initial_state)

        assert result["frame_state"]["pos_x"] == 0.0
        assert result["frame_state"]["pos_y"] == 2.0

    @pytest.mark.asyncio
    async def test_run_frame_movement_s(self, engine):
        initial_state = {"pos_x": 0.0, "pos_y": 0.0}
        # Action "S" decreases pos_y by 1.0 * multiplier = -2.0
        result = await engine.run_frame("S", initial_state)

        assert result["frame_state"]["pos_x"] == 0.0
        assert result["frame_state"]["pos_y"] == -2.0

    @pytest.mark.asyncio
    async def test_run_frame_no_movement(self, engine):
        initial_state = {"pos_x": 10.0, "pos_y": 10.0}
        # Unknown action, no movement
        result = await engine.run_frame("UNKNOWN", initial_state)

        assert result["frame_state"]["pos_x"] == 10.0
        assert result["frame_state"]["pos_y"] == 10.0

    def test_compile_to_wasm(self, engine, mock_vector_store):
        wasm_bytes = engine.compile_to_wasm()

        header = b"WASM_MCP_V1"
        assert wasm_bytes.startswith(header)

        # Verify payload contains numpy bytes
        expected_payload = mock_vector_store.numpy().tobytes()
        assert wasm_bytes[len(header):] == expected_payload

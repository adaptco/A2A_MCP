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

    @pytest.mark.parametrize(
        "action, initial_pos, expected_pos",
        [
            ("D", (0.0, 0.0), (2.0, 0.0)),
            ("A", (0.0, 0.0), (-2.0, 0.0)),
            ("W", (0.0, 0.0), (0.0, 2.0)),
            ("S", (0.0, 0.0), (0.0, -2.0)),
            ("UNKNOWN", (10.0, 10.0), (10.0, 10.0)),
        ],
    )
    @pytest.mark.asyncio
    async def test_run_frame_movement(self, engine, action, initial_pos, expected_pos):
        initial_state = {"pos_x": initial_pos[0], "pos_y": initial_pos[1]}
        result = await engine.run_frame(action, initial_state)

        assert result["status"] == "success"
        assert "timestamp" in result
        assert result["frame_state"]["pos_x"] == expected_pos[0]
        assert result["frame_state"]["pos_y"] == expected_pos[1]

    def test_compile_to_wasm(self, engine, mock_vector_store):
        wasm_bytes = engine.compile_to_wasm()

        header = b"WASM_MCP_V1"
        assert wasm_bytes.startswith(header)

        # Verify payload contains numpy bytes
        expected_payload = mock_vector_store.numpy().tobytes()
        assert wasm_bytes[len(header):] == expected_payload

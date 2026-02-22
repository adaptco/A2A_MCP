# Workflow Instructions: WHAM Game Engine Testing

## Overview
This workflow describes the process for validating the `WHAMGameEngine` and its dependencies.

## Steps
1. **Dependency Installation**:
   - Ensure `torch` and `numpy` are installed.
   - Run `pip install -r requirements.txt`.

2. **Test Execution**:
   - Run `pytest tests/test_wham_game_engine.py` to validate the engine logic.
   - Verify `test_run_frame_movement_*` tests pass to confirm movement logic.
   - Verify `test_compile_to_wasm` to confirm artifact generation.

3. **DMN Validation**:
   - Refer to `wham_engine_dmn.xml` for the decision logic governing movement based on input action and multiplier.

## Configuration
- See `diff_config.yaml` for a summary of changes applied in this workflow.

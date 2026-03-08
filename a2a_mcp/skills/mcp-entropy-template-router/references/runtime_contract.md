# Runtime Contract

Use this skill when an orchestration payload needs deterministic controls for:
- Avatar API skill-token injection (`api_skill_tokens`)
- Enthalpy/entropy style temperature (`style_temperature_profile`)
- Uniform dotproduct template routing (`template_route`)

## Output Fields

- `enthalpy`: risk + change-pressure scalar in `[0,1]`
- `entropy`: normalized Shannon entropy from template probabilities
- `temperature`: tuned style temperature, clamped to safe range
- `template_scores`: normalized dot-product scores for `frontend`, `backend`, `fullstack`
- `selected_template`: winning template label
- `selected_actions`: action list used to trigger implementation workflow
- `api_skill_tokens`: tokenized API skill bindings for avatar runtime shell

## Integration Points

1. `world_foundation_model.build_worldline_block` for planning payloads.
2. `schemas/runtime_bridge.RuntimeAssignmentV1` for handoff serialization.
3. `orchestrator/runtime_bridge.py` for runtime assignment construction.

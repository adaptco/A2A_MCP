# MCP 3D Agent Execution v1

Normative source-of-truth spec pack for client-side MCP runtime execution in dual
3D targets (`unity` and `threejs`) with multimodal RAG and vector-direction token
lineage.

## Scope

- Deterministic coder-agent execution chain:
  - `Planner -> Architect -> Coder -> Tester -> Reviewer`
- Client-side MCP runtime contract over existing runtime tools:
  - `submit_runtime_assignment`
  - `get_runtime_assignment`
  - `list_runtime_assignments`
  - `embed_submit`
  - `embed_status`
  - `embed_lookup`
  - `embed_dispatch_batch`
  - `route_a2a_intent`
- Token authority:
  - `schemas/kernel_control_token.v1.schema.json`
  - `schemas/TokenEvent.v1.schema.json`

## Production Artifact Flow

1. `worldline_block.json`
2. `multimodal_rag_logic_tree.json`
3. `token_reconstruction.json`
4. `workflow_actions.json`
5. `runtime_assignment`
6. `vector_direction_token_bundle`

## Layout

- `schemas/`: normative JSON schemas
- `examples/`: valid + invalid fixtures for each schema
- validation runner:
  - `scripts/validate_mcp_3d_agent_execution_spec.py`

## Mirror Consumption

This top-level path is authoritative. Mirrored trees should reference this pack
instead of copying schemas to avoid drift.

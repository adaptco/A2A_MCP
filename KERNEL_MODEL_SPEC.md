# Kernel Model Specification

## Purpose
Define a stable kernel contract that binds vector-manifold orchestration to release control and API-token policy.

## Model Id
- `kernel_id`: deterministic ID based on `plan_id`.
- `manifold_engine`: logical runtime (`vector-manifold-engine`).
- `vector_namespace`: isolated namespace (`a2a.manifold.<plan_id>`).

## Release Control Contract
- `release_channel`: defaults to `stable`.
- `api_token_env_var`: must be `A2A_MCP_API_TOKEN`.
- `release_control.required_phase`: `ready_for_release`.
- `release_control.token_stream_normalized`: `true`.
- `release_control.minimum_token_count`: at least 1 token.

## Spec References
- `INDEX.md`
- `MANIFOLD_VECTOR_RELEASE_SPEC.md`
- `runtime.assignment.v1` in `schemas/runtime_bridge.py`

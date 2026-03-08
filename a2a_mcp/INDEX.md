# A2A_MCP Agentic Factory Index

This index is the root entrypoint for the Agentic Factory System release-control stack.

## Kernel And Release Specs
- `KERNEL_MODEL_SPEC.md`: kernel model contract for vector manifold control and API-token gating.
- `MANIFOLD_VECTOR_RELEASE_SPEC.md`: release policy for vectorized runtime assignments and MCP handoff.

## Core Python Surfaces
- `orchestrator/release_orchestrator.py`: phase resolver and release gating signals.
- `orchestrator/runtime_bridge.py`: handshake bundle builder and runtime assignment writer.
- `schemas/runtime_bridge.py`: typed runtime handoff schema (`runtime.assignment.v1` + kernel model).
- `tests/test_release_orchestrator.py`: release-control behavior tests.

## API Token Control
- Runtime assignments reference `A2A_MCP_API_TOKEN` as the required environment variable for release-controlled MCP calls.

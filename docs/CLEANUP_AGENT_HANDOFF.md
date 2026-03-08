# Cleanup Agent Handoff

This file is the current slop queue for repository compaction and deployment maintenance.

## Slop Pile Snapshot

- Temp artifact deletions already staged: `223` files
- Pattern: `tmpclaude-*-cwd` and `specs/tmpclaude-*-cwd`
- Submodule local churn (excluded from auto-clean): `PhysicalAI-Autonomous-Vehicles`
- Local runtime DB churn (exclude from deploy commits): `a2a_mcp.db`

## Deployment Maintenance Queue

1. Runtime bridge consolidation
   - `orchestrator/runtime_bridge.py`
   - `schemas/runtime_bridge.py`
   - Action: split transport/schema assembly from stateful onboarding side-effects.
2. Multimodal retrieval simplification
   - `orchestrator/multimodal_rag_workflow.py`
   - `orchestrator/client_token_pipe.py`
   - Action: isolate vector selection logic into pure functions and reduce cross-module coupling.
3. OIDC ingress hardening
   - `scripts/oidc_token.py`
   - Action: enforce strict claim validation and normalize failure responses.
4. Contract regression alignment
   - `tests/test_webhook_handshake.py`
   - `tests/test_runtime_bridge_contract.py`
   - `tests/test_multimodal_rag_workflow.py`
   - Action: keep tests tied to runtime assignment schema and orchestration-state contract.

## Standard Cleanup Run

```bash
python scripts/cleanup_repo.py --compact
```

## Notes

- Keep cleanup commits separate from feature work.
- Do not auto-edit submodule content under `PhysicalAI-Autonomous-Vehicles`.
- Treat `.env` and database files as local-only unless explicitly needed for runtime fixtures.

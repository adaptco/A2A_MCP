# MCP Agent Release Final

## Current Release State
- Status: live
- Version train:
  - Phase 1: persistence layer
  - Phase 2: self-healing control plane
  - Phase 3: vector memory and retrieval
  - Phase 4: CI/CD monitor and signed workflow webhooks

## Launch Protocol
1. Start MCP runtime and webhook service.
2. Confirm workflow ingress endpoint is reachable.
3. Confirm CI monitor endpoint ingestion is enabled.
4. Validate release readiness from `/cicd/status/{head_sha}`.

## Required Runtime Configuration
1. `WEBHOOK_SHARED_SECRET` for token mode.
2. `GITHUB_WEBHOOK_SECRET` for signature mode.

## Required GitHub Secrets
1. `MCP_ENDPOINT`
2. `MCP_TOKEN`
3. `MCP_WEBHOOK_SECRET` (signature mode)

## References
1. `docs/release/CI_CD_MONITOR_RELEASE_NOTES.md`
2. `docs/release/AGENT_WORKFLOW_TASKS.md`
3. `PR_BODY.md`

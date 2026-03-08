# Canonical Control Plane

## Scope
This document is the architecture source of truth for the primary A2A_MCP runtime.

Primary runtime stack:

1. `orchestrator.api:app`
2. `app.mcp_gateway:app`
3. `rbac.rbac_service:app`

## Runtime Services

| Service | Entrypoint | Port | Purpose |
|---|---|---:|---|
| Orchestrator API | `orchestrator.api:app` | 8000 | Pipeline orchestration, plan ingress, actions catalog/execution |
| MCP Gateway | `app.mcp_gateway:app` | 8080 | MCP transport (`/mcp`) and compatibility tool endpoint (`/tools/call`) |
| RBAC Gateway | `rbac.rbac_service:app` | 8001 | Agent onboarding and permission checks |

## Request Flow

1. Client calls MCP gateway (`/mcp` or `/tools/call`) with bearer token.
2. MCP gateway validates OIDC claims and dispatches protected tools.
3. Orchestrator API executes multi-agent workflow via `IntentEngine`.
4. FSM transitions are enforced by `orchestrator.stateflow.StateMachine`.
5. Artifacts and plan snapshots are persisted through `orchestrator.storage`.
6. RBAC checks are enforced by orchestrator through `rbac.client.RBACClient`.

## Environment Contract

### Shared globals
- `ENV`
- `LOG_LEVEL`
- `DATABASE_URL`

### MCP runtime (`.env.runtime.mcp.example`)
- `OIDC_ENFORCE`
- `OIDC_ISSUER`
- `OIDC_AUDIENCE`
- `OIDC_JWKS_URL`
- `OIDC_AVATAR_REPOSITORY_ALLOWLIST`
- `OIDC_AVATAR_ACTOR_ALLOWLIST`
- `PORT`

### Orchestrator runtime (`.env.runtime.orchestrator.example`)
- `LLM_API_KEY`
- `LLM_ENDPOINT`
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`
- `RBAC_ENABLED`
- `RBAC_URL`
- `RBAC_SECRET`
- `AUTH_DISABLED`
- `PORT`

### RBAC runtime (`.env.runtime.rbac.example`)
- `RBAC_SECRET`
- `ALLOWED_ORIGINS`
- `ENV`
- `PORT`

## Authoritative MCP Tool Contract

Canonical tool registry for MCP gateway (`app.mcp_tooling`):

1. `ingest_repository_data`
2. `ingest_avatar_token_stream`

`/tools/call` payload shape:

```json
{
  "tool_name": "ingest_repository_data",
  "arguments": {
    "snapshot": {"repository": "org/repo"},
    "authorization": "Bearer <token>"
  }
}
```

## Legacy Compatibility Paths

These are retained for compatibility but are not canonical control-plane entrypoints:

- `orchestrator.main`
- `app.main`
- `mcp_server.py`
- webhook-only direct runtime (`orchestrator.webhook:app`)

## Auxiliary Subdomains (Non-Primary)

The following areas are treated as auxiliary unless explicitly promoted:

- `src/prime_directive`
- `src/core_orchestrator`
- `a2a_mcp`
- Node app stacks under `apps/` and related subprojects

## Deployment Topology

The canonical local stack is defined in `docker-compose.unified.yml`:

- `orchestrator`
- `mcp-gateway`
- `rbac-gateway`
- `db`
- optional supporting services (`redis`, `qdrant`, ingestion workers)

Kubernetes deployment is defined in `deploy/helm/a2a-mcp` and must follow the same env key contract.

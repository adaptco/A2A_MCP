# MCP Server vs A2A_MCP Client API — Architecture Comparison

This document maps the **remote MCP server** tools and protocol layer against the
**A2A_MCP client-side API** to clarify responsibilities, integration points, and
where drift can occur.

---

## High-Level Architecture

```
┌─────────────────────────────┐       ┌──────────────────────────────────┐
│   MCP SERVERS (Tool Layer)  │       │   CLIENT API (HTTP / FastAPI)    │
│                             │       │                                  │
│  mcp_server.py              │ stdio │  multi_client_api.py             │
│  ├─ FastMCP("A2A_Orch...")  │◄─────►│  ├─ POST /mcp/register           │
│  └─ register_tools(mcp)    │       │  ├─ POST /mcp/{id}/baseline      │
│                             │       │  ├─ POST /mcp/{id}/stream        │
│  runtime_mcp_server.py      │       │  ├─ POST /a2a/runtime/.../scen.  │
│  ├─ FastMCP("A2A_Runtime")  │       │  ├─ POST /a2a/scenario/.../rag   │
│  ├─ submit_runtime_assign.  │       │  ├─ POST /a2a/scenario/.../lora  │
│  ├─ get_runtime_assignment  │       │  └─ GET  /a2a/executions/verify  │
│  ├─ list_runtime_assign.    │       │                                  │
│  ├─ embed_submit            │       │  multi_client_router.py          │
│  ├─ embed_status            │       │  ├─ MultiClientMCPRouter         │
│  ├─ embed_lookup            │       │  ├─ ClientTokenPipe              │
│  ├─ embed_dispatch_batch    │       │  ├─ InMemoryEventStore           │
│  └─ route_a2a_intent        │       │  └─ ClientContext                │
│                             │       │                                  │
│  docker_mcp_catalog/        │       │  app/clients/                    │
│  ├─ read_file               │       │  ├─ github.py                    │
│  ├─ write_file              │       │  ├─ monday.py                    │
│  └─ list_directory          │       │  ├─ airtable.py                  │
│                             │       │  ├─ notion.py                    │
│  mcp_core.py (shared)       │       │  └─ clickup.py                   │
│  ├─ MCPCore (nn.Module)     │       │                                  │
│  ├─ MCPResult               │       │                                  │
│  └─ compute_protocol_sim.   │       │                                  │
└─────────────────────────────┘       └──────────────────────────────────┘
```

---

## Detailed Mapping

### Transport Layer

| Aspect | MCP Server | Client API |
|--------|-----------|------------|
| **Transport** | stdio (MCP protocol) | HTTP/REST (FastAPI) |
| **Entry point** | `mcp_server.py`, `runtime_mcp_server.py` | `app/multi_client_api.py` |
| **Framework** | `FastMCP` (MCP SDK) | `FastAPI` |
| **Auth model** | MCP client trust | OIDC claims + API key hash |

### Tool ↔ Endpoint Mapping

| MCP Server Tool | Client API Equivalent | Notes |
|-----------------|----------------------|-------|
| `register_tools(mcp)` | `POST /mcp/register` | Server registers tool catalog; Client registers a tenant |
| `submit_runtime_assignment` | `POST /a2a/runtime/{client_id}/scenario` | Both create runtime execution contexts |
| `get_runtime_assignment` | `GET /a2a/executions/{execution_id}/verify` | Server returns assignment; Client returns verification |
| `list_runtime_assignments` | — | No client equivalent (server-only admin tool) |
| `embed_submit` | `POST /mcp/{client_id}/stream` | Both accept token embeddings for processing |
| `embed_status` | — | Server-only; Client uses drift score in response |
| `embed_lookup` | `POST /a2a/scenario/{execution_id}/rag-context` | Both retrieve context from stored embeddings |
| `embed_dispatch_batch` | — | Server-only batch dispatch |
| `route_a2a_intent` | `POST /mcp/{client_id}/stream` (via router) | Intent routing vs. client-specific stream processing |
| `DockerMCPCatalog.read_file` | — | Server-only I/O sandbox |
| `DockerMCPCatalog.write_file` | — | Server-only I/O sandbox |
| `DockerMCPCatalog.list_directory` | — | Server-only I/O sandbox |

### Shared Core (`mcp_core.py`)

Both server and client sides consume `MCPCore`:

- **Server**: `runtime_mcp_server.py` uses it via `embed_control_plane.py`
- **Client**: `multi_client_router.py` instantiates `MCPCore()` directly in `MultiClientMCPRouter`

This shared dependency is the primary integration contract. Changes to `MCPCore` affect both sides.

### Isolation & Security

| Concern | MCP Server | Client API |
|---------|-----------|------------|
| **Tenant isolation** | MCP namespace (implicit) | `ClientContext` + namespace projection |
| **Drift detection** | — | `ClientTokenPipe._compute_drift()` via KS statistic |
| **Contamination guard** | — | `ContaminationError` raised on threshold breach |
| **Quota enforcement** | — | `QuotaExceededError` in `ClientTokenPipe` |
| **File sandboxing** | `DockerMCPCatalog._is_path_allowed()` | — |
| **Result witnessing** | — | HMAC signing in `_witness_result()` |

---

## Drift Risk Areas

1. **`MCPCore` schema changes** — If `MCPResult` fields change, both `runtime_mcp_server.py` and `multi_client_router.py` break
2. **Tool additions without endpoints** — New server tools without corresponding client routes create silent gaps
3. **Auth model divergence** — Server uses MCP trust; Client uses OIDC. A unified auth layer is recommended
4. **Event store split** — Server uses `RuntimeAssignmentV1` storage; Client uses `InMemoryEventStore`. These are not synchronized

---

## Recommended Actions

- [ ] Add a shared OpenAPI/tool schema that both server and client validate against
- [ ] Unify the event store backend so server assignments and client events share lineage
- [ ] Add the `mcp-server-client-api-validation.yml` GitHub Action (included in this PR) to catch drift on every PR

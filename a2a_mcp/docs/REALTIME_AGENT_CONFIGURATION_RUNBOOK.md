# Real-Time Agent Configuration Runbook (Repo Artifact, Local + Remote)

This is the canonical operator walk for configuring and invoking agent ingestion in real time from repository artifacts.

Canonical ingestion tool: `ingest_repository_data`.

Legacy references to `ingest_worldline_block` are compatibility/in-progress paths and are not the primary operator path in this runbook.

## 1. Prerequisites

- Python environment and dependencies installed (`pip install -r requirements.txt`).
- Repository checked out locally.
- A valid GitHub OIDC bearer token for your target environment.
- `GITHUB_OIDC_AUDIENCE` set to the expected OIDC audience where verification is enforced.

Optional environment variables:

```bash
export REPO_ROOT="/absolute/path/to/your/A2A_MCP"
export DATABASE_URL="sqlite:////absolute/path/to/your/A2A_MCP/a2a_mcp.db"
export GITHUB_OIDC_AUDIENCE="a2a-mcp"
```

## 2. Configure MCP Client Registration (`mcp_config.json`)

Use a local stdio entry and a remote streamable-http entry.

```json
{
  "mcpServers": {
    "a2a-orchestrator": {
      "command": "python",
      "args": ["/absolute/path/to/your/A2A_MCP/mcp_server.py"],
      "env": {
        "DATABASE_URL": "sqlite:////absolute/path/to/your/A2A_MCP/a2a_mcp.db"
      }
    },
    "a2a-orchestrator-remote": {
      "transport": "streamable-http",
      "url": "https://a2a-mcp.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${GITHUB_TOKEN}"
      }
    }
  }
}
```

Required local values:

- `mcpServers.a2a-orchestrator.command = "python"`
- `mcpServers.a2a-orchestrator.args[0] = absolute path to mcp_server.py`
- `mcpServers.a2a-orchestrator.env.DATABASE_URL = absolute SQLite path`

Required remote values:

- `transport = "streamable-http"`
- `url = https://<host>/mcp`
- `headers.Authorization = Bearer ${GITHUB_TOKEN}`

## 3. Build the Repo Artifact Payload

The ingestion contract expects:

- `snapshot.repository` (required for identity binding)
- `snapshot.commit_sha` (optional but recommended)
- any additional metadata fields needed by your process

Example payload:

```json
{
  "snapshot": {
    "repository": "adaptco/A2A_MCP",
    "commit_sha": "abc123def456",
    "actor": "github-actions",
    "metadata": {
      "source": "release-pipeline"
    }
  },
  "authorization": "Bearer <OIDC_TOKEN>"
}
```

## 4. Start Runtime Services

Local stdio MCP server:

```bash
python mcp_server.py
```

Optional HTTP gateway for remote-compatible invocation:

```bash
python -m uvicorn app.mcp_gateway:app --host 0.0.0.0 --port 8080
```

Health checks:

```bash
curl -s http://localhost:8080/healthz
curl -s http://localhost:8080/readyz
```

Expected:

- `/healthz` returns `{"status":"ok"}`
- `/readyz` returns `{"status":"ready"}`

## 5. Execute Tool Calls

### 5.1 Local MCP path (native tool call)

Use the MCP client against the ingestion app:

```python
import asyncio
from mcp.client import client as Client
from knowledge_ingestion import app_ingest

async def main():
    payload = {
        "snapshot": {
            "repository": "adaptco/A2A_MCP",
            "commit_sha": "abc123def456",
            "actor": "github-actions",
        },
        "authorization": "Bearer <OIDC_TOKEN>",
    }
    async with Client(app_ingest) as client:
        response = await client.call_tool("ingest_repository_data", payload)
        print(response)

asyncio.run(main())
```

### 5.2 Remote MCP compatibility path (`/tools/call`)

```bash
curl -sS -X POST "http://localhost:8080/tools/call" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <OIDC_TOKEN>" \
  -d '{
    "tool_name": "ingest_repository_data",
    "arguments": {
      "snapshot": {
        "repository": "adaptco/A2A_MCP",
        "commit_sha": "abc123def456",
        "actor": "github-actions"
      },
      "authorization": "Bearer <OIDC_TOKEN>"
    }
  }'
```

## 6. Validate the Response Contract

Success response shape:

```json
{
  "ok": true,
  "data": {
    "repository": "adaptco/A2A_MCP",
    "execution_hash": "<64-char-sha256>"
  }
}
```

Compatibility wrapper response from `/tools/call`:

```json
{
  "tool_name": "ingest_repository_data",
  "ok": true,
  "result": {
    "ok": true,
    "data": {
      "repository": "adaptco/A2A_MCP",
      "execution_hash": "<64-char-sha256>"
    }
  }
}
```

Failure mapping to enforce:

- `AUTH_BEARER_MISSING`: missing or malformed `Authorization` header.
- `AUTH_BEARER_EMPTY`: `Bearer ` with empty token.
- `REPOSITORY_CLAIM_MISMATCH`: snapshot repository differs from verified token claim.
- invalid OIDC token: decode/validation error.

## 7. Real-Time Verification Scenarios

Run and record these checks for each environment:

1. Local happy path: valid bearer token + matching repository claim.
2. Remote happy path: `POST /tools/call` returns `ok: true`.
3. Missing auth: malformed or absent bearer token rejected.
4. Claim mismatch: mismatched repository rejected with `REPOSITORY_CLAIM_MISMATCH`.
5. Token integrity: invalid/expired token rejected without leaking internals.
6. Determinism: same `repository + snapshot` produces same `execution_hash`.
7. Readiness: `/healthz` and `/readyz` return healthy before calls.

Determinism spot-check:

```bash
# Run the same request twice and compare execution_hash values.
```

## 8. Troubleshooting

`error: tool not found` from `/tools/call`:

- Ensure the gateway has an active tool registry mapping for `ingest_repository_data`.
- Verify the tool name exactly matches `ingest_repository_data`.

OIDC audience failure:

- Verify `GITHUB_OIDC_AUDIENCE` matches the `aud` claim expected by your token issuer.

Repository mismatch:

- Compare `snapshot.repository` to token claim `repository`.
- Use the exact owner/repo string from the verified claim.

Unexpected 400/500 from gateway:

- Check gateway logs for exception details.
- Verify request body includes both `snapshot` and `authorization`.

## 9. Notes on Canonical vs Legacy Paths

- Canonical operator tool in this repository is `ingest_repository_data(snapshot, authorization)`.
- `ingest_worldline_block` references in some docs/tests are compatibility or in-progress paths.
- When conflicts exist, implementation in `knowledge_ingestion.py` and `app/mcp_tooling.py` is source of truth.

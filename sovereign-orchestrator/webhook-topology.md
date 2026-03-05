# Webhook Topology — Echo Relay Mesh

All inter-agent messages route through Echo's MCP endpoint.
External webhooks (browsers, chatbots) enter via `repository_dispatch`.

```mermaid
graph LR
    subgraph External["🌐 External Sources"]
        Browser["Browser/Chatbot"]
        API["REST API Client"]
    end

    subgraph GHA["⚙️ GitHub Actions VM"]
        Dispatch["webhook-dispatch.yml"]
        Orchestrator["orchestrator.yml"]
        Runner["agent-runner.yml"]
    end

    subgraph Agents["🤖 Boo Agent Mesh"]
        Celine["🧠 Celine<br/>Planning"]
        Gloh["📚 Gloh<br/>RAG Retrieval"]
        Dot["🔧 Dot<br/>Code Gen + CI/CD"]
        Spryte["🎨 Spryte<br/>Frontend Gen"]
        Echo["📡 Echo<br/>Relay Broker"]
        Luma["✅ Luma<br/>Quality Gate"]
    end

    subgraph MCP["🔌 MCP Servers"]
        EchoMCP["Echo MCP<br/>mcp.echo.internal"]
        GlohMCP["Gloh MCP<br/>mcp.gloh.internal"]
        SovMCP["Sovereign MCP<br/>mcp.sovereign.internal"]
    end

    Browser -->|repository_dispatch| Dispatch
    API -->|repository_dispatch| Dispatch
    Dispatch --> Echo

    Orchestrator --> Celine
    Celine -->|plan| Echo
    Echo -->|enrichment request| Gloh
    Gloh -->|enriched plan| Echo
    Echo -->|code request| Dot
    Dot -->|code artifact| Echo
    Echo -->|frontend request| Spryte
    Spryte -->|UI artifact| Echo
    Echo -->|all artifacts| Luma
    Luma -->|attestation| Orchestrator

    Echo --- EchoMCP
    Gloh --- GlohMCP
    Dot --- SovMCP

    Runner -.->|executes| Celine
    Runner -.->|executes| Gloh
    Runner -.->|executes| Dot
    Runner -.->|executes| Spryte
```

## Webhook Flow

1. **Ingress**: External sources send `POST /repos/{owner}/{repo}/dispatches` with `event_type` and `client_payload`
2. **Route**: `webhook-dispatch.yml` extracts `to_agent` from payload and routes to the correct agent
3. **Execute**: Agent runs on the GitHub Actions VM via `runner.py`
4. **Relay**: Echo wraps output in an A2A envelope and fires `repository_dispatch` to the next agent
5. **Attest**: Luma validates all receipts and signs the attestation
6. **Artifacts**: All outputs uploaded as GitHub Actions artifacts

## OS-Agnostic Webhook Trigger

```bash
# From any OS, browser, or chatbot — trigger the pipeline:
curl -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/{owner}/{repo}/dispatches \
  -d '{"event_type":"chat-trigger","client_payload":{"task_id":"T-chat","to_agent":"Celine","payload":{"prompt":"Build a login page"}}}'
```

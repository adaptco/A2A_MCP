# Tools — Tool Registry

## LLM Router

- **Type**: SDK
- **Endpoint / Import**: `agents.runner.call_llm`
- **Auth**: `LLM_TARGET` env var routes to `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, or `OLLAMA_HOST`
- **Input Schema**: `{"system_prompt": "string", "user_message": "string"}`
- **Output Schema**: `{"response": "string"}`
- **Used By**: [Celine, Spryte, Dot]

## Echo Relay

- **Type**: Webhook
- **Endpoint / Import**: `https://mcp.echo.internal/sse`
- **Auth**: `ECHO_MCP_TOKEN`
- **Input Schema**: `{"envelope_version": "1.0", "task_id": "string", "from_agent": "string", "to_agent": "string", "llm_hop": "string", "payload": {}, "timestamp": "ISO8601", "signature": "Ed25519 or null"}`
- **Output Schema**: `{"status": "relayed", "receipt_id": "string"}`
- **Used By**: [Echo]

## Gloh RAG

- **Type**: MCP
- **Endpoint / Import**: `https://mcp.gloh.internal/sse`
- **Auth**: `GLOH_MCP_TOKEN`
- **Input Schema**: `{"query": "string", "top_k": "integer", "namespace": "string"}`
- **Output Schema**: `{"results": [{"content": "string", "score": "float", "metadata": {}}]}`
- **Used By**: [Gloh]

## Luma Attestor

- **Type**: CLI
- **Endpoint / Import**: `python agents/Luma/attest.py`
- **Auth**: none (runs locally in Actions runner)
- **Input Schema**: `{"receipts_dir": "path"}`
- **Output Schema**: `{"attestation": {"task_id": "string", "status": "pass|fail", "signature": "string"}}`
- **Used By**: [Luma]

## GitHub Actions Dispatch

- **Type**: REST
- **Endpoint / Import**: `https://api.github.com/repos/{owner}/{repo}/dispatches`
- **Auth**: `GITHUB_TOKEN`
- **Input Schema**: `{"event_type": "string", "client_payload": {}}`
- **Output Schema**: `HTTP 204 No Content`
- **Used By**: [Dot, Echo]

## Artifact Uploader

- **Type**: SDK
- **Endpoint / Import**: `actions/upload-artifact@v4`
- **Auth**: `GITHUB_TOKEN` (auto-provided)
- **Input Schema**: `{"name": "string", "path": "string"}`
- **Output Schema**: `{"artifact_id": "integer", "url": "string"}`
- **Used By**: [Dot, Spryte]

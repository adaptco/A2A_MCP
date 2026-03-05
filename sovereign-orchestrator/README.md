# Sovereign Orchestrator

**End-to-end AI coding agent framework** that uses GitHub Actions as production VMs, MCP servers for inter-agent messaging, and OS-agnostic webhooks to compile chat-context implementation plans into executable code artifacts.

## Architecture

| Component | Purpose |
|-----------|---------|
| `task-graph.a2a.json` | A2A protocol task DAG (7 nodes) |
| `rasic-matrix.json` | RASIC responsibility assignments |
| `mcp-registry.json` | MCP server endpoints |
| `Agents.md` / `Tools.md` / `Skills.md` | MoE Agent Card surface |
| `agents/runner.py` | Universal LLM adapter (Claude/OpenAI/Gemini/Ollama) |
| `.github/workflows/` | CI/CD pipelines |

## Agents (Boo Bindings)

| Agent | Domain | LLM Target |
|-------|--------|------------|
| **Celine** | Planning, prompt decomposition | Gemini |
| **Spryte** | Frontend generation (HTML/CSS/JS) | Gemini |
| **Echo** | Webhook relay broker | Any |
| **Gloh** | RAG vector store retrieval | Any |
| **Luma** | Quality gate, receipt attestation | Any |
| **Dot** | Code generation, CI/CD automation | Claude |

## Quick Start

1. **Configure GitHub Secrets**: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ECHO_MCP_TOKEN`, `GLOH_MCP_TOKEN`
2. **Push to main** to trigger `orchestrator.yml`
3. **Or use `workflow_dispatch`** with a prompt input
4. **Or send a webhook** from any browser/chatbot:

```bash
curl -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/{owner}/{repo}/dispatches \
  -d '{"event_type":"chat-trigger","client_payload":{"to_agent":"Celine","payload":{"prompt":"Build a dashboard"}}}'
```

## Governance

1. **Single Worldline** — one canonical `task-graph.a2a.json`; no forks
2. **SSOT** — `Agents.md`, `Tools.md`, `Skills.md` are the only sources of truth
3. **Echo as Relay** — all cross-LLM messages route through Echo
4. **Luma as Gate** — no artifact is complete without a Luma receipt
5. **Dot owns CI/CD** — all workflows are Dot's domain
6. **Fail-closed** — missing keys or unsigned receipts halt the pipeline

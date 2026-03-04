# A2A_MCP Unified Code-Generating ADK (v1.0.0)

This repository now includes a unified ADK implementation under `src/mcp_adk`.

## Included components

- Constitutional schemas (`src/mcp_adk/contracts`)
- Artifact schemas (`src/mcp_adk/artifact_schemas`)
- Runtime interfaces (`src/mcp_adk/runtime.py`)
- Internal adapters (`src/mcp_adk/codex_adapter.py`, `src/mcp_adk/orchestration_agent.py`)
- External API contract (`src/mcp_adk/contracts/agent_api.md`)
- Code generation templates (`src/mcp_adk/templates`)
- CLI implementation (`src/mcp_adk/cli.py`)

## CLI commands

```bash
python -m mcp_adk.cli generate python-agent <name>
python -m mcp_adk.cli generate ts-agent <name>
python -m mcp_adk.cli validate contract <file>
python -m mcp_adk.cli validate artifact <file>
python -m mcp_adk.cli scaffold codex-adapter
python -m mcp_adk.cli scaffold orchestration-agent
python -m mcp_adk.cli attest <receipt>
```

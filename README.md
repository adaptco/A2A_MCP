# A2A_MCP - Autonomous Agent Architecture with Model Context Protocol

[![CI](https://github.com/adaptco-main/A2A_MCP/actions/workflows/agents-ci-cd.yml/badge.svg)](https://github.com/adaptco-main/A2A_MCP/actions/workflows/agents-ci-cd.yml)
[![Unity MLOps](https://github.com/adaptco-main/A2A_MCP/actions/workflows/ml_pipeline.yml/badge.svg)](https://github.com/adaptco-main/A2A_MCP/actions/workflows/ml_pipeline.yml)

The **Agentic Factory** is a unified monorepo for autonomous agent orchestration, Model Context Protocol (MCP) tooling, and Unity-based RL training pipelines. It enforces strict governance, deterministic state transitions, and sovereign token management across distributed agent swarms.

## 🏗️ Architecture

The system follows a canonical control plane architecture where specialized agents operate as "Avatars" within a managed lattice.

- **Orchestrator**: Central authority for task decomposition and agent lifecycle.
- **MCP Bus**: Standardized Model Context Protocol communication layer.
- **WorldModel**: Stateful representation of the environmental context.
- **Sovereign RBAC**: Role-based access control enforcing tool-call boundaries.

Compatibility entrypoints are still preserved for legacy integration:
- `server.py` (FastAPI production endpoint)
- `mcp_server.py` (stdio MCP compatibility server)

See `docs/architecture/canonical_control_plane.md` for the source-of-truth architecture map.
See `docs/architecture/mcp_extension_route_map.mmd` for the companion Mermaid route diagram.
See `docs/architecture/mcp_extension_route_map.md` for the end-to-end route and extension seam map.

## Overview

A2A_MCP provides:
1.  **Autonomous Code Generation**: Dynamic synthesis of Python/C# code for environment manipulation.
2.  **Unity MLOps Pipeline**: End-to-end RL training, from code generation to Vertex AI model registration.
3.  **Deterministic Release Control**: Four-phase gating (SAMPLE, COMPOSE, GENERATE, LEDGER) for artifact integrity.
4.  **Multi-Platform Tooling**: Cross-OS shell execution and filesystem management via MCP.

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- `uv` (recommended) or `pip`
- Docker & Docker Compose (for local automation runtime)

### Installation
```bash
# Install core package and dev dependencies
pip install -e .[dev]

# Set up local environment
cp .env.example .env
```

### Automation Environment

For browser or desktop automations, use the dedicated simulator/runtime stack:

```powershell
Copy-Item .env.automation.example .env.automation
.\scripts\automation_runtime.ps1 -Action up -Build
```

This starts:

- Runtime API: `http://localhost:8010/healthz`
- Simulator frontend: `http://localhost:4173`

The automation stack uses `app.multi_client_api:app`, so the simulator can register a client, build runtime scenarios, request RAG context, export LoRA datasets, and verify lineage without the full unified stack.

## 🛠️ Development

### Running Tests
```bash
pytest tests/ -v
```

## 🔐 Security & Integrity

- **Signed Receipts**: Every critical state transition emits an RFC8785-canonicalized, signed VVL record.
- **Gating**: Invariants are enforced via the `PINNAgent` before any model weights or code are "seald" for release.
- **RBAC**: Agent permissions are scoped by sovereign tokens issued via `mcp_token.py`.

<!-- avatar-engine:auto:start -->
## Avatar-Engine Status
- **Last Sync**: 2026-03-14
- **Schedule**: **09:00 America/New_York** (DST-safe schedule gate)
- Catalog output refreshed by automation: `skills/SKILL.md`
- Safe merge policy: auto-merge only when required checks are green and conflict-free
<!-- avatar-engine:auto:end -->

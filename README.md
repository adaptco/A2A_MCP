# A2A_MCP - Autonomous Agent Architecture with Model Context Protocol

[![CI](https://github.com/adaptco-main/A2A_MCP/actions/workflows/agents-ci-cd.yml/badge.svg)](https://github.com/adaptco-main/A2A_MCP/actions/workflows/agents-ci-cd.yml)

A production-grade multi-agent AI orchestration framework that implements a self-healing architecture with Model Context Protocol (MCP) support.

## Overview

A2A_MCP delivers the Synapse digital twin, Chrono-Sync protocol, and World OS kernel, running under a single Docker Compose stack for local and CI environments. It features a self-healing multi-agent pipeline (Orchestrator, Coder, Tester, Researcher) and implements its own Model Context Protocol (MCP) server.

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    A2A_MCP Pipeline                         │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ManagingAgent ──► OrchestrationAgent ──► ArchitectureAgent│
│                                               │            │
│                                    ┌──────────┘            │
│                                    ▼                       │
│                              CoderAgent ◄──► TesterAgent   │
│                              (self-healing loop)           │
│                                    │                       │
│                                    ▼                       │
│                           ┌──────────────┐                 │
│                           │  StateMachine │                │
│                           │  (FSM)        │                │
│                           └──────┬───────┘                 │
│                                  ▼                         │
│                          SQLite / Postgres                  │
│                                                            │
│  MCP Server ──► FastAPI Webhook ──► IntentEngine           │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## 🏗️ Project Structure

### Kernel Module (Orchestration Core)
- **orchestrator/main.py**: MCPHub entry point & healing loop.
- **orchestrator/intent_engine.py**: 5-agent pipeline coordinator.
- **orchestrator/stateflow.py**: Thread-safe FSM with Prime Directive states.
- **orchestrator/storage.py**: DB persistence layer (SQLAlchemy).
- **orchestrator/webhook.py**: FastAPI ingress endpoints.

### Agent Swarm
- **Managing Agent**: High-level task assignment.
- **Orchestration Agent**: Workflow coordination.
- **Architecture Agent**: System design decisions.
- **Coder Agent**: Code generation.
- **Tester Agent**: Quality assurance.
- **PINN Agent**: Physics-informed neural network arbitration.

### Data Contracts & Models
- **schemas/agent_artifacts.py**: MCPArtifact contracts.
- **schemas/database.py**: SQLAlchemy ORM models.
- **schemas/project_plan.py**: Planning contracts.
- **schemas/world_model.py**: World state models.

## 🚀 Quick Start

### Environment Setup
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# Unix
source .venv/bin/activate

pip install -r requirements.txt
```

### Run MCP Server
```bash
python mcp_server.py
```

### Start Webhook Server
```bash
uvicorn orchestrator.webhook:app --reload --port 8000
```

### Run Tests
```bash
pytest tests/ -v
```

## 🔐 Security & Integrity

- **OIDC Authentication**: GitHub OpenID Connect provider integration.
- **Knowledge Store Protection**: Cryptographic binding of training data.
- **Artifact Provenance**: Complete audit trail with OIDC claims.

## 📄 License

See [LICENSE](LICENSE).

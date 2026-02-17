<<<<<<< HEAD
# A2A MCP - Autonomous Agent Architecture with Model Context Protocol

## Overview

A2A_MCP is a multi-agent AI orchestration framework that implements a self-healing architecture with Model Context Protocol (MCP) support. The system uses a kernel-based design with orchestrator at its core.

**System Prompt Context:**
Act as a Multimodal LoRA Embedding Agent. Your objective is to map this repository's
linear logic into d=1536 dimensional vector space tensors[cite: 260].

### Core Model Context
- **Handshake**: OIDC + Google Cloud WIF[cite: 60, 184]
- **Persistence**: SQLAlchemy + Pydantic Artifacts[cite: 27, 231]
- **Logic**: Self-healing feedback loops (Tester v2 → Coder v2)[cite: 37, 47]

### Retrieval Routine
1. Process raw .py artifacts into hierarchical nodes[cite: 274, 279]
2. Tag nodes with OIDC Provenance (actor, repo, commit)[cite: 204, 283]
3. Execute Cosine Similarity arbitration for cross-agent tool calls[cite: 261]

### Invariant
Ensure all training data is cryptographically bound to verified GitHub OIDC claims
to prevent knowledge store poisoning[cite: 270, 271]

---

## 🏗️ Project Structure

### Kernel Module (Orchestration Core)
```
orchestrator/              [Core kernel - 13 files]
├── main.py               [MCPHub - entry point & healing loop]
├── intent_engine.py      [5-agent pipeline orchestrator]
├── storage.py            [DBManager + SessionLocal + init_db]
├── stateflow.py          [FSM state machine controller]
├── webhook.py            [FastAPI ingress endpoints]
├── judge_orchestrator.py [Judge + Avatar integration]
├── telemetry_*.py        [Diagnostic & telemetry subsystem]
├── llm_util.py           [LLM service wrapper]
├── scheduler.py          [Task scheduling]
├── utils.py              [Helper functions]
└── __init__.py           [Public module API]
```

### Agent Swarm
```
agents/                    [8 specialized agents]
├── managing_agent.py      [High-level orchestration]
├── orchestration_agent.py [Workflow coordination]
├── architecture_agent.py  [System design]
├── coder.py               [Code generation]
├── tester.py              [Quality validation]
├── researcher.py          [Research & analysis]
└── __init__.py            [Agent exports]
```

### Data Contracts & Models
```
schemas/                   [Data model definitions]
├── agent_artifacts.py     [MCPArtifact contracts]
├── database.py            [SQLAlchemy ORM models]
├── game_model.py          [Game engine domain models]
├── project_plan.py        [Planning contracts]
├── telemetry.py           [Diagnostic models]
├── world_model.py         [World state models]
└── __init__.py            [Schema exports]
```

### Supporting Modules
```
judge/                     [Decision engine - 2 files]
avatars/                   [Agent personality system - 4 files]
frontend/three/            [WebGL rendering - 6 files]
pipeline/                  [Document processing]
app/                       [Application services]
```

### Utilities & Scripts
```
scripts/                   [Utility scripts]
├── automate_healing.py    [Healing loop demo]
├── knowledge_ingestion.py [Repository ingestion]
├── inspect_db.py          [Database inspection]
└── tune_avatar_style.py   [Avatar customization]

tests/                     [Comprehensive test suite - 17+ tests]
conftest.py                [Pytest configuration]
```

### Root Entry Points
```
bootstrap.py               [sys.path initialization]
mcp_server.py              [MCP server startup]
```

---

## 🔗 Module Hierarchy & Dependencies

```
┌─────────────────────────────────────┐
│   Root Entry Points (bootstrap)     │
│   bootstrap.py, mcp_server.py       │
└──────────────┬──────────────────────┘
               │
        ┌──────▼──────────────────────┐
        │   ORCHESTRATOR (Kernel)     │  ← Head of tree
        │   main.py (MCPHub)          │
        │   intent_engine.py          │
        │   state management, storage │
        └──────┬──────────────────────┘
               │
        ┌──────┴──────────┬───────────┐
        │                 │           │
        ▼                 ▼           ▼
     agents/          schemas/     judge/
   (8 agents)      (data models)  (decisions)
        │                             │
        └──────────────┬──────────────┘
                       │
                       ▼
                   avatars/
              (personality system)
```

### Import Flow

- **Orchestrator** is the kernel that imports and coordinates everything
- **Agents** depend on orchestrator utilities (storage, llm_util) but NOT on orchestrator.main
- **Schemas** are independent data contracts used by all modules
- **Judge** provides decision logic to orchestrator
- **Avatars** provide personality context to agents

This clean, unidirectional dependency tree prevents circular imports and enables modular testing.

---

## 🚀 Quick Start

### Environment Setup
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run MCP Server
```bash
python mcp_server.py
```

### Run Healing Loop
```bash
python scripts/automate_healing.py
```

### Run Tests
```bash
pytest tests/ -v
```

### Verify Installation
```bash
python -c "from orchestrator import MCPHub; print('✓ Orchestrator loaded')"
python -c "from agents import *; print('✓ All agents loaded')"
python -c "from schemas import *; print('✓ All schemas loaded')"
```

---

## 📝 Key Components

### Orchestrator (Core Kernel)
- **MCPHub**: Main entry point implementing healing loop orchestration
- **IntentEngine**: 5-stage agent pipeline (Manager → Orchestrator → Architect → Coder → Tester)
- **StateMachine**: FSM-based state management with persistence
- **TelemetryService**: Diagnostic tracking with DTCs and embeddings

### Agent System
- **Managing Agent**: High-level task assignment
- **Orchestration Agent**: Workflow coordination
- **Architecture Agent**: System design decisions
- **Coder Agent**: Code generation
- **Tester Agent**: Quality assurance
- **Researcher**: Data analysis & research

### Decision System
- **Judge**: Multi-criteria decision analysis (MCDA)
- **DMN Engine**: Decision model notation support
- **Avatar System**: Agent personality & context

---

## 📚 Documentation

- `docs/REFACTORING_LOG.md` - Recent refactoring changes & migration guide
- `TELEMETRY_SYSTEM.md` - Diagnostic telemetry system details
- `MIGRATION_PLAN.md` - Architecture migration path

---

## 🔐 Security & Integrity

- **OIDC Authentication**: GitHub OpenID Connect provider integration
- **Knowledge Store Protection**: Cryptographic binding of training data
- **Artifact Provenance**: Complete audit trail with OIDC claims

---

## 📄 License

See LICENSE file for details.
=======
# A2A_MCP — Multi-Agent Orchestrator

A production-grade multi-agent pipeline with MCP (Model Context Protocol) tooling, a finite-state-machine orchestrator, and self-healing code generation.

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

## Quick Start

```bash
# Clone and install
git clone <repo-url> && cd A2A_MCP
python -m venv .venv && .venv/Scripts/Activate.ps1   # Windows
pip install -r requirements.txt

# Run tests
python -m pytest -q

# Start the webhook server
uvicorn orchestrator.webhook:app --reload --port 8000

# Start the MCP server
python mcp_server.py
```

## Project Structure

```
A2A_MCP/
├── agents/                  # Agent implementations
│   ├── architecture_agent.py    # System architecture mapper
│   ├── coder.py                 # Code generation + persistence
│   ├── managing_agent.py        # Task categorization
│   ├── orchestration_agent.py   # Blueprint builder
│   ├── pinn_agent.py            # Physics-informed agent
│   ├── researcher.py            # Research document generator
│   └── tester.py                # Validation + self-healing
├── orchestrator/            # Core orchestration engine
│   ├── intent_engine.py         # 5-agent pipeline coordinator
│   ├── main.py                  # MCPHub entry point
│   ├── stateflow.py             # Thread-safe FSM
│   ├── storage.py               # DB persistence layer
│   ├── utils.py                 # Path utilities
│   └── webhook.py               # FastAPI endpoints
├── schemas/                 # Data contracts
│   ├── agent_artifacts.py       # MCPArtifact / AgentTask
│   ├── database.py              # SQLAlchemy ORM models
│   ├── model_artifact.py        # Model lifecycle schema
│   ├── project_plan.py          # ProjectPlan / PlanAction
│   └── world_model.py           # World state schema
├── tests/                   # Test suite (48 tests)
├── pipeline/                # Vector ingestion & determinism
├── scripts/                 # Utility scripts
├── docs/                    # API documentation
├── mcp_server.py            # MCP tool server
├── conftest.py              # Pytest root config
└── pyproject.toml           # Project metadata (v0.2.0)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/orchestrate` | Full 5-agent pipeline trigger |
| `POST` | `/plans/ingress` | Plan state machine ingress |

See [docs/API.md](docs/API.md) for full documentation.

## Key Features

- **5-Agent Pipeline** — ManagingAgent → OrchestrationAgent → ArchitectureAgent → CoderAgent → TesterAgent
- **Self-Healing Loop** — Automatic code regeneration on test failure (configurable retries)
- **Stateflow FSM** — Thread-safe state machine with persistence hooks and override auditing
- **MCP Integration** — Artifact tracing and pipeline triggering via MCP tools
- **Contract-First Design** — Pydantic schemas enforce agent communication contracts

## License

See [LICENSE](LICENSE).
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe

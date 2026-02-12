# A2A_MCP System Architecture

## 1. Repository Inventory

### Local Repositories

- **A2A_MCP** (main): Multi-agent orchestration system for code generation and testing
- **PhysicalAI-Autonomous-Vehicles** (subproject): Autonomous vehicle sensor data and ML training datasets

### GitHub Repositories

- **Primary**: [A2A_MCP](https://github.com/adaptco/A2A_MCP)
- **Dependencies**: Mistral API, MCP CLI tools

---

## 2. Core Orchestrator Architecture

### 2.1 Component Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server Layer                         │
│  (mcp_server.py - FastMCP endpoint)                        │
│  - get_artifact_trace() tool                               │
│  - trigger_new_research() tool                             │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│              Orchestrator Layer                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ IntentEngine (intent_engine.py)                        │ │
│  │ - Coordinates 5-agent pipeline execution              │ │
│  │ - run_full_pipeline(description)                       │ │
│  │ - execute_plan(plan)                                   │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ StateMachine (stateflow.py)                            │ │
│  │ - FSM with persistence hooks                          │ │
│  │ - 8 states (IDLE → EXECUTING → EVALUATING → TERM)    │ │
│  │ - Thread-safe with RLock                              │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ DBManager (storage.py)                                │ │
│  │ - Artifact CRUD operations                            │ │
│  │ - save_plan_state() for FSM snapshots                 │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Additional Services                                    │ │
│  │ - LLMService (llm_util.py): Mistral/Codestral API    │ │
│  │ - SimpleScheduler: Interval-based async jobs         │ │
│  │ - WebhookEndpoints: FastAPI /plans/ingress            │ │
│  │ - MCPHub: Self-healing loop coordinator              │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────┬────────────────┬────────────────┬─────────────────┘
           │                │                │
   ┌───────▼─────────┐ ┌───▼──────────┐ ┌────▼──────────┐
   │  Agent Swarm    │ │   Schemas    │ │   Database    │
   │                 │ │              │ │               │
   │ • Managing      │ │ • MCPArtifact│ │ • SQLAlchemy  │
   │ • Orchestration │ │ • ProjectPlan│ │ • Models:     │
   │ • Architecture  │ │ • ModelArtif │ │   - Artifact  │
   │ • Coder         │ │ • WorldModel │ │   - PlanState │
   │ • Tester        │ │ • Database   │ │               │
   │ • Researcher    │ │             │ │               │
   │ • PINN          │ │             │ │               │
   └─────────────────┘ └─────────────┘ └───────────────┘
           │                │                │
           └────────────────┴────────────────┘
                  │
         ┌────────▼──────────────┐
         │   External Services   │
         │                       │
         │ • Mistral/Codestral   │
         │   (LLM API)           │
         │ • SQLite/PostgreSQL   │
         │   (Database)          │
         │ • Redis (optional)    │
         │   (Queue)             │
         └───────────────────────┘
```

### 2.2 Orchestrator Files

| File | Purpose | Key Classes/Functions |
| --- | --- | --- |
| **intent_engine.py** | Pipeline coordinator | `IntentEngine`, `PipelineResult` |
| **stateflow.py** | Finite state machine | `StateMachine`, `State`, `TransitionRecord` |
| **storage.py** | Database manager | `DBManager`, `save_plan_state()`, `load_plan_state()` |
| **llm_util.py** | LLM integration | `LLMService.call_llm()` |
| **webhook.py** | Plan ingress endpoint | `plan_ingress()` endpoint |
| **main.py** | Self-healing loop | `MCPHub.run_healing_loop()` |
| **scheduler.py** | Async job scheduler | `SimpleScheduler` |
| **database_utils.py** | Legacy DB setup | `SessionLocal` (deprecated) |
| **utils** | Path utilities | `extract_plan_id_from_path()` |

---

## 3. Integration Points & Data Flows

### 3.1 Full 5-Agent Pipeline (run_full_pipeline)

**Source**: `orchestrator/intent_engine.py:54-136`

```text
User Description
    ↓
IntentEngine.run_full_pipeline()
    ├── Stage 1: ManagingAgent.categorize_project()
    │   OUTPUT: ProjectPlan with PlanAction items
    │
    ├── Stage 2: OrchestrationAgent.build_blueprint()
    │   INPUT: ProjectPlan
    │   OUTPUT: Blueprint with delegation metadata
    │
    ├── Stage 3: ArchitectureAgent.map_system()
    │   INPUT: Blueprint
    │   OUTPUT: Architecture artifacts, VectorTokens → WorldModel
    │
    └── Stage 4-5: Self-Healing Loop (per action)
        ├── CoderAgent.generate_solution()
        │   INPUT: Parent context, feedback
        │   OUTPUT: Code MCPArtifact
        │   PERSIST: DBManager.save_artifact()
        │
        └── Loop until PASS (max 3 retries):
            └── TesterAgent.validate()
                INPUT: Artifact ID
                OUTPUT: TestReport (status, critique)
                ├── IF status == "PASS": COMPLETE action
                └── ELSE: Feedback → CoderAgent (retry)

FINAL OUTPUT: PipelineResult
    - plan: User's categorized project
    - blueprint: Orchestrated blueprint
    - architecture_artifacts: System design artifacts
    - code_artifacts: Generated code
    - test_verdicts: Test results
    - success: bool (all actions completed)
```

### 3.2 State Machine Transitions

**Source**: `orchestrator/stateflow.py:85-107`

```text
IDLE
  ↓ OBJECTIVE_INGRESS
SCHEDULED
  ↓ RUN_DISPATCHED
EXECUTING ←→ REPAIR
  ↓            ↓
EVALUATING    REPAIR_COMPLETE
  ├─VERDICT_PASS──→ TERMINATED_SUCCESS
  ├─VERDICT_FAIL──→ TERMINATED_FAIL
  └─VERDICT_PARTIAL → RETRY
              ↑
         RETRY_DISPATCHED
              (or RETRY_LIMIT_EXCEEDED → TERMINATED_FAIL)
```

### 3.3 Database Persistence

**Source**: `orchestrator/storage.py`

```text
save_artifact(MCPArtifact):
    ├── Extract: artifact_id, type, content, metadata
    ├── Create: ArtifactModel row
    └── Persist: SQLAlchemy session

save_plan_state(plan_id, snapshot):
    ├── Serialize: FSM state → JSON
    ├── Find/Create: PlanStateModel row
    └── Persist: SQLAlchemy session

load_plan_state(plan_id):
    ├── Query: PlanStateModel by plan_id
    └── Deserialize: JSON → FSM state dict
```

---

## 4. Key Source File Locations

### Orchestrator Core

- **Main Coordinator**: `orchestrator/intent_engine.py:39-49` (IntentEngine.__init__)
- **Pipeline Execution**: `orchestrator/intent_engine.py:54-136` (run_full_pipeline)
- **State Machine**: `orchestrator/stateflow.py:64-229` (StateMachine class)
- **DB Persistence**: `orchestrator/storage.py:11-74` (DBManager + functions)
- **LLM Service**: `orchestrator/llm_util.py:7-34` (LLMService.call_llm)
- **Webhook Ingress**: `orchestrator/webhook.py:11-37` (plan_ingress endpoint)

### Data Models

- **Artifacts**: `schemas/agent_artifacts.py`
- **Plans**: `schemas/project_plan.py`
- **Database**: `schemas/database.py` (SQLAlchemy models)
- **World Model**: `schemas/world_model.py`

### Agents

- **Managing**: `agents/managing_agent.py`
- **Orchestration**: `agents/orchestration_agent.py`
- **Architecture**: `agents/architecture_agent.py`
- **Coder**: `agents/coder.py`
- **Tester**: `agents/tester.py`

### MCP Server

- **FastMCP Tools**: `mcp_server.py:8-25`

---

## 5. Known Issues & Cleanup Tasks

### Issue #1: Redundant Database Utils

**Location**: `orchestrator/database_utils.py`

**Problem**: Duplicates `DBManager` functionality from `storage.py`

**Impact**: `mcp_server.py` imports `SessionLocal` from here instead of using `DBManager`

**Fix**: Consolidate to use `storage.DBManager` in `mcp_server.py`

### Issue #2: Incomplete FastAPI Initialization

**Location**: `orchestrator/webhook.py:6`

**Problem**: `app = FastAPI(...)` uses placeholder `...`

**Impact**: Invalid Python syntax, should be proper initialization

**Fix**: Replace with `app = FastAPI(title="A2A Plan Orchestrator")`

### Issue #3: Redundant Import

**Location**: `orchestrator/webhook.py:31`

**Problem**: `StateMachine` imported twice (lines 3 and 31)

**Impact**: Code smell, inefficient

**Fix**: Remove the import at line 31

### Issue #4: Missing Type Hints

**Location**: `orchestrator/storage.py:19-43`

**Problem**: `save_artifact()` and `get_artifact()` methods lack type hints

**Impact**: Reduced IDE support and documentation

**Fix**: Add return types and parameter types

### Issue #5: Global Eager Singleton

**Location**: `orchestrator/storage.py:46`

**Problem**: `_db_manager = DBManager()` instantiates immediately

**Impact**: Database connection created at import time (inefficient)

**Fix**: Use lazy initialization or factory pattern

### Issue #6: In-Memory FSM State in Webhook

**Location**: `orchestrator/webhook.py:9`

**Problem**: `PLAN_STATE_MACHINES = {}` is not persisted

**Impact**: FSM state lost on restart, violates stateful requirements

**Fix**: Add persistence callback using `storage.save_plan_state()`

---

## 6. Integration Checklist

- [x] `mcp_server.py` uses `storage.DBManager` instead of `database_utils`
- [x] `webhook.py` has proper FastAPI initialization
- [x] No duplicate imports in `webhook.py`
- [x] Type hints added to `storage.py` methods
- [x] FSM state machine in webhook persists via callback
- [ ] All agents properly initialized with `LLMService` and `DBManager`
- [ ] Database tables (`artifacts`, `plan_states`) created on startup
- [ ] Tests pass for orchestrator layer

---

## 7. Configuration

### Environment Variables

Create a `.env` file with:

```text
DATABASE_URL=sqlite:///./a2a_mcp.db
LLM_API_KEY=<your-mistral-key>
LLM_ENDPOINT=https://api.mistral.ai/v1/chat/completions
```

### FastMCP Config

Create `mcp_config.json`:

```json
{
  "mcpServers": {
    "A2A_Orchestrator": {
      "command": "python mcp_server.py"
    }
  }
}
```

---

## 8. Testing Strategy

- **Unit Tests**: Test individual components (StateMachine transitions, LLMService)
- **Integration Tests**: Test end-to-end pipeline with mock LLM
- **Persistence Tests**: Verify artifact and plan state CRUD operations
- **FSM Tests**: Validate all state transitions and error handling

---

## 9. Deployment Considerations

1. **Database**: Supports both SQLite (dev) and PostgreSQL (prod)
2. **Scalability**: Thread-safe FSM allows concurrent plan executions
3. **Observability**: FSM history (TransitionRecord) provides audit trail
4. **Resilience**: Self-healing loop with configurable retry mechanism
5. **Extensibility**: Agent swarm can be extended with new agent types

---

Generated: 2026-02-11


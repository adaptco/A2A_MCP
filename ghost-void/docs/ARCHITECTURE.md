# A2A MCP System Architecture

## 1. Repository Inventory

### Local Repositories

- **A2A_MCP** (main): Multi-agent orchestration system for code generation and
  testing.
- **PhysicalAI-Autonomous-Vehicles** (subproject): Autonomous vehicle sensor
  data and ML training datasets.

### GitHub Repositories

- **Primary**: [A2A_MCP](https://github.com/adaptco/A2A_MCP)
- **Dependencies**: Mistral API, MCP CLI tools

## 2. Core Orchestrator Architecture

### 2.1 Component Overview

```text
MCP Server Layer (mcp_server.py)
- get_artifact_trace()
- trigger_new_research()
            |
            v
Orchestrator Layer
- IntentEngine (intent_engine.py)
  - run_full_pipeline(description)
  - execute_plan(plan)
- StateMachine (stateflow.py)
  - 8 states with persistence hooks
  - thread-safe with RLock
- DBManager (storage.py)
  - artifact CRUD
  - save_plan_state()
- Additional Services
  - LLMService (llm_util.py)
  - SimpleScheduler
  - Webhook endpoints
  - MCPHub healing loop
            |
            v
Shared Components
- Agent Swarm
- Schemas
- Database Models
            |
            v
External Services
- Mistral/Codestral
- SQLite/PostgreSQL
- Redis (optional)
```

### 2.2 Orchestrator Files

| File | Purpose | Key Classes and Functions |
| --- | --- | --- |
| `intent_engine.py` | Pipeline coordinator | `IntentEngine`, `PipelineResult` |
| `stateflow.py` | Finite state machine | `StateMachine`, `State`, `TransitionRecord` |
| `storage.py` | Database manager | `DBManager`, `save_plan_state()`, `load_plan_state()` |
| `llm_util.py` | LLM integration | `LLMService.call_llm()` |
| `webhook.py` | Plan ingress endpoint | `plan_ingress()` |
| `main.py` | Self-healing loop | `MCPHub.run_healing_loop()` |
| `scheduler.py` | Async job scheduler | `SimpleScheduler` |
| `database_utils.py` | Legacy DB setup | `SessionLocal` (deprecated) |
| `utils` | Path utilities | `extract_plan_id_from_path()` |

## 3. Integration Points and Data Flows

### 3.1 Full 5-Agent Pipeline (`run_full_pipeline`)

Source: `orchestrator/intent_engine.py`

```text
User Description
  -> IntentEngine.run_full_pipeline()
    -> Stage 1: ManagingAgent.categorize_project()
    -> Stage 2: OrchestrationAgent.build_blueprint()
    -> Stage 3: ArchitectureAgent.map_system()
    -> Stage 4-5: Self-healing loop per action
       -> CoderAgent.generate_solution()
       -> TesterAgent.validate()
       -> PASS: complete action
       -> FAIL: feedback to CoderAgent (max 3 retries)

Output: PipelineResult
- plan
- blueprint
- architecture_artifacts
- code_artifacts
- test_verdicts
- success
```

### 3.2 State Machine Transitions

Source: `orchestrator/stateflow.py`

```text
IDLE
  -> OBJECTIVE_INGRESS
SCHEDULED
  -> RUN_DISPATCHED
EXECUTING <-> REPAIR
  -> EVALUATING
EVALUATING
  -> VERDICT_PASS -> TERMINATED_SUCCESS
  -> VERDICT_FAIL -> TERMINATED_FAIL
  -> VERDICT_PARTIAL -> RETRY -> RETRY_DISPATCHED
  -> RETRY_LIMIT_EXCEEDED -> TERMINATED_FAIL
```

### 3.3 Database Persistence

Source: `orchestrator/storage.py`

```text
save_artifact(MCPArtifact)
- extract fields
- create ArtifactModel row
- persist via SQLAlchemy session

save_plan_state(plan_id, snapshot)
- serialize FSM snapshot to JSON
- create/update PlanStateModel row
- persist via SQLAlchemy session

load_plan_state(plan_id)
- query PlanStateModel by plan_id
- deserialize JSON to FSM state dict
```

## 4. Key Source File Locations

### Orchestrator Core

- Main coordinator: `orchestrator/intent_engine.py`
- Pipeline execution: `orchestrator/intent_engine.py`
- State machine: `orchestrator/stateflow.py`
- DB persistence: `orchestrator/storage.py`
- LLM service: `orchestrator/llm_util.py`
- Webhook ingress: `orchestrator/webhook.py`

### Data Models

- Artifacts: `schemas/agent_artifacts.py`
- Plans: `schemas/project_plan.py`
- Database: `schemas/database.py`
- World model: `schemas/world_model.py`

### Agents

- Managing: `agents/managing_agent.py`
- Orchestration: `agents/orchestration_agent.py`
- Architecture: `agents/architecture_agent.py`
- Coder: `agents/coder.py`
- Tester: `agents/tester.py`

### MCP Server

- FastMCP tools: `mcp_server.py`

## 5. Known Issues and Cleanup Tasks

### Issue 1: Redundant Database Utils

- Location: `orchestrator/database_utils.py`
- Problem: Duplicates `DBManager` functionality from `storage.py`.
- Impact: `mcp_server.py` imports `SessionLocal` from legacy module.
- Fix: Consolidate around `storage.DBManager`.

### Issue 2: Incomplete FastAPI Initialization

- Location: `orchestrator/webhook.py`
- Problem: `app = FastAPI(...)` placeholder.
- Impact: Invalid Python syntax.
- Fix: Use `app = FastAPI(title="A2A Plan Orchestrator")`.

### Issue 3: Redundant Import

- Location: `orchestrator/webhook.py`
- Problem: `StateMachine` imported twice.
- Impact: Code smell.
- Fix: Keep a single import.

### Issue 4: Missing Type Hints

- Location: `orchestrator/storage.py`
- Problem: Missing method type hints.
- Impact: Reduced IDE and static-analysis quality.
- Fix: Add return and parameter types.

### Issue 5: Global Eager Singleton

- Location: `orchestrator/storage.py`
- Problem: Eager `_db_manager = DBManager()` at import time.
- Impact: Unnecessary database setup on import.
- Fix: Lazy initialization or factory.

### Issue 6: In-Memory FSM State in Webhook

- Location: `orchestrator/webhook.py`
- Problem: `PLAN_STATE_MACHINES = {}` is in-memory only.
- Impact: State loss on restart.
- Fix: Persist callbacks via `storage.save_plan_state()`.

## 6. Integration Checklist

- [x] `mcp_server.py` uses `storage.DBManager` instead of `database_utils`
- [x] `webhook.py` has proper FastAPI initialization
- [x] No duplicate imports in `webhook.py`
- [x] Type hints added in `storage.py`
- [x] Webhook FSM persistence callback wired
- [ ] Agents initialized consistently with `LLMService` and `DBManager`
- [ ] Database tables created on startup
- [ ] Orchestrator tests pass

## 7. Configuration

### Environment Variables

Create `.env`:

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

## 8. Testing Strategy

- Unit tests: State machine transitions, LLM service, utility functions.
- Integration tests: End-to-end pipeline with mocked LLM service.
- Persistence tests: Artifact and plan-state CRUD behavior.
- FSM tests: Transition coverage and error paths.

## 9. Deployment Considerations

1. Database: SQLite for development, PostgreSQL for production.
2. Scalability: Thread-safe FSM for concurrent plan execution.
3. Observability: Transition history for auditability.
4. Resilience: Self-healing loop with bounded retries.
5. Extensibility: Add new agents without changing pipeline contract.

Generated: 2026-02-11

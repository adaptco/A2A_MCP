# 🧵 Agentic Core Skills as Database of Repos: Architecture Weave

## The Thread Architecture: "Digital Weave"

This document maps the **Agentic Core Skills Database** — where specialized agent repositories are embedded as **scripted tools** operating within a unified orchestration fabric.

---

## 🎯 The Core Pattern: Skill as Embedded Repository

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION CORE (Intent Engine)           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │         REPO-EMBEDDED SKILL SWARM (8 Specialized Agents)   ││
│  │                                                              ││
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐ ││
│  │  │ managing_agent  │  │orchestration    │  │ architect  │ ││
│  │  │ (Task Parsing)  │  │_agent (Routing) │  │(System Map)│ ││
│  │  └─────────────────┘  └─────────────────┘  └────────────┘ ││
│  │                                                              ││
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐ ││
│  │  │  coder.py      │  │  tester.py      │  │researcher  │ ││
│  │  │(Code Generate) │  │ (Validation)    │  │ (Analysis) │ ││
│  │  └─────────────────┘  └─────────────────┘  └────────────┘ ││
│  │                                                              ││
│  │  ┌──────────────────────────┐  ┌─────────────────┐        ││
│  │  │  trained_model_agent     │  │  pinn_agent     │        ││
│  │  │ (ML Model Inference)     │  │ (Physics Engine)│        ││
│  │  └──────────────────────────┘  └─────────────────┘        ││
│  │                                                              ││
│  └────────────────────────────────┬──────────────────────────┘│
│                                    │                           │
│  ┌────────────────────────────────▼──────────────────────────┐│
│  │          PERSISTENCE & STATE LAYER (Database)            ││
│  │  • ArtifactModel (code, tests, docs)                      ││
│  │  • PlanStateModel (task state snapshots)                  ││
│  │  • TelemetryEventModel (execution tracking)               ││
│  │  • DiagnosticReportModel (system health)                  ││
│  └─────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │    PERSONALITY & EVALUATION LAYER (Judge + Avatar)    │ │
│  │  • AvatarRegistry: 8 Agent Bindings                   │ │
│  │  • JudgeOrchestrator: MCDA Scoring [0.0, 1.0]       │ │
│  │  • Criteria: Safety, Spec Alignment, Intent, Latency│ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Layer 1: THE SKILL REPOSITORY SWARM (agents/)

Each agent is a **specialized embedded repository** with its own execution contract:

### **1. ManagingAgent** (Task Decomposition Skill)
- **Location**: `agents/managing_agent.py`
- **Function**: Intent decomposition engine
- **Input**: Free-text project description
- **Output**: `ProjectPlan` with discrete `PlanAction` items
- **Embedded Database Role**: Reads from LLM, writes `categorisation` artifacts

### **2. OrchestrationAgent** (Workflow Routing Skill)
- **Location**: `agents/orchestration_agent.py`
- **Function**: Task-to-agent mapping
- **Input**: Task list with descriptions
- **Output**: `ProjectPlan` (blueprint) with routed actions
- **Embedded Database Role**: Coordinates downstream tasks

### **3. ArchitectureAgent** (System Design Skill)
- **Location**: `agents/architecture_agent.py`
- **Function**: System decomposition and component mapping
- **Input**: `ProjectPlan` (blueprint from Orchestrator)
- **Output**: Architecture artifacts (component specs, dependency graphs)
- **Embedded Database Role**: Persists system design docs

### **4. CoderAgent** (Code Generation Skill)
- **Location**: `agents/coder.py`
- **Function**: Solution code generation with self-healing
- **Input**: Parent context + feedback
- **Output**: `MCPArtifact` (type: `code_solution`)
- **Embedded Database Role**: Fetches parent context from DB, saves generated code

### **5. TesterAgent** (Validation Skill)
- **Location**: `agents/tester.py`
- **Function**: Quality assurance and test verdict generation
- **Input**: Artifact ID
- **Output**: Test report with `status` and `critique`
- **Embedded Database Role**: Validates artifacts, provides feedback loop

### **6. ResearcherAgent** (Analysis Skill)
- **Location**: `agents/researcher.py`
- **Function**: Research and knowledge synthesis
- **Input**: Query/context
- **Output**: Research documentation
- **Embedded Database Role**: Stores research artifacts

### **7. TrainedModelAgent** (ML Inference Skill)
- **Location**: `agents/trained_model_agent.py`
- **Function**: Machine learning model invocation
- **Input**: Inference payload
- **Output**: Model predictions
- **Embedded Database Role**: Tracks ML execution telemetry

### **8. PINNAgent** (Physics-Informed Skill)
- **Location**: `agents/pinn_agent.py`
- **Function**: Physics-informed neural network operations
- **Input**: Physical domain parameters
- **Output**: Physics-validated solutions
- **Embedded Database Role**: Stores physics computation artifacts

---

## 🗄️ Layer 2: SKILL EXECUTION DATABASE (schemas/ + orchestrator/storage.py)

The database **IS** the skill registry and execution state:

### **ArtifactModel** (Core Skill Output Units)
```python
id: String (UUID)              # Globally unique skill output
parent_artifact_id: String     # Skill dependency chain
agent_name: String             # Which agent (skill) created this
type: String                   # 'code', 'test_report', 'architecture', etc.
content: Text                  # The actual skill output
created_at: DateTime           # Execution timestamp
```

**This IS the "Skill Output Repository"** — each row = a skill invocation with its result.

### **PlanStateModel** (Skill Orchestration State)
```python
plan_id: String                # Workflow identifier
snapshot: JSON                 # Full state of all active skills
created_at: DateTime           # State capture time
updated_at: DateTime           # Last skill execution update
```

### **TelemetryEventModel** (Skill Execution Metrics)
```python
event_id: String
component: String              # Which agent/skill
event_type: String             # 'execution_start', 'execution_end'
artifact_id: String            # Which output artifact
input_embedding: JSON          # Vector representation
output_embedding: JSON         # Result embedding
embedding_distance: Float      # Quality delta
duration_ms: Float             # Execution latency
```

**This IS the "Skill Performance Repository"** — tracks quality and latency per skill.

### **DiagnosticReportModel** (Skill Health Assessment)
```python
report_id: String
execution_phase: String        # Which skill detected issues
detected_dtcs: JSON           # Diagnostic Trouble Codes
embedding_trajectory: JSON    # Skill output vector evolution
recommendations: JSON         # How to heal skill failures
```

---

## 🔀 Layer 3: ORCHESTRATION KERNEL (orchestrator/)

### **IntentEngine** (Skill Conductor)
- **File**: `orchestrator/intent_engine.py`
- **Pattern**: Dataflow orchestrator
- **Skill Sequence**:
  ```
  input → ManagingAgent (parse)
        → OrchestrationAgent (route)
        → ArchitectureAgent (design)
        → CoderAgent (generate)
        → TesterAgent (validate)
        ↓
  [Loop on failure] → CoderAgent again
  ```

### **DBManager** (Skill Persistence)
- **File**: `orchestrator/storage.py`
- **Methods**:
  - `save_artifact()` — Register new skill output
  - `get_artifact()` — Retrieve skill context for chaining
  - `save_plan_state()` — Snapshot all active skills
  - `load_plan_state()` — Resume interrupted workflows

### **LLMService** (Skill Prompting Engine)
- **File**: `orchestrator/llm_util.py`
- **Role**: Translates skill intent into LLM calls
- **Method**: `call_llm(prompt)` — Common interface for all agents

### **JudgeOrchestrator** (Skill Evaluation)
- **File**: `orchestrator/judge_orchestrator.py`
- **Role**: Multi-criteria decision analysis for skill outputs
- **Scoring**: `[0.0, 1.0]` per skill output across 4 criteria:
  - **Safety** (weight: 1.0) — Does skill output contain errors?
  - **Spec Alignment** (weight: 0.8) — Does output match requirements?
  - **Intent** (weight: 0.7) — Does output serve user's goal?
  - **Latency** (weight: 0.5) — Was skill execution fast enough?

---

## 👥 Layer 4: PERSONALITY & CONTEXT LAYER (avatars/ + judge/)

### **Avatar System** — Skill Personality Binding
- **File**: `avatars/registry.py` (AvatarRegistry singleton)
- **Pattern**: Each skill (agent) is bound to an avatar:
  ```
  ManagingAgent       → Avatar("Manager", role="Engineer")
  OrchestrationAgent  → Avatar("Conductor", role="Engineer")
  ArchitectureAgent   → Avatar("Architect", role="Designer")
  CoderAgent          → Avatar("Coder", role="Engineer")
  TesterAgent         → Avatar("Tester", role="Engineer")
  ResearcherAgent     → Avatar("Researcher", role="Designer")
  TrainedModelAgent   → Avatar("Model", role="Engineer")
  PINNAgent           → Avatar("Physicist", role="Engineer")
  ```

### **Judge Decision System** — Skill Output Evaluation
- **File**: `judge/decision.py` (JudgmentModel)
- **Weights Loaded From**: `specs/judge_criteria.yaml`
- **Integration**: Judge scores each skill output, orchestrator routes based on score

---

## 🧬 Layer 5: DATA CONTRACTS (schemas/)

### **MCPArtifact** (Universal Skill Output Contract)
```python
artifact_id: str               # Unique skill output ID
type: str                      # Skill output type
content: str                   # Result data
timestamp: str                 # When skill executed
metadata: Dict                 # Agent name, model version, etc.
```

### **ProjectPlan + PlanAction** (Skill Workflow Contract)
```python
ProjectPlan:
  plan_id: str
  project_name: str
  actions: List[PlanAction]

PlanAction:
  action_id: str
  title: str
  instruction: str
  status: "pending" | "in_progress" | "completed" | "failed"
  validation_feedback: str     # Judge verdict on skill output
```

---

## 🔄 Execution Flow: "Weaving the Threads"

```
User Request
    ↓
IntentEngine.run_full_pipeline(description)
    ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: UNDERSTANDING                                  │
│ ManagingAgent.categorize_project(description)           │
│ → Artifacts: categorisation                             │
│ → Database: save PlanAction list                        │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: ROUTING                                        │
│ OrchestrationAgent.build_blueprint(task_list)           │
│ → Artifacts: task_routing                               │
│ → Database: update plan_states with routes              │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 3: ARCHITECTING                                  │
│ ArchitectureAgent.map_system(blueprint)                 │
│ → Artifacts: architecture_spec, component_map           │
│ → Database: save design artifacts                       │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 4: CODING (with Healing Loop)                    │
│ FOR each action in blueprint:                           │
│   CoderAgent.generate_solution(parent_id, feedback)     │
│   → Artifacts: code_solution                            │
│   → Database: save generated code with parent ref       │
│   → Judge: score output [0.0, 1.0]                      │
│                                                          │
│   TesterAgent.validate(artifact_id)                     │
│   → Artifacts: test_report                              │
│   → Database: store verdict                             │
│   → Judge: score test results                           │
│                                                          │
│   IF test fails AND retries < max:                      │
│     → Feedback → CoderAgent (healing loop)              │
└──────────────────────┬──────────────────────────────────┘
                       ↓
                   SUCCESS ✓ or ESCALATION
```

---

## 💾 The Database as Skill Registry

### Key Insight: **The Database IS the Skills Repository**

Instead of external tool registries, the A2A_MCP system uses the database itself:

```
artifacts                    TelemetryEvents         DiagnosticReports
├── Row 1: Mgr output       ├── Mgr exec time       ├── Phase findings
├── Row 2: Orch output      ├── Orch latency        ├── DTC codes
├── Row 3: Arch output      ├── Arch quality        ├── Recommendations
├── Row 4: Code output      ├── Coder rework count  └── Healing actions
├── Row 5: Test output      └── Tester pass/fail
└── Row 6: Code output (v2)
```

**Each row = a skill invocation**
**Each column = skill metadata**
**Parent refs = skill dependency chain**

---

## 📐 Skill Chaining: The Thread Connections

Skills are woven together via **artifact parent references**:

```
PlanStateModel (plan-abc123)
  ↓
  {
    "plan_id": "plan-abc123",
    "actions": [
      {
        "artifact_id": "cat-001",        # ManagingAgent output
        "status": "completed"
      },
      {
        "artifact_id": "route-002",      # OrchestrationAgent output
        "parent_id": "cat-001",          # Links to previous skill
        "status": "completed"
      },
      {
        "artifact_id": "arch-003",       # ArchitectureAgent output
        "parent_id": "route-002",        # Links to previous skill
        "status": "completed"
      },
      {
        "artifact_id": "code-004",       # CoderAgent output
        "parent_id": "arch-003",         # Links to previous skill
        "status": "in_progress"
      },
      {
        "artifact_id": "test-005",       # TesterAgent output
        "parent_id": "code-004",         # Links to previous skill
        "status": "completed",
        "verdict": "FAIL"
      }
    ]
  }
```

When **test fails**, the loop rewinds:
```
code-006 → parent: test-005 → feedback: "fix X"
```

---

## 🎬 Entry Points: Scripts as Skill Invokers

### **mcp_server.py** (MCP Protocol Gateway)
- Wraps the orchestrator in an MCP-compliant server
- Exposes skills as MCP tools

### **bootstrap.py** (Path Initialization)
- Ensures all skill modules are importable

### **orchestrator/main.py (MCPHub)** (Direct Skill Runner)
```python
hub = MCPHub()
asyncio.run(hub.run_healing_loop("Fix connection string"))
```

---

## 🧪 Configuration & Deployment

### **mcp_config.json** (Skill Server Registration)
```json
{
  "mcpServers": {
    "a2a-orchestrator": {
      "command": "python",
      "args": ["mcp_server.py"],
      "env": {
        "DATABASE_URL": "sqlite:///a2a_mcp.db"
      }
    }
  }
}
```

### **Database Initialization**
```python
from orchestrator.storage import init_db
init_db()  # Creates all skill output tables
```

---

## 🎯 Summary: The Woven Structure

| **Thread** | **Component** | **Role** |
|-----------|--------------|---------|
| **Skill Swarm** | 8 agents in `agents/` | Specialized execution units |
| **Skill State** | `artifacts` table | Output repository |
| **Skill Routing** | `intent_engine.py` | Dataflow orchestrator |
| **Skill Persistence** | `storage.py` (DBManager) | Artifact retrieval & chaining |
| **Skill Evaluation** | `judge_orchestrator.py` | Output quality scoring |
| **Skill Personality** | `avatars/` + `judge/` | Agent binding & MCDA |
| **Skill Contracts** | `schemas/` | Data model definitions |
| **Skill Healing** | Feedback loops | Automatic retry with learned fixes |

---

## 🏆 The Core Innovation

**Repos are NOT external tools. They are EMBEDDED REPOSITORIES:**

- Each agent = a specialized code repository
- Each agent output = a database row (skill invocation record)
- Each parent reference = a skill dependency link
- Each MCDA score = a skill quality metric
- Each healing loop = a skill self-correction mechanism

**The database becomes a complete audit trail of all skill invocations, failures, and improvements.**

This is the **Agentic Core Skills Database** — a unified system where specialized repositories are embedded as scripted tools operating within a managed orchestration fabric.

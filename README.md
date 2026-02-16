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
### WhatsApp Notifications (Task Completion)
Set these environment variables to enable Twilio WhatsApp alerts when agent coding tasks complete:

```bash
WHATSAPP_NOTIFICATIONS_ENABLED=true
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
WHATSAPP_FROM=whatsapp:+14155238886
WHATSAPP_TO=whatsapp:+15551234567
WHATSAPP_CHANNEL_BRIDGE_TO=whatsapp:+15551234567
```

Bootstrap those keys into `.env` automatically:

```bash
python scripts/configure_twilio_agent.py
```

The notifier is wired into `IntentEngine` and sends a summary when plan execution finishes.

### Notification App (Agent -> WhatsApp Channel Workflow)
Run the notification app:

```bash
uvicorn app.notification_app:app_notify --reload --port 8082
```

Send a request:

```bash
curl -X POST http://127.0.0.1:8082/notify/whatsapp/channel \
  -H "Content-Type: application/json" \
  -d "{\"channel_url\":\"https://whatsapp.com/channel/0029Vb6UzUH5a247SNGocW26\",\"message\":\"Build complete\"}"
```

The `NotificationAgent` currently uses bridge mode: it sends the message to `WHATSAPP_CHANNEL_BRIDGE_TO` for operator posting into the channel.

CLI option:

```bash
python scripts/send_channel_message.py --message "Build complete"
```

### Verify Installation
```bash
python -c "from orchestrator import MCPHub; print('✓ Orchestrator loaded')"
python -c "from agents import *; print('✓ All agents loaded')"
python -c "from schemas import *; print('✓ All schemas loaded')"
```

See [docs/API.md](docs/API.md) for full documentation.

## Key Features

- **5-Agent Pipeline** — ManagingAgent → OrchestrationAgent → ArchitectureAgent → CoderAgent → TesterAgent
- **Self-Healing Loop** — Automatic code regeneration on test failure (configurable retries)
- **Stateflow FSM** — Thread-safe state machine with persistence hooks and override auditing
- **MCP Integration** — Artifact tracing and pipeline triggering via MCP tools
- **Contract-First Design** — Pydantic schemas enforce agent communication contracts

## License

See [LICENSE](LICENSE).

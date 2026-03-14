# 🌌 Agentic Factory: Unified Monorepo Index

This index serves as the root map for the consolidated Agentic Factory system.

## 🤖 Core Agent Surfaces
- `agents/`: Implementation of specialized agent personas (`managing_agent.py`, `orchestration_agent.py`, `reviewer.py`).
- `rbac/`: Sovereign Role-Based Access Control and token management.
- `registry/agents/`: Canonical JSON indexes for agent cards and skills.
- `mcp_core.py`: Multi-agent Model Context Protocol core module.

## 🧵 Orchestration & Middleware
- `orchestrator/`: Runtime orchestration, release gating (`release_orchestrator.py`), and FSM persistence.
- `middleware/`: Platform-level middleware for environment integration.
- `app/`: Production API entrypoints (`server.py`, `mcp_rest_endpoint.py`).
- `schemas/`: Shared Pydantic contracts for protocol-level messaging.

## 🛠️ Skills & Capabilities
- `skills/`: Pluggable agent skills including:
  - `recursive-action-handler`: Multi-level task decomposition and routing.
  - `mcp-entropy-template-router`: Skill-token generation and template routing.
  - `avatar-mcp-root-context`: Zero-shot context building.

## 🧪 CI/CD & MLOps
- `mlops_unity_pipeline.py`: Autonomous Unity + RL training pipeline.
- `scripts/`: Unified automation and utility scripts.
- `tests/`: End-to-end and unit test suites.
- `.github/workflows/`: Hardened CI/CD pipelines.

## 🔐 Forensics & Governance
- `judge/`: LLM-driven decision logic for release gating.
- `data/events/`: Immutable append-only ledger of state transitions.
- `scripts/verification/`: Deterministic verification of frozen capsules.

## 📖 Documentation
- `AGENTS.md`: Agent personas, embedded skills, and RBAC token flow.
- `Skills.md`: Detailed catalog of available skills and execution patterns.
- `README.md`: System overview, setup, and architecture maps.

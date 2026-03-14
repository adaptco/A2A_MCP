# 🤖 Agent Catalog

This document defines the specialized agent personas available in the Agentic Factory.

## Project overview
A2A_MCP is a multi-module repository that combines agent orchestration, model governance, runtime middleware, and game/Unity-focused MLOps workflows.

Core areas include:
- `a2a_mcp/`, `orchestrator/`, and `middleware/` for runtime orchestration and messaging.
- `mlops/` and `mlops_unity_pipeline.py` for automated Unity + RL training pipelines.
- `docs/`, `specs/`, and `adk/` for architecture, release specs, and contracts/schemas.
- Mixed-language components (primarily Python with C++ engine code under `src/` and headers in `include/`).

When working in this repo, prefer minimal, targeted changes and avoid unrelated refactors.

## Frontier agent index + RBAC token flow
Generate the Frontier LLM agent index, agent cards, and per-agent RBAC tokens for MCP tool pulls with:
- `make frontier-index`
- If `make` is unavailable: `python scripts/build_frontier_agent_index.py`

Artifacts written by the command:
- `registry/agents/frontier_agent_index.v1.json`
- `registry/agents/frontier_agent_cards.v1.json`
- `runtime/rbac/frontier_rbac_tokens.local.json` (local token bundle; do not commit)

## Agent cards (roles with embedded skills)
| Agent ID | Frontier LLM | RBAC role | RBAC Token | Embedded skills | MCP tool pull scope |
| --- | --- | --- | --- | --- | --- |
| `agent:frontier.endpoint.gpt` | `endpoint / gpt-4o-mini` | `pipeline_operator` | `A2A_MCP_GPT_V1` | planning, implementation, integration, code_generation | full MCP tool scope |
| `agent:frontier.anthropic.claude` | `anthropic / claude-3-5-sonnet-latest` | `admin` | `A2A_MCP_CLAUDE_ADMIN` | governance, policy_enforcement, orchestration, release_governance | full MCP tool scope |
| `agent:frontier.vertex.gemini` | `vertex / gemini-1.5-pro` | `pipeline_operator` | `A2A_MCP_GEMINI_V1` | architecture_mapping, context_synthesis, integration | full MCP tool scope |
| `agent:frontier.ollama.llama` | `ollama / llama3.1` | `healer` | `A2A_MCP_LLAMA_HEAL` | regression_triage, self_healing, patch_synthesis, verification | healing + read-oriented MCP tools |
| `agent:frontier.reviewer` | `endpoint / gpt-4o-mini` | `observer` | `A2A_MCP_REVIEWER_V1` | code_review, security_audit, performance_analysis | full MCP tool scope |

## Build and test commands
Use the smallest command set needed for the files you touched.

```bash
# Run managing agent unit tests
pytest tests/test_coder_agent.py -v
```

### Local automation runtime (Docker compose helper)
- Start (with build): `.\scripts\automation_runtime.ps1 -Action up -Build`
- Validate prerequisites/config: `.\scripts\automation_runtime.ps1 -Action validate`
- Health check: `.\scripts\automation_runtime.ps1 -Action health`
- Stop runtime: `.\scripts\automation_runtime.ps1 -Action down`
- Prerequisite: Docker Compose plugin required; Docker Desktop running for `up`, `down`, and `health`.

### Python environment
- Install dependencies: `pip install -r requirements.txt`
- Editable install (optional): `pip install -e .`

### Python checks
- Run tests: `pytest`
- Narrow scope: `pytest <path-or-test-name>`
- Type checking: `pyright`

### C++ build (if touching engine code)
- Configure: `cmake -S . -B build`
- Build: `cmake --build build`

## Code style guidelines
- Keep modules focused; prefer small functions and explicit naming.
- Follow existing patterns in the directory you are editing; do not introduce new frameworks unless requested.
- Preserve backward compatibility for public interfaces unless the task explicitly calls for breaking changes.
- Never wrap imports in `try/except` blocks.
- Update related docs/specs when behavior, config, or public APIs change.

## Testing instructions
- Run at least one direct check for every change (unit test, targeted pytest selection, or a relevant script).
- For docs-only changes, run a lightweight sanity check (for example: `python -m py_compile <modified_python_files>` when relevant, or confirm paths/commands are valid).
- Prefer targeted tests first; run full-suite tests only when necessary.
- Include exact commands and outcomes in your PR notes.

## Security considerations
- Never commit secrets, access tokens, service-account keys, or private certificates.
- Treat model artifacts, logs, and telemetry as potentially sensitive; avoid exposing raw production data.
- Validate and sanitize external inputs in scripts that call shell commands, webhooks, or MCP/LLM endpoints.
- Minimize privileges for cloud resources and service accounts (principle of least privilege).
- Pin or review dependency versions before introducing new external packages.

## Commit and pull request guidelines
- Commit messages should be imperative and scoped (e.g., `docs: add root AGENTS.md guidance`).
- Keep commits atomic: one coherent change per commit when possible.
- PRs should include:
  - What changed.
  - Why it changed.
  - How it was validated (exact commands).
  - Any follow-up work or known limitations.

## Monorepo guidance and nested AGENTS.md
- If a subproject has unique workflows, add a nested `AGENTS.md` in that directory.
- The nearest `AGENTS.md` to a file takes precedence for that file.
- Use nested files to document package-specific build/test commands, deployment steps, and local constraints (datasets, infra dependencies, etc.).

## Full-Stack Multi-Agent Orchestration System

The A2A_MCP implements a multi-tiered agent orchestration system designed to manage complex, stateful workflows across distributed environments.

### Core Architecture
- **Orchestration Layer**: The `OrchestrationAgent` coordinates tasks, resolving dependencies and mapping sub-tasks to specialized domain agents.
- **Execution Layer**: Specialized agents (`CoderAgent`, `TesterAgent`, `ArchitectureAgent`) operate autonomously within bounded sandboxes.
- **Verification Layer**: The `PINNAgent` (Physics-Informed Neural Network Agent) acts as the deterministic verifier, enforcing invariants and RFC8785 canonicalization.

### Data Flow & State Management
 1. **Ingress**: `ManagingAgent` ingests the objective, categorizes the domain, and initializes the WorldModel state.
 2. **Decomposition**: The `OrchestrationAgent` builds an action sequence (Blueprint) stored in the context KV store.
 3. **Execution**: Target agents retrieve atomic tasks from the context broker, perform actions, and commit state deltas.
 4. **Validation**: The `TesterAgent` triggers continuous self-healing loops upon detection of failure states.
 5. **Egress**: The `PINNAgent` validates the final artifact against the strict compliance matrix before emitting the terminal event.

### Deployment & Middleware
- Communication uses the Model Context Protocol (MCP) acting as the message bus.
- State is serialized via the ADK (Agent Development Kit) schemas located in `adk/contracts/`.

### Local Skill Extensions
- `skills/mcp-entropy-template-router`: Generates API skill tokens for avatar runtime shell, computes enthalpy/entropy style temperature, and routes deterministic frontend/backend/fullstack template actions via uniform dotproduct scoring.

 <!-- avatar-engine:auto:start -->
 ## Avatar-Engine Production Pipeline

 - Use `.github/workflows/avatar-engine.yml` as the production artifact pipeline.
 - The scheduled upskill job regenerates `skills/SKILL.md`, syncs docs, and opens/updates a PR automatically.
 - Auto-merge is configured in safe mode only (`gh pr merge --auto --squash`) and depends on green required checks.
 - Secrets are consumed from GitHub Actions secrets only (not plaintext files): `AVATAR_ENGINE_AUTOMATION_PAT`.
 <!-- avatar-engine:auto:end -->

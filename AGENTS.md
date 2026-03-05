# AGENTS.md

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
| Agent ID | Frontier LLM | RBAC role | Embedded skills | MCP tool pull scope |
| --- | --- | --- | --- | --- |
| `agent:frontier.endpoint.gpt` | `endpoint / gpt-4o-mini` | `pipeline_operator` | planning, implementation, integration, code_generation | full MCP tool scope |
| `agent:frontier.anthropic.claude` | `anthropic / claude-3-5-sonnet-latest` | `admin` | governance, policy_enforcement, orchestration, release_governance | full MCP tool scope |
| `agent:frontier.vertex.gemini` | `vertex / gemini-1.5-pro` | `pipeline_operator` | architecture_mapping, context_synthesis, integration | full MCP tool scope |
| `agent:frontier.ollama.llama` | `ollama / llama3.1` | `healer` | regression_triage, self_healing, patch_synthesis, verification | healing + read-oriented MCP tools |

## Build and test commands
Use the smallest command set needed for the files you touched.

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

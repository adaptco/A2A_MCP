# AGENTS.md

## Project overview
A2A_MCP is a multi-module repository that combines agent orchestration, model governance, runtime middleware, and game/Unity-focused MLOps workflows.

Core areas include:
- `a2a_mcp/`, `orchestrator/`, and `middleware/` for runtime orchestration and messaging.
- `mlops/` and `mlops_unity_pipeline.py` for automated Unity + RL training pipelines.
- `docs/`, `specs/`, and `adk/` for architecture, release specs, and contracts/schemas.
- Mixed-language components (primarily Python with C++ engine code under `src/` and headers in `include/`).

When working in this repo, prefer minimal, targeted changes and avoid unrelated refactors.

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

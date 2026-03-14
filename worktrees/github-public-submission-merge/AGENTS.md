# AGENTS.md

This file gives coding agents a practical, repo-level playbook for working in `core-orchestrator`.

## Project overview
- `core-orchestrator` is a mixed-language monorepo (Python + Node/TypeScript + shell tooling) for orchestration, capsule/ledger workflows, schema validation, and automation utilities.
- The repository contains service code (`app/`, `src/`, `server/`, `codex_qernel/`), automation scripts (`scripts/`, root shell scripts), specs/schemas (`specs/`, `schemas/`), and tests (`tests/`).
- Treat JSON/schema and ledger-related artifacts as integrity-sensitive; prefer additive edits and preserve canonical field naming/order conventions used by existing tooling.

## Build and test commands
Run commands from the repository root unless a subproject README says otherwise.

### JavaScript/TypeScript workflows
- Install workspace dependencies: `pnpm install`
- Lint: `pnpm lint`
- Test (workspace): `pnpm test`
- Build (workspace): `pnpm build`

### Python workflows
- Install Python package + dev extras: `python -m pip install -e .[dev]`
- Run Python tests: `pytest -q`

### Targeted validation for common changes
- Schema/spec validation: `python scripts/validate_ssot.py`
- Drift/invariant checks (if touched): `python scripts/check_drift.py` and/or `python scripts/check_invariants.py`
- Ledger verification helpers: `node scripts/verify-ledger.js`

## Code style guidelines
- Follow existing style in the touched area; this is a polyglot repo, so avoid global reformatting.
- Keep changes minimal and scoped to the request; do not refactor unrelated files.
- Never add `try/catch` wrappers around imports.
- Preserve stable interfaces, file formats, and schema contracts unless the task explicitly requires a breaking change.
- Prefer descriptive names and small, testable functions over large procedural blocks.
- For JSON/YAML artifacts, keep keys and structure consistent with neighboring files and scripts that consume them.

## Testing instructions
- Run the narrowest tests that exercise your change first, then run broader checks when practical.
- If you modify Python runtime code under `app/`, `src/`, or `codex_qernel/`, run relevant `pytest` tests.
- If you modify Node/server code under `server/`, `lib/`, or JS scripts, run the related Node/Jest tests (or `pnpm test` when scope is broad).
- If you modify schemas/specs/manifests, run the relevant validator scripts and any impacted tests.
- In your final summary, report exactly what was run and whether it passed.

## Security considerations
- Never commit real secrets. Use sample/env template files (for example `.env.example`, `infra/secrets.sample.env`) for placeholders only.
- Treat keys, signatures, digests, and ledger artifacts as security-critical; do not regenerate or overwrite them unless explicitly requested.
- Avoid introducing network calls or dependency changes unless required by the task.
- Validate untrusted inputs in API/automation paths and prefer explicit schema validation already present in the repo.

## Commit and pull request guidance
- Use clear, scoped commit messages in imperative mood, e.g. `docs: add root AGENTS.md onboarding guide`.
- Include in PR description:
  - What changed
  - Why it changed
  - How it was validated (commands + outcomes)
  - Any follow-up work or known limitations
- Keep PRs focused; separate unrelated changes into different commits/PRs.

## Guidance for large monorepo areas
- Add nested `AGENTS.md` files inside subprojects that need custom instructions.
- The nearest `AGENTS.md` in the directory tree takes precedence for files under that subtree.
- Suggested candidates for nested guidance in this repo include:
  - `adaptco-core-orchestrator/`
  - `adaptco-previz/`
  - `adaptco-ssot/`
  - `qube-forensic-console/`
  - `app/`
  - `server/`
  - other areas with distinct build/test pipelines

## Available Skills
- **RBAC Management**: Microsoft Foundry role management and auditing.
- **Pickle Rick Agent**: Specialized agent for implementation planning and contextual coherence.

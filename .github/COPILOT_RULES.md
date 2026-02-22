# Copilot Contribution Rules

These guidelines apply to AI-assisted contributions in this repository. Follow them for all generated code, documentation, and tests.

## Repository awareness
- Read relevant documentation (`README.md`, `docs/`, `QA_TASKS.md`) before making changes.
- Keep changes scoped to the request; avoid drive-by refactors.
- Preserve existing patterns, naming, and file organization.

## Code quality
- Prefer small, readable functions with clear names.
- Match existing language and formatting conventions.
- Avoid introducing new dependencies without explicit justification.
- Do not introduce commented-out code or debugging artifacts.

## Testing and validation
- Run relevant tests or checks when feasible, and report results.
- If tests are not run, state the reason clearly in the PR summary.

## Security and safety
- Never hardcode secrets, tokens, or credentials.
- Avoid insecure defaults; follow least-privilege practices.
- Use safe parsing and validation for external input.

## Documentation
- Update or add documentation when behavior changes.
- Provide concise, actionable summaries in PRs.

## Licensing
- Only add code you have the right to contribute.
- Avoid copying from external sources unless license-compatible and attributed.

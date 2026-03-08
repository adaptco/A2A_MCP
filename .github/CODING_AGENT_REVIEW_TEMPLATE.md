# Coding Agent Review Template: GitHub Actions & Unit Tests

Use this template when reviewing pull requests that change CI workflows, testing setup, or test coverage.

## 1) Workflow safety and correctness
- [ ] Workflow file paths are correct (`.github/workflows/*.yml`).
- [ ] Trigger conditions (`on:`) match intent and avoid unnecessary runs.
- [ ] Permissions are least-privilege (`permissions:` minimized).
- [ ] Secrets are referenced safely and never printed in logs.
- [ ] Third-party actions are pinned to a commit SHA when feasible.
- [ ] Job dependencies (`needs:`) and conditionals (`if:`) are logically correct.

## 2) CI reliability
- [ ] Runtime versions (Python/Node/etc.) are explicit and supported.
- [ ] Dependency installation is deterministic (lockfile/pinned versions where needed).
- [ ] Caching strategy is valid and not over-broad.
- [ ] Steps fail fast on error; no silent failures.
- [ ] Artifacts and test reports are uploaded when useful.

## 3) Unit test quality
- [ ] New behavior has tests; changed behavior updates existing tests.
- [ ] Tests assert behavior, not internal implementation details.
- [ ] Edge cases and error paths are covered.
- [ ] Tests are isolated, deterministic, and avoid network/external flakiness.
- [ ] Fixtures/mocks are scoped and maintainable.

## 4) Coverage and guardrails
- [ ] CI executes the relevant unit test targets for changed modules.
- [ ] Regressions are prevented by adding/adjusting tests.
- [ ] Optional: coverage checks are enforced for critical packages.

## 5) Review output format (for coding agents)
When posting findings, use this structure:
1. **Risk summary** (high/medium/low)
2. **Findings** (file + issue + impact)
3. **Requested changes** (concrete patch-level guidance)
4. **Validation commands** (exact commands run or recommended)

## Suggested commands
```bash
pytest -q
pytest <path-or-test-name>
python -m py_compile <modified_python_files>
```

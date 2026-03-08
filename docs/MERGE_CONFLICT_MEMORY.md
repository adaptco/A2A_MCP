# Merge Conflict Memory

## Incident

Unresolved git conflict markers were present in tracked files:
- `a2a_mcp/__init__.py`
- `.github/workflows/ci.yml`
- mirrored `ghost-void/.../gate_policy.json`

This blocked imports and made CI workflow parsing invalid.

## Permanent Fix Controls

1. Added `scripts/check_merge_conflicts.py` (tracked-file scan via `git ls-files`).
2. Wired guard into `.github/workflows/ci.yml` as `merge-marker-guard`.
3. Wired guard into `scripts/pre_pr_check.ps1` and `a2a_mcp/scripts/pre_pr_check.ps1`.
4. Resolved existing markers and restored clean exports in `a2a_mcp/__init__.py`.

## Operating Rule

Before any PR merge:
1. Run `python scripts/check_merge_conflicts.py --root .`
2. Run `pwsh scripts/pre_pr_check.ps1 -SkipTests` (or full test gate)
3. If markers are found, resolve manually and re-run guard before commit.

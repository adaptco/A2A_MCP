# Pullable PR Runbook

This runbook explains why a PR may not be pullable from this environment and
how to verify/fix it with deterministic checks.

## Why PRs were not pullable here
A pullable PR requires all of the following:
1. A configured remote (usually `origin`).
2. Reachable repository endpoint.
3. Valid credentials for push/PR permissions.
4. A pushed branch with commits not already merged.

In this workspace, `git remote -v` was empty, so the branch had no push target.

## One-command preflight

```bash
scripts/pr_preflight_check.sh
```

Exit code meanings:
- `0`: Push dry-run succeeds; PR can be created.
- `2`: No remotes configured.
- `3`: `origin` unreachable (network/auth/repo URL problem).
- `4`: Push dry-run failed (permissions/auth).

## Make this branch pullable

```bash
# 1) Attach remote
git remote add origin <repo-url>

# 2) Validate remote + auth
git ls-remote --exit-code origin

# 3) Push branch
git push -u origin $(git branch --show-current)

# 4) Open PR from pushed branch (UI/CLI/integration)
```

## Recommended CI check
Add `scripts/pr_preflight_check.sh` to a release workflow as a pre-PR gate so
missing remotes/auth are caught before review cycles.

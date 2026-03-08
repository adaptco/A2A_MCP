#!/usr/bin/env bash
set -euo pipefail

printf 'PR preflight\n'

branch="$(git branch --show-current)"
head="$(git rev-parse --short HEAD)"

printf 'branch=%s\n' "$branch"
printf 'head=%s\n' "$head"

remote_count="$(git remote | wc -l | tr -d ' ')"
if [[ "$remote_count" -eq 0 ]]; then
  echo 'FAIL: no git remotes configured (expected origin).' >&2
  exit 2
fi

echo 'remotes:'
git remote -v

if ! git ls-remote --exit-code origin >/dev/null 2>&1; then
  echo 'FAIL: cannot reach origin (network/auth/repo issue).' >&2
  exit 3
fi

# Determine default branch from origin HEAD when available.
default_ref="$(git symbolic-ref --quiet refs/remotes/origin/HEAD 2>/dev/null || true)"
default_branch="${default_ref#refs/remotes/origin/}"
if [[ -z "$default_branch" || "$default_branch" == "$default_ref" ]]; then
  default_branch="main"
fi

if ! git merge-base --is-ancestor "origin/${default_branch}" HEAD 2>/dev/null; then
  echo "WARN: HEAD is not descendant of origin/${default_branch}." >&2
fi

if ! git push --dry-run origin "$branch" >/dev/null 2>&1; then
  echo 'FAIL: push dry-run failed (likely auth/permissions).' >&2
  exit 4
fi

echo 'PASS: branch is pushable; PR can be created from this environment.'

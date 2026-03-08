#!/usr/bin/env python3
"""Create/update a daily upskill PR and enable safe auto-merge."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def has_changes(cwd: Path) -> bool:
    result = run(["git", "status", "--porcelain"], cwd=cwd, check=False)
    return bool(result.stdout.strip())


def ensure_branch(branch: str, cwd: Path) -> None:
    run(["git", "checkout", "-B", branch], cwd=cwd)


def commit_changes(branch: str, cwd: Path) -> bool:
    run(["git", "add", "skills/SKILL.md", "README.md", "AGENTS.md"], cwd=cwd, check=False)
    if not has_changes(cwd):
        print("No catalog/docs changes to commit.")
        return False
    run(["git", "commit", "-m", "chore: refresh skills catalog via avatar-engine automation"], cwd=cwd)
    run(["git", "push", "-u", "origin", branch, "--force-with-lease"], cwd=cwd)
    return True


def create_or_update_pr(base_branch: str, head_branch: str, cwd: Path) -> int:
    existing = run(
        [
            "gh",
            "pr",
            "list",
            "--base",
            base_branch,
            "--head",
            head_branch,
            "--json",
            "number",
            "--jq",
            ".[0].number",
        ],
        cwd=cwd,
        check=False,
    ).stdout.strip()

    if existing:
        return int(existing)

    result = run(
        [
            "gh",
            "pr",
            "create",
            "--base",
            base_branch,
            "--head",
            head_branch,
            "--title",
            "chore: daily avatar-engine upskill sync",
            "--body",
            (
                "Automated daily upskill refresh.\n\n"
                "- Regenerated `skills/SKILL.md`\n"
                "- Refreshed agent automation docs\n"
                "- Safe auto-merge enabled when required checks are green"
            ),
        ],
        cwd=cwd,
    )
    last_line = result.stdout.strip().splitlines()[-1]
    pr_number = run(["gh", "pr", "view", last_line, "--json", "number", "--jq", ".number"], cwd=cwd).stdout.strip()
    return int(pr_number)


def enable_auto_merge(pr_number: int, cwd: Path) -> None:
    run(["gh", "pr", "merge", str(pr_number), "--auto", "--squash", "--delete-branch"], cwd=cwd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--base-branch", default="main")
    parser.add_argument("--automation-branch", default="automation/avatar-engine-upskill")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        print("GH_TOKEN/GITHUB_TOKEN is required for PR automation.", file=sys.stderr)
        return 2

    run(["git", "config", "user.name", "github-actions[bot]"], cwd=repo_root)
    run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], cwd=repo_root)

    ensure_branch(args.automation_branch, repo_root)
    committed = commit_changes(args.automation_branch, repo_root)
    if not committed:
        print("No pending changes after catalog refresh.")
        return 0

    pr_number = create_or_update_pr(args.base_branch, args.automation_branch, repo_root)
    enable_auto_merge(pr_number, repo_root)
    print(f"PR #{pr_number} is configured for auto-merge.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

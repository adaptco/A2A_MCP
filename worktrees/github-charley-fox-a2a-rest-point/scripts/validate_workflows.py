#!/usr/bin/env python3
"""Validate local GitHub Actions workflow files with repo-specific checks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


def validate_workflow(path: Path, repo_root: Path) -> list[str]:
    issues: list[str] = []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return [f"{path}: workflow must be a YAML object"]

    for key in ("name", "on", "jobs"):
        if key not in data:
            issues.append(f"{path}: missing top-level key '{key}'")

    jobs = data.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        issues.append(f"{path}: jobs must be a non-empty mapping")
        return issues

    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            issues.append(f"{path}: job '{job_name}' must be a mapping")
            continue
        if "runs-on" not in job:
            issues.append(f"{path}: job '{job_name}' missing 'runs-on'")
        steps = job.get("steps")
        if not isinstance(steps, list) or not steps:
            issues.append(f"{path}: job '{job_name}' missing steps")
            continue

        for step in steps:
            if not isinstance(step, dict):
                continue
            uses = step.get("uses")
            run = step.get("run")
            if uses:
                if "@" not in uses:
                    issues.append(f"{path}: step '{step.get('name', uses)}' must pin an action ref")
                elif uses.endswith("@master"):
                    issues.append(f"{path}: step '{step.get('name', uses)}' uses floating @master")
            if isinstance(run, str) and "test-command-here" in run:
                issues.append(f"{path}: step '{step.get('name', 'unnamed')}' contains placeholder test command")

            if uses == "docker/build-push-action@v5":
                context = step.get("with", {}).get("context")
                if isinstance(context, str):
                    resolved = (repo_root / context).resolve()
                    if not resolved.exists():
                        issues.append(f"{path}: Docker context does not exist: {context}")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "workflow_dir",
        nargs="?",
        default=".github/workflows",
        help="Directory that contains GitHub workflow YAML files",
    )
    args = parser.parse_args()

    workflow_dir = Path(args.workflow_dir).resolve()
    repo_root = workflow_dir.parent.parent
    if not workflow_dir.exists():
        print(f"Workflow directory not found: {workflow_dir}", file=sys.stderr)
        return 2

    issues: list[str] = []
    workflow_files = sorted(workflow_dir.glob("*.y*ml"))
    for path in workflow_files:
        issues.extend(validate_workflow(path, repo_root))

    if issues:
        for issue in issues:
            print(issue)
        return 1

    print(f"Validated {len(workflow_files)} workflow files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

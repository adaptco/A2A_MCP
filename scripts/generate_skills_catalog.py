#!/usr/bin/env python3
"""Generate a consolidated skills catalog for automation and review agents."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class SkillEntry:
    name: str
    description: str
    source: str
    rel_path: str


def _parse_frontmatter(skill_path: Path) -> tuple[str, str]:
    name = skill_path.parent.name
    description = ""

    lines = skill_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if not lines or lines[0].strip() != "---":
        return name, description

    frontmatter: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip().lower()] = value.strip().strip('"').strip("'")

    name = frontmatter.get("name", name)
    description = frontmatter.get("description", description)
    return name, description


def _collect_skills(repo_root: Path, roots: list[str]) -> list[SkillEntry]:
    entries: list[SkillEntry] = []
    for root in roots:
        root_path = (repo_root / root).resolve()
        if not root_path.exists():
            continue
        for skill_path in sorted(root_path.rglob("SKILL.md")):
            name, description = _parse_frontmatter(skill_path)
            entries.append(
                SkillEntry(
                    name=name,
                    description=description,
                    source=root,
                    rel_path=str(skill_path.relative_to(repo_root)).replace("\\", "/"),
                )
            )
    return entries


def _collect_workflows(repo_root: Path) -> list[str]:
    workflows_dir = repo_root / ".github" / "workflows"
    if not workflows_dir.exists():
        return []
    workflows: list[str] = []
    for wf in sorted(workflows_dir.glob("*.y*ml")):
        workflows.append(str(wf.relative_to(repo_root)).replace("\\", "/"))
    return workflows


def _render_markdown(entries: list[SkillEntry], workflows: list[str]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines: list[str] = [
        "---",
        "name: skills-catalog",
        "description: Consolidated skill registry generated for agent automation and CI upskill loops.",
        "---",
        "",
        "# Skills Catalog",
        "",
        f"_Generated: {now} (UTC)_",
        "",
        f"- Total skills discovered: **{len(entries)}**",
        f"- Workflow definitions discovered: **{len(workflows)}**",
        "",
        "## Skills",
        "",
        "| Name | Source Root | Path | Description |",
        "|---|---|---|---|",
    ]

    if entries:
        for entry in entries:
            desc = (entry.description or "").replace("|", "\\|")
            lines.append(
                f"| `{entry.name}` | `{entry.source}` | `{entry.rel_path}` | {desc} |"
            )
    else:
        lines.append("| _none_ | - | - | - |")

    lines.extend(
        [
            "",
            "## Workflow Surface",
            "",
        ]
    )

    if workflows:
        lines.extend([f"- `{workflow}`" for workflow in workflows])
    else:
        lines.append("- _No workflow files discovered._")

    lines.extend(
        [
            "",
            "## Review Automation Contract",
            "",
            "- Agents should scan open pull requests, collect unresolved comments/threads, and apply fixes in-order.",
            "- Merge is allowed only after required checks pass and merge conflicts are resolved.",
            "- Daily upskill runs are orchestrated by `.github/workflows/avatar-engine.yml`.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default="skills/SKILL.md")
    parser.add_argument(
        "--roots",
        nargs="+",
        default=["skills", "a2a_mcp/skills"],
        help="Skill roots to recursively scan for SKILL.md files.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_path = (repo_root / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    entries = _collect_skills(repo_root, args.roots)
    workflows = _collect_workflows(repo_root)
    rendered = _render_markdown(entries, workflows)
    output_path.write_text(rendered, encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Synchronize README and AGENTS sections for avatar-engine automation."""

from __future__ import annotations

import argparse
from pathlib import Path


START = "<!-- avatar-engine:auto:start -->"
END = "<!-- avatar-engine:auto:end -->"


README_BLOCK = """## Avatar Engine Automation

- Production pipeline: `.github/workflows/avatar-engine.yml`
- Daily recursive upskill schedule: **09:00 America/New_York** (DST-safe schedule gate)
- Catalog output refreshed by automation: `skills/SKILL.md`
- Safe merge policy: auto-merge only when required checks are green and conflict-free
"""


AGENTS_BLOCK = """## Avatar-Engine Production Pipeline

- Use `.github/workflows/avatar-engine.yml` as the production artifact pipeline.
- The scheduled upskill job regenerates `skills/SKILL.md`, syncs docs, and opens/updates a PR automatically.
- Auto-merge is configured in safe mode only (`gh pr merge --auto --squash`) and depends on green required checks.
- Secrets are consumed from GitHub Actions secrets only (not plaintext files): `AVATAR_ENGINE_AUTOMATION_PAT`.
"""


def _upsert_block(path: Path, block: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    wrapped = f"{START}\n{block.strip()}\n{END}\n"

    if START in text and END in text:
        prefix = text.split(START, 1)[0]
        suffix = text.split(END, 1)[1]
        updated = f"{prefix}{wrapped}{suffix.lstrip()}"
    else:
        updated = text.rstrip() + "\n\n" + wrapped

    path.write_text(updated, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    _upsert_block(repo_root / "README.md", README_BLOCK)
    _upsert_block(repo_root / "AGENTS.md", AGENTS_BLOCK)
    print("README.md and AGENTS.md synced for avatar-engine automation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

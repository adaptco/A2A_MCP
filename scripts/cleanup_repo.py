"""Repository cleanup and compaction helper for deployment maintenance."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Set

TEMP_PATTERNS = (
    "tmpclaude-*",
    "specs/tmpclaude-*",
)

CACHE_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

SKIP_TOP_LEVEL = {
    ".git",
    ".venv",
    "PhysicalAI-Autonomous-Vehicles",
}


@dataclass
class CleanupReport:
    root: str
    dry_run: bool
    compact: bool
    removed_paths: List[str]
    skipped_paths: List[str]
    errors: List[str]
    git_gc_exit_code: int | None = None


def _is_skipped(path: Path, root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        return True
    if not rel.parts:
        return False
    return rel.parts[0] in SKIP_TOP_LEVEL


def _collect_pattern_matches(root: Path) -> Set[Path]:
    matches: Set[Path] = set()
    for pattern in TEMP_PATTERNS:
        for path in root.glob(pattern):
            if path.exists():
                matches.add(path)
    return matches


def _collect_cache_dirs(root: Path) -> Set[Path]:
    matches: Set[Path] = set()
    for path in root.rglob("*"):
        if not path.is_dir():
            continue
        if path.name not in CACHE_DIR_NAMES:
            continue
        if _is_skipped(path, root):
            continue
        matches.add(path)
    return matches


def _remove_path(path: Path, *, dry_run: bool) -> None:
    if dry_run:
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=False)
        return
    path.unlink(missing_ok=True)


def _run_git_gc(root: Path, *, dry_run: bool) -> int | None:
    if not dry_run:
        completed = subprocess.run(
            ["git", "gc", "--prune=now"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        return completed.returncode
    return None


def _sorted_paths(paths: Iterable[Path]) -> List[Path]:
    return sorted(paths, key=lambda p: str(p).lower())


def cleanup_repo(root: Path, *, dry_run: bool, compact: bool) -> CleanupReport:
    candidates = _collect_pattern_matches(root) | _collect_cache_dirs(root)
    removed_paths: List[str] = []
    skipped_paths: List[str] = []
    errors: List[str] = []

    for candidate in _sorted_paths(candidates):
        if _is_skipped(candidate, root):
            skipped_paths.append(str(candidate.relative_to(root)))
            continue
        try:
            _remove_path(candidate, dry_run=dry_run)
            removed_paths.append(str(candidate.relative_to(root)))
        except OSError as exc:
            errors.append(f"{candidate}: {exc}")

    git_gc_exit_code = _run_git_gc(root, dry_run=dry_run) if compact else None
    return CleanupReport(
        root=str(root),
        dry_run=dry_run,
        compact=compact,
        removed_paths=removed_paths,
        skipped_paths=skipped_paths,
        errors=errors,
        git_gc_exit_code=git_gc_exit_code,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean temporary repo artifacts and optionally compact git objects."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root directory. Defaults to current directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List cleanup candidates without deleting them.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Run `git gc --prune=now` after cleanup.",
    )
    parser.add_argument(
        "--report",
        default="build/cleanup/cleanup_report.json",
        help="Path to write JSON cleanup report.",
    )

    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = cleanup_repo(root, dry_run=args.dry_run, compact=args.compact)

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = root / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")

    print(f"Cleanup report written to: {report_path}")
    print(f"Removed paths: {len(report.removed_paths)}")
    print(f"Skipped paths: {len(report.skipped_paths)}")
    print(f"Errors: {len(report.errors)}")

    if report.git_gc_exit_code not in (None, 0):
        print(f"git gc exited with code {report.git_gc_exit_code}")
        return report.git_gc_exit_code
    if report.errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

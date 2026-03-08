"""CLI entrypoint for unified cross-IDE common-thread mapping."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestrator.common_thread import (
    DEFAULT_IDE_ROOTS,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TEMPLATE_DIR,
    write_common_thread_artifacts,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build common-thread graph + workflow map + working model bundle."
    )
    parser.add_argument(
        "--roots",
        nargs="+",
        default=DEFAULT_IDE_ROOTS,
        help="Workspace roots to scan.",
    )
    parser.add_argument(
        "--scope",
        default="agent-mcp",
        choices=["agent-mcp", "all"],
        help="Repository scope filter.",
    )
    parser.add_argument(
        "--format",
        default="json+mermaid",
        choices=["json+mermaid", "json", "mermaid"],
        help="Retained for interface compatibility; artifacts are always written.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for generated artifacts.",
    )
    parser.add_argument(
        "--template-dir",
        default=str(DEFAULT_TEMPLATE_DIR),
        help="Template export directory (world-model/wasm sink).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = write_common_thread_artifacts(
        roots=args.roots,
        scope=args.scope,
        output_dir=Path(args.output_dir),
        template_dir=Path(args.template_dir),
    )
    print("Common-thread artifacts generated:")
    for key, value in sorted(paths.items()):
        print(f"- {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

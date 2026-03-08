"""Load root memory anchor preferences for frontier registry builds."""

from __future__ import annotations

from pathlib import Path

DEFAULT_MEMORY_ANCHORS = [Path("C:/AGENTS.md"), Path("C:/Skills.md"), Path("/AGENTS.md"), Path("/Skills.md")]


def load_workspace_preferences() -> dict[str, object]:
    anchors: list[dict[str, str]] = []
    for path in DEFAULT_MEMORY_ANCHORS:
        if path.exists():
            text = path.read_text(encoding="utf-8")
            anchors.append(
                {
                    "path": str(path),
                    "line_count": str(len(text.splitlines())),
                    "bytes": str(len(text.encode("utf-8"))),
                }
            )

    return {
        "memory_anchors": anchors,
        "memory_anchor_count": len(anchors),
    }

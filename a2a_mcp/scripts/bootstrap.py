"""Project bootstrap helpers for stable imports and runtime defaults."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def bootstrap_paths() -> Path:
    """
    Normalize sys.path so both local-package and repo-root imports work.

    Returns:
        Resolved project root path.
    """
    project_root = Path(__file__).resolve().parent
    parent_root = project_root.parent

    root_str = str(project_root)
    parent_str = str(parent_root)

    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    if parent_str not in sys.path:
        sys.path.insert(0, parent_str)

    os.environ.setdefault("A2A_MCP_ROOT", root_str)
    return project_root


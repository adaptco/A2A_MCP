from __future__ import annotations

from pathlib import Path


ALLOWED_ROOTS = (Path("staging").resolve(), Path("exports").resolve())


def enforce_allowed_root(path: Path) -> Path:
    resolved = path.resolve()
    if not any(resolved.is_relative_to(root) for root in ALLOWED_ROOTS):
        raise ValueError(f"Path outside allowed roots: {resolved}")
    return resolved

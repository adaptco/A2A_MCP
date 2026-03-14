#!/usr/bin/env python3
"""Canonicalize the avatar bindings manifest by deeply sorting keys and lists."""

from __future__ import annotations

import json
import sys
from typing import Any


def _sort_deep(value: Any) -> Any:
    """Recursively sort dictionaries and lists for deterministic output."""
    if isinstance(value, dict):
        return {key: _sort_deep(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        canonical_items = [_sort_deep(item) for item in value]
        return sorted(
            canonical_items,
            key=lambda item: json.dumps(item, ensure_ascii=False, separators=(",", ":")),
        )
    return value


def main() -> None:
    data = json.load(sys.stdin)
    canonical = _sort_deep(data)
    json.dump(canonical, sys.stdout, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()

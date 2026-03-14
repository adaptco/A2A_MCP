"""Compatibility shim that allows ``python src/main.py`` while packaging lives under ``core_orchestrator``."""
from __future__ import annotations

from core_orchestrator.cli import main


if __name__ == "__main__":  # pragma: no cover - convenience execution
    raise SystemExit(main())

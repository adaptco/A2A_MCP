"""Compatibility wrapper for Unity MLOps pipeline imports.

Canonical module surface lives at ``src/core_orchestrator/mlops_unity_pipeline.py``
and should be imported as ``core_orchestrator.mlops_unity_pipeline`` when the
package is installed.

This root module is retained for backward compatibility so existing callers can
continue using ``import mlops_unity_pipeline`` in source-checkout contexts.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC_PATH = Path(__file__).resolve().parent / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from core_orchestrator.mlops_unity_pipeline import *  # noqa: F401,F403

from __future__ import annotations

from typing import Tuple

from ..schemas.task import CanonicalTask


def fake_analyzer(task: CanonicalTask) -> Tuple[bool, str]:
    """Deterministic analyzer for tests."""
    if "anomaly" in task.name.lower():
        return False, "anomaly detected"
    return True, ""

from __future__ import annotations

from enum import Enum


class PipelineState(str, Enum):
    IDLE = "idle"
    RENDERED = "rendered"
    VALIDATED = "validated"
    EXPORTED = "exported"
    COMMITTED = "committed"
    HALTED = "halted"

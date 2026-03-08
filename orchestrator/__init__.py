"""Public orchestrator package exports with lazy loading.

This package used to import many heavy modules at import time, which could block
submodule-only consumers (for example tests that only need multimodal helpers).
Exports are now resolved on first access.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Tuple

_EXPORTS: Dict[str, Tuple[str, str]] = {
    # Core classes
    "StateMachine": ("orchestrator.stateflow", "StateMachine"),
    "DBManager": ("orchestrator.storage", "DBManager"),
    "SessionLocal": ("orchestrator.storage", "SessionLocal"),
    "init_db": ("orchestrator.storage", "init_db"),
    "LLMService": ("orchestrator.llm_util", "LLMService"),
    "extract_plan_id_from_path": ("orchestrator.utils", "extract_plan_id_from_path"),
    # Optional components
    "MCPHub": ("orchestrator.main", "MCPHub"),
    "IntentEngine": ("orchestrator.intent_engine", "IntentEngine"),
    "JudgeOrchestrator": ("orchestrator.judge_orchestrator", "JudgeOrchestrator"),
    "schedule_job": ("orchestrator.scheduler", "schedule_job"),
    "TelemetryService": ("orchestrator.telemetry_service", "TelemetryService"),
    "TelemetryIntegration": ("orchestrator.telemetry_integration", "TelemetryIntegration"),
    "ReleaseOrchestrator": ("orchestrator.release_orchestrator", "ReleaseOrchestrator"),
    "ReleaseSignals": ("orchestrator.release_orchestrator", "ReleaseSignals"),
    "ReleasePhase": ("orchestrator.release_orchestrator", "ReleasePhase"),
    "webhook_app": ("orchestrator.webhook", "app"),
    "api_app": ("orchestrator.api", "app"),
    "build_worldline_block": ("orchestrator.multimodal_worldline", "build_worldline_block"),
    "EndToEndOrchestrator": ("orchestrator.end_to_end_orchestration", "EndToEndOrchestrator"),
}

__all__ = list(_EXPORTS.keys())


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module 'orchestrator' has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    try:
        module = import_module(module_name)
        value = getattr(module, attr_name)
    except Exception:
        value = None

    globals()[name] = value
    return value

"""
Orchestrator module - Core kernel for the A2A MCP orchestration system.

Provides orchestration, state management, and pipeline coordination.
"""

# Core classes (always available)
from orchestrator.stateflow import StateMachine
from orchestrator.storage import DBManager, SessionLocal, init_db
from orchestrator.llm_util import LLMService
from orchestrator.utils import extract_plan_id_from_path

# Optional imports with fallback
try:
    from orchestrator.main import MCPHub
except ImportError:
    # MCPHub import depends on agents module
    MCPHub = None

try:
    from orchestrator.intent_engine import IntentEngine
except ImportError:
    IntentEngine = None

try:
    from orchestrator.judge_orchestrator import JudgeOrchestrator
except ImportError:
    JudgeOrchestrator = None

try:
    from orchestrator.scheduler import schedule_job
except ImportError:
    schedule_job = None

try:
    from orchestrator.telemetry_service import TelemetryService
except ImportError:
    TelemetryService = None

try:
    from orchestrator.telemetry_integration import TelemetryIntegration
except ImportError:
    TelemetryIntegration = None

try:
    from orchestrator.release_orchestrator import ReleaseOrchestrator, ReleaseSignals, ReleasePhase
except ImportError:
    ReleaseOrchestrator = None
    ReleaseSignals = None
    ReleasePhase = None

try:
    from orchestrator.webhook import app as webhook_app
except ImportError:
    # webhook depends on FastAPI which may not be installed
    webhook_app = None

__all__ = [
    # Core classes (always available)
    'StateMachine',
    'DBManager',
    'SessionLocal',
    'init_db',
    'LLMService',
    'extract_plan_id_from_path',

    # Optional classes (may be None if dependencies not available)
    'MCPHub',
    'IntentEngine',
    'JudgeOrchestrator',
    'TelemetryService',
    'TelemetryIntegration',
    'ReleaseOrchestrator',
    'ReleaseSignals',
    'ReleasePhase',
    'schedule_job',
    'webhook_app',
]

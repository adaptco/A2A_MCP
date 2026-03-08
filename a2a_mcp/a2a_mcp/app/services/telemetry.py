import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger("TelemetryService")

class TelemetryService:
    """
    Production-grade telemetry service for agent performance and health monitoring.
    Aligns with TELEMETRY_SYSTEM.md specifications.
    """
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.events: List[Dict[str, Any]] = []

    def record_event(self, agent_name: str, event_type: str, metadata: Dict[str, Any] = None):
        """Records a telemetry event with standard headers."""
        event = {
            "trace_id": str(uuid.uuid4()),
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent_name,
            "event_type": event_type,
            "payload": metadata or {}
        }
        self.events.append(event)
        logger.info(f"Telemetry Event: {agent_name} | {event_type}")
        
    def record_performance(self, agent_name: str, duration_ms: float, success: bool):
        """Specifically records execution performance metrics."""
        self.record_event(agent_name, "performance_metric", {
            "duration_ms": duration_ms,
            "success": success
        })

    def export_telemetry(self) -> List[Dict[str, Any]]:
        """Returns all recorded events for persistence or cloud export."""
        return self.events

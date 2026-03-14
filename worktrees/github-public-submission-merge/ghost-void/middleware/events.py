from typing import List, Any
import logging
from orchestrator.storage import _db_manager

# Terminal states that trigger external notifications
TERMINAL_STATES = {"DEPLOYED", "ROLLED_BACK", "DRIFT_BLOCKED", "FINALIZED", "VERIFIED", "CONVERGED", "FAILED", "SCORE_FINALIZED"}

class PostgresEventStore:
    def __init__(self, observers: List[Any] = None):
        self.db_manager = _db_manager
        self.observers = observers or []
        self.logger = logging.getLogger("PostgresEventStore")

    async def append_event(self, artifact):
        """
        Persist the artifact as an event and notify observers if terminal state reached.
        """
        try:
            saved_artifact = self.db_manager.save_artifact(artifact)
        except Exception as e:
            self.logger.error(f"Failed to save artifact {getattr(artifact, 'artifact_id', 'unknown')}: {e}")
            raise

        state = getattr(saved_artifact, 'state', None)
        if state in TERMINAL_STATES:
             self.logger.info(f"Event {saved_artifact.artifact_id} reached terminal state {state}. Notifying observers.")
             for obs in self.observers:
                 try:
                     await obs.on_state_change(saved_artifact)
                 except Exception as e:
                     self.logger.error(f"Observer failed: {e}")
        
        return saved_artifact

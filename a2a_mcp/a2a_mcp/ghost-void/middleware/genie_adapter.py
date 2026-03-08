import asyncio
import logging
import json
from typing import Dict, Any, Optional
from middleware.runtime import AgenticRuntime
from agency_hub.genie_bridge import GenieBridge
from schemas.model_artifact import ModelArtifact, AgentLifecycleState

logger = logging.getLogger(__name__)

class GenieAdapter:
    """
    Middleware adapter that exposes the Genie exploration interface as a client-side API.
    Bridges the Digital Thread (ADK) with the interactive Simulation substrate.
    """
    def __init__(self, runtime: AgenticRuntime, genie_bridge: GenieBridge):
        self.runtime = runtime
        self.genie = genie_bridge
        self.is_active = False

    async def start_interactive_session(self):
        """Initializes the interactive exploration session."""
        self.is_active = True
        logger.info("Genie Interactive Session Started.")
        
        # Emit an event indicating the start of exploration
        artifact = ModelArtifact(
            artifact_id="genie-session-start",
            model_id="genie-foundation-v1",
            weights_hash="N/A",
            embedding_dim=0,
            state=AgentLifecycleState.INIT,
            content="Interactive exploration session initialized."
        )
        await self.runtime.emit_event(artifact)

    async def process_client_input(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes an incoming client intent (e.g. via WebSocket/SSE).
        Returns the updated projection for the client UI/UX.
        """
        if not self.is_active:
            raise RuntimeError("Interactive session not active.")

        intent = payload.get("intent")
        if not intent:
            return {"error": "No intent provided"}

        # Translate and execute via GenieBridge
        success = await self.genie.handle_intent(intent)
        
        # Get the new projection (Project Genie style spatial mapping)
        projection = self.genie.get_explorer_projection()
        
        # Create a trace artifact for the action record
        action_artifact = ModelArtifact(
            artifact_id=f"genie-act-{intent}-{int(asyncio.get_event_loop().time())}",
            model_id="genie-foundation-v1",
            weights_hash="hash_pending",
            embedding_dim=64,
            state=AgentLifecycleState.INIT,
            content=f"Agent executed intent: {intent}",
            metadata={"projection": projection, "success": success}
        )
        await self.runtime.emit_event(action_artifact)

        return {
            "success": success,
            "projection": projection,
            "status": "SETTLED"
        }

    async def stop_interactive_session(self):
        """Ends the interactive session."""
        self.is_active = False
        logger.info("Genie Interactive Session Terminated.")

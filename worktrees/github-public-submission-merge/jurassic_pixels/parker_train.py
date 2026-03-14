import argparse
import sys
import time
import asyncio
import os
import uuid
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Add project root to sys.path to allow imports from orchestrator
sys.path.append(str(Path(__file__).parent.parent))

from middleware import AgenticRuntime, WhatsAppEventObserver
from schemas.model_artifact import ModelArtifact, AgentLifecycleState
from llm.gemini_client import GeminiClient
from llm.decision_engine import DecisionEngine
from llm.decision_schema import ParkerDecision

import websockets

logger = logging.getLogger("ParkerAgent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

# ---------------------------------------------------------------------------
# Action schema
# ---------------------------------------------------------------------------

ALLOWED_DIRECTIONS = {"left", "right", "jump", "idle"}
FAIL_CLOSED_ACTION = {"type": "move", "direction": "idle"}

PARKER_PROMPT_TEMPLATE = (
    "You are Parker, an autonomous game agent.\n"
    "Choose the next action.\n"
    "Allowed directions for 'move' type: left, right, jump, idle.\n"
    "Current observation:\n{observation}"
)


def validate_action(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Strict allowlist validation. Raises ValueError with a reason code on failure."""
    if not isinstance(raw, dict):
        raise ValueError("E_ACTION_NOT_OBJECT")
    if raw.get("type") != "move":
        raise ValueError("E_ACTION_TYPE_INVALID")
    direction = raw.get("direction")
    if direction not in ALLOWED_DIRECTIONS:
        raise ValueError(f"E_ACTION_DIRECTION_INVALID: {direction!r}")
    return {"type": "move", "direction": direction}


def decide_action(engine: DecisionEngine, observation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Gemini via the DecisionEngine to produce the next Parker action.
    Returns a mapped dictionary for fail-closed WebSocket compliance.
    """
    user_prompt = PARKER_PROMPT_TEMPLATE.format(
        observation=json.dumps(observation, sort_keys=True, separators=(",", ":"))
    )
    try:
        decision = engine.decide(
            system="You are Parker's training controller. Decide the next action. Output JSON that matches ParkerDecision.",
            user=f"Context:\nEnvironment observation.\n\nState:\n{user_prompt}\n\nGoal:\nNavigate without crashing."
        )
        
        logger.debug("Parker decided: %s (confidence: %f)", decision.action, decision.confidence)
        
        # Map ParkerDecision back to legacy move dictionary for WebSockets
        if decision.action in ["drive", "continue"]:
             # If mapping drive to ws schema...
             # We'll use the direction equivalent
             return {"type": "move", "direction": "idle"}
        elif decision.action in ["left", "right", "jump", "idle"]:
             return {"type": "move", "direction": decision.action}
        else:
             return {"type": "move", "direction": "idle"}
             
    except Exception as e:
        logger.warning("E_MODEL_CALL_FAILED: %s", e)

    logger.info("Fail-closed: returning idle action")
    return FAIL_CLOSED_ACTION.copy()


# ---------------------------------------------------------------------------
# Gemini client initialisation
# ---------------------------------------------------------------------------

def init_gemini() -> Optional[DecisionEngine]:
    """
    Initialise the Gemini client from GEMINI_API_KEY env var.
    Returns None if credentials are unavailable — agent will not run in intelligent mode.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error(
            "E_MISSING_MODEL_CREDENTIALS: GEMINI_API_KEY not set. "
            "Parker will not run in intelligent mode."
        )
        return None
        
    try:
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
        client = GeminiClient(api_key=api_key, model=model_name)
        engine = DecisionEngine(client)
        logger.info(f"Gemini client and Decision Engine initialised ({model_name})")
        return engine
    except Exception as e:
        logger.error(f"E_GEMINI_INIT_FAILED: {e}")
        return None


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

async def agent_loop():
    client = init_gemini()
    if client is None:
        logger.error("Intelligent mode unavailable. Exiting agent loop.")
        return

    uri = "ws://server:8080"
    logger.info("Connecting to %s...", uri)
    async with websockets.connect(uri) as websocket:
        logger.info("Connected to Game Server")
        while True:
            try:
                message = await websocket.recv()
                observation = json.loads(message)

                # Gemini decides the action via DecisionEngine
                action = decide_action(client, observation)
                await websocket.send(json.dumps(action))

            except websockets.exceptions.ConnectionClosed:
                logger.info("Connection closed")
                break
            except Exception as e:
                logger.error("Unexpected error: %s", e)
                break


# ---------------------------------------------------------------------------
# Training loop (RL stub — separate from intelligent agent loop)
# ---------------------------------------------------------------------------

async def train(episodes: int, export: bool):
    print(f"Starting training for {episodes} episodes...")
    for i in range(episodes):
        print(f"Episode {i+1}/{episodes}: Reward={(i+1)*10}")
        time.sleep(0.1)  # Simulate computation

    if export:
        print("Exporting model to 'parker_model.zip'...")
        with open("parker_model.zip", "w") as f:
            f.write("mock_model_data")

        print("📢 Notifying MLOps Ticker...")
        try:
            api_token = os.getenv("WHATSAPP_API_TOKEN")
            phone_id = os.getenv("WHATSAPP_PHONE_ID")
            channel_id = os.getenv("WHATSAPP_CHANNEL_ID")

            observers = []
            if api_token and phone_id and channel_id:
                observers.append(WhatsAppEventObserver(api_token, phone_id, channel_id))
            else:
                print("⚠️  WhatsApp credentials not found. Skipping notification.")

            if observers:
                runtime = AgenticRuntime(observers=observers)
                artifact = ModelArtifact(
                    artifact_id=f"parker-rl-{str(uuid.uuid4())[:8]}",
                    model_id="parker-rl-v1",
                    weights_hash=str(uuid.uuid4()),
                    embedding_dim=128,
                    state=AgentLifecycleState.CONVERGED,
                    content="RL training completed",
                    metadata={
                        "pipeline": "parker-rl-training",
                        "episodes": episodes,
                        "reward_mean": episodes * 10,
                    },
                )
                await runtime.emit_event(artifact)
                print("✅ CONVERGED event emitted via AgenticRuntime.")
        except Exception as e:
            print(f"❌ Failed to notify ticker: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def interactive():
    try:
        asyncio.run(agent_loop())
    except KeyboardInterrupt:
        print("Agent stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train / Run Parker Agent")
    parser.add_argument("--episodes", type=int, default=10, help="Number of training episodes")
    parser.add_argument("--export", action="store_true", help="Export the trained model")
    parser.add_argument("--interactive", action="store_true", help="Run in intelligent agent mode (Gemini)")

    args = parser.parse_args()

    if args.interactive:
        interactive()
    else:
        asyncio.run(train(args.episodes, args.export))

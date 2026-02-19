from __future__ import annotations

from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect

from prime_directive.api.schemas import HealthResponse
from prime_directive.pipeline.context import PipelineContext
from prime_directive.pipeline.engine import PipelineEngine

app = FastAPI(title="PRIME_DIRECTIVE")
_engine = PipelineEngine(PipelineContext(run_id="bootstrap"))



@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws/pipeline")
async def pipeline_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json({"type": "state.transition", "state": engine.get_state().value})

    try:
        while True:
            message = await websocket.receive_json()
            message_type = message.get("type")

            if message_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif message_type == "get_state":
                await websocket.send_json({"type": "state.transition", "state": engine.get_state().value})
            elif message_type == "render_request":
                await websocket.send_json({"type": "ack", "message": "render_request received"})
            else:
                await websocket.send_json({"type": "error", "message": "unknown message type"})
    except WebSocketDisconnect:
        return

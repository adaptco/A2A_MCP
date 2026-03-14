"""FastAPI app for agent-driven WhatsApp channel notifications."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from agents.notification_agent import NotificationAgent


class ChannelMessageRequest(BaseModel):
    channel_url: str = Field(
        ...,
        description="WhatsApp channel URL, e.g. https://whatsapp.com/channel/...",
    )
    message: str = Field(..., min_length=1, max_length=4096)


app_notify = FastAPI(title="A2A Notification App")
_agent = NotificationAgent()


@app_notify.get("/health")
async def health() -> dict:
    return {"status": "ok", "agent": _agent.agent_name}


@app_notify.post("/notify/whatsapp/channel")
async def notify_whatsapp_channel(payload: ChannelMessageRequest) -> dict:
    result = _agent.send_to_whatsapp_channel(
        channel_url=payload.channel_url,
        message=payload.message,
    )
    return {
        "status": result.status,
        "mode": result.mode,
        "detail": result.detail,
    }

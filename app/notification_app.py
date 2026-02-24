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

def send_pipeline_completion_notification(
    notifier_agent: NotificationAgent,
    project_name: str,
    success: bool,
    completed_actions: int,
    failed_actions: int,
) -> None:
    """
    Send a WhatsApp notification about pipeline completion.

    Args:
        notifier_agent: The NotificationAgent instance to use.
        project_name: Name of the project.
        success: Whether the pipeline succeeded.
        completed_actions: Count of completed actions.
        failed_actions: Count of failed actions.
    """
    if not notifier_agent:
        return

    status_emoji = "✅" if success else "❌"
    message = (
        f"{status_emoji} Pipeline *{project_name}* finished.\n"
        f"Result: {'Success' if success else 'Failure'}\n"
        f"Actions: {completed_actions} completed, {failed_actions} failed."
    )

    # Placeholder channel URL - in prod this would be config-driven
    channel_url = "https://whatsapp.com/channel/example"

    notifier_agent.send_to_whatsapp_channel(channel_url, message)

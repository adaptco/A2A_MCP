"""Agent for outbound notification delivery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from orchestrator.notifier import (
    WhatsAppNotifier,
    send_channel_bridge_notification,
)


@dataclass
class NotificationResult:
    status: str
    mode: str
    detail: str


class NotificationAgent:
    """Sends operational notifications through configured channels."""

    def __init__(self, notifier: Optional[WhatsAppNotifier] = None) -> None:
        self.agent_name = "NotificationAgent-Alpha"
        self.notifier = notifier or WhatsAppNotifier.from_env()

    def send_to_whatsapp_channel(
        self,
        *,
        channel_url: str,
        message: str,
    ) -> NotificationResult:
        """
        Send a channel update request.

        Current behavior uses bridge mode because channel posting is not
        available through public WhatsApp Business/Twilio APIs.
        """
        if not channel_url.startswith("https://whatsapp.com/channel/"):
            return NotificationResult(
                status="FAILED",
                mode="validation",
                detail="Invalid WhatsApp channel URL format.",
            )

        if self.notifier is None:
            return NotificationResult(
                status="SKIPPED",
                mode="disabled",
                detail=(
                    "Notifier is not configured. Set WHATSAPP_NOTIFICATIONS_ENABLED "
                    "and Twilio env vars."
                ),
            )

        send_channel_bridge_notification(
            self.notifier,
            channel_url=channel_url,
            message=message,
            requested_by=self.agent_name,
        )
        return NotificationResult(
            status="SENT",
            mode="bridge_to_operator",
            detail=(
                "Delivered to bridge recipient for channel posting workflow."
            ),
        )

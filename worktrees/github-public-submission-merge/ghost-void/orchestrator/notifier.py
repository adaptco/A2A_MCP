"""WhatsApp notification utilities for task and pipeline completion."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Optional
from urllib import error, parse, request

from dotenv import load_dotenv


load_dotenv()


def _is_enabled(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class WhatsAppNotifier:
    """Twilio-backed WhatsApp notifier."""

    account_sid: str
    auth_token: str
    from_number: str
    to_number: str
    timeout_s: float = 10.0

    @classmethod
    def from_env(cls) -> Optional["WhatsAppNotifier"]:
        """Construct notifier from environment variables when enabled."""
        if not _is_enabled(os.getenv("WHATSAPP_NOTIFICATIONS_ENABLED")):
            return None

        account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        from_number = os.getenv("WHATSAPP_FROM", "").strip()
        to_number = os.getenv("WHATSAPP_TO", "").strip()
        if not all([account_sid, auth_token, from_number, to_number]):
            return None

        return cls(
            account_sid=account_sid,
            auth_token=auth_token,
            from_number=from_number,
            to_number=to_number,
        )

    def send(self, message: str, to_number: Optional[str] = None) -> None:
        """Send WhatsApp message through Twilio REST API."""
        if not message.strip():
            return

        recipient = (to_number or self.to_number).strip()
        if not recipient:
            return

        endpoint = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{self.account_sid}/Messages.json"
        )
        payload = parse.urlencode(
            {
                "From": self.from_number,
                "To": recipient,
                "Body": message,
            }
        ).encode("utf-8")

        credentials = f"{self.account_sid}:{self.auth_token}".encode("utf-8")
        auth_header = base64.b64encode(credentials).decode("ascii")

        req = request.Request(endpoint, data=payload, method="POST")
        req.add_header("Authorization", f"Basic {auth_header}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with request.urlopen(req, timeout=self.timeout_s) as response:
                # Force-read response to surface non-2xx responses.
                _ = response.read()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Twilio HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Twilio network error: {exc.reason}") from exc


def send_pipeline_completion_notification(
    notifier: Optional[WhatsAppNotifier],
    *,
    project_name: str,
    success: bool,
    completed_actions: int,
    failed_actions: int,
) -> None:
    """Best-effort pipeline completion message."""
    if notifier is None:
        return

    status = "SUCCESS" if success else "FAILED"
    message = (
        f"A2A task complete: {project_name}\n"
        f"Status: {status}\n"
        f"Completed actions: {completed_actions}\n"
        f"Failed actions: {failed_actions}"
    )
    notifier.send(message)


def send_channel_bridge_notification(
    notifier: Optional[WhatsAppNotifier],
    *,
    channel_url: str,
    message: str,
    requested_by: str = "NotificationAgent",
) -> None:
    """
    Bridge a channel update request to a direct WhatsApp recipient.

    WhatsApp Channels do not expose a public API for posting messages, so this
    sends the update request to a configured operator number instead.
    """
    if notifier is None:
        return

    bridge_to = os.getenv("WHATSAPP_CHANNEL_BRIDGE_TO", "").strip()
    payload = (
        f"Channel post request\n"
        f"Requested by: {requested_by}\n"
        f"Channel: {channel_url}\n\n"
        f"{message}"
    )
    notifier.send(payload, to_number=bridge_to or None)


def twilio_env_template() -> str:
    """Return JSON template for required environment variables."""
    return json.dumps(
        {
            "WHATSAPP_NOTIFICATIONS_ENABLED": "true",
            "TWILIO_ACCOUNT_SID": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "TWILIO_AUTH_TOKEN": "your_auth_token",
            "WHATSAPP_FROM": "whatsapp:+14155238886",
            "WHATSAPP_TO": "whatsapp:+15551234567",
            "WHATSAPP_CHANNEL_BRIDGE_TO": "whatsapp:+15551234567",
        },
        indent=2,
    )

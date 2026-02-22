import asyncio
import aiohttp
import logging
from dataclasses import dataclass
from typing import Optional, Dict

from event_store.models import Event

logger = logging.getLogger(__name__)

@dataclass
class WhatsAppConfig:
    channel_id: str
    access_token: str
    base_url: str = "https://graph.facebook.com/v20.0"

class WhatsAppEventObserver:
    def __init__(self, config: WhatsAppConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.terminal_states = {
            "FINALIZED", "DEPLOYED", "ROLLED_BACK",
            "DRIFT_BLOCKED", "VERIFIED", "COMPLETED"
        }

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=5)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def on_state_change(self, event: Event) -> None:
        """Non-blocking witness broadcast."""
        if event.state not in self.terminal_states:
            return

        asyncio.create_task(self._broadcast(event))

    async def _broadcast(self, event: Event):
        try:
            payload = self._format_payload(event)
            await self._post_message(payload)
            logger.info(f"✅ Witnessed {event.execution_id} -> WhatsApp")
        except Exception as e:
            logger.warning(f"WhatsApp broadcast failed: {e}")

    def _format_payload(self, event: Event) -> dict:
        """WhatsApp Cloud API channel broadcast format."""
        body = (
            f"[STATE VERIFIED]\n"
            f"pipeline: {event.event_type}\n"
            f"exec: {event.execution_id[:8]}\n"
            f"state: {event.state}\n"
            f"hash: {event.hash_current[:12]}\n"
            f"time: {event.timestamp.strftime('%Y-%m-%dT%H:%M')}"
        )

        return {
            "messaging_product": "whatsapp",
            "recipient_type": "channel",
            "to": self.config.channel_id,
            "type": "text",
            "text": {"body": body}
        }

    async def _post_message(self, payload: Dict):
        # Allow passing session explicitly for testing, or use self.session
        session = self.session
        if session is None:
             # Fallback: create temporary session if not in context manager (though discouraged)
             async with aiohttp.ClientSession() as temp_session:
                await self._send_request(temp_session, payload)
        else:
            await self._send_request(session, payload)

    async def _send_request(self, session: aiohttp.ClientSession, payload: Dict):
        url = f"{self.config.base_url}/{self.config.channel_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.config.access_token}",
            "Content-Type": "application/json"
        }

        async with session.post(url, json=payload, headers=headers) as resp:
            resp.raise_for_status()

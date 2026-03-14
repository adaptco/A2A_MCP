from abc import ABC, abstractmethod
import os
import httpx
import logging
from typing import Dict, Any, List

# Configure logger
logger = logging.getLogger(__name__)

# Events that constitute a "Ticker Worthy" state change
TERMINAL_STATES = {
    "DEPLOYED", 
    "ROLLED_BACK", 
    "DRIFT_BLOCKED", 
    "DEPLOY_VERIFY_PASSED", 
    "DEPLOY_VERIFY_FAILED"
}

class EventObserver(ABC):
    @abstractmethod
    async def on_state_change(self, event: Any):
        """Called when an event state changes."""
        pass

class WhatsAppEventObserver(EventObserver):
    def __init__(self, api_token: str, phone_id: str, channel_id: str):
        self.api_token = api_token
        self.phone_id = phone_id
        self.channel_id = channel_id
        self.api_version = "v20.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    async def on_state_change(self, event: Any):
        """
        Triggered when an event is appended. filters for TERMINAL_STATES.
        """
        if event.state not in TERMINAL_STATES:
            return

        message_body = self._format_message(event)
        await self._send_whatsapp_message(message_body)

    def _format_message(self, event: Any) -> str:
        """
        Formats the event into the settlement-grade text block.
        """
        # Minimal emojis, robust text block
        return (
            f"[MODEL EVENT VERIFIED]\n"
            f"pipeline: {event.pipeline}\n"
            f"execution: {event.execution_id}\n"
            f"state: {event.state}\n"
            f"hash: {event.hash or 'N/A'}\n"
            f"timestamp: {event.timestamp.isoformat()}"
        )

    async def _send_whatsapp_message(self, body_text: str):
        """
        Sends the message via Meta Cloud API with minimal retry strategy.
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": self.channel_id,
            "type": "text",
            "text": {"body": body_text}
        }
        
        max_retries = 3
        base_delay = 1.0

        async with httpx.AsyncClient(timeout=10.0) as client:
            for attempt in range(max_retries + 1):
                try:
                    response = await client.post(
                        self.base_url, 
                        headers=self.headers, 
                        json=payload
                    )
                    response.raise_for_status()
                    logger.info(f"WhatsApp ticker updated: {response.json().get('messages', [{}])[0].get('id')}")
                    return
                except httpx.HTTPError as e:
                    if attempt == max_retries:
                        logger.error(f"Failed to send WhatsApp message after {max_retries} retries: {e}")
                        if hasattr(e, 'response'):
                            logger.error(f"Response: {e.response.text}")
                    else:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"WhatsApp send failed (attempt {attempt+1}/{max_retries}). Retrying in {delay}s...")
                        import asyncio
                        await asyncio.sleep(delay)


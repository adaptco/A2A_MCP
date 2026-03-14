import os
import httpx
import logging
import json
from typing import Optional, Dict, Any

class WhatsAppEventObserver:
    def __init__(self, channel_id: str = None, api_token: str = None):
        self.channel_id = channel_id or os.getenv("WHATSAPP_CHANNEL_ID")
        self.api_token = api_token or os.getenv("WHATSAPP_API_TOKEN")
        self.api_version = "v20.0"
        # Verify if channel_id is phone number ID or WABA ID. Usually Phone Number ID for sending messages.
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.channel_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger("WhatsAppObserver")

    async def on_state_change(self, event):
        if not self.api_token or not self.channel_id:
            self.logger.warning("WhatsApp credentials missing. Skipping notification.")
            return

        body = self._format_message(event)

        payload = {
            "messaging_product": "whatsapp",
            "to": self.channel_id,  # For channel/broadcast, this might need adjustment based on provider
            "type": "text",
            "text": {"body": body}
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.base_url, headers=self.headers, json=payload)
                response.raise_for_status()
                self.logger.info(f"WhatsApp notification sent for event {event.id}")
            except Exception as e:
                self.logger.error(f"Failed to send WhatsApp notification: {e}")

    def _format_message(self, event):
        # Extract metadata safely
        meta = {}
        if hasattr(event, "meta_data") and event.meta_data:
             try:
                 if isinstance(event.meta_data, str):
                    meta = json.loads(event.meta_data)
                 elif isinstance(event.meta_data, dict):
                    meta = event.meta_data
             except:
                 pass
        elif hasattr(event, "metadata") and event.metadata:
             meta = event.metadata
        
        pipeline = meta.get("pipeline_id", "unknown-pipeline")
        execution = meta.get("execution_id", "unknown-execution")
        weights_hash = getattr(event, "weights_hash", "no-hash")
        
        # fallback
        if weights_hash == "no-hash":
             weights_hash = meta.get("weights_hash", "no-hash")

        ts = getattr(event, "created_at", None) or getattr(event, "timestamp", "UNKNOWN_TIME")

        return (
            f"[MODEL EVENT VERIFIED]\n"
            f"pipeline: {pipeline}\n"
            f"execution: {execution}\n"
            f"state: {getattr(event, 'state', 'UNKNOWN').value if hasattr(getattr(event, 'state', 'UNKNOWN'), 'value') else str(getattr(event, 'state', 'UNKNOWN'))}\n"
            f"hash: {weights_hash[:12]}...\n"
            f"timestamp: {ts}"
        )

import asyncio
import logging
from typing import Any, List, Dict
from datetime import datetime, timedelta
from orchestrator.observers import EventObserver, WhatsAppEventObserver

logger = logging.getLogger(__name__)

class TetrisScoreAggregator(EventObserver):
    """
    Aggregates high-frequency scoring events and sends summaries to WhatsApp.
    Prevents "firehose" noise in the public ticker.
    """
    def __init__(self, whatsapp_observer: WhatsAppEventObserver, flush_interval_seconds: int = 60):
        self.whatsapp_observer = whatsapp_observer
        self.flush_interval = flush_interval_seconds
        self.buffer: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._flush_task = None

    async def on_state_change(self, event: Any):
        """
        Triggered on every event. Filters for 'gaming' category and 'SCORE_FINALIZED' state.
        """
        # Ensure EventModel has category support or default to check pipeline name
        category = getattr(event, 'category', 'mlops')
        if category != 'gaming' or event.state != 'SCORE_FINALIZED':
            return

        async with self._lock:
            self.buffer.append({
                "pipeline": event.pipeline,
                "score": event.details.get("score", 0) if isinstance(event.details, dict) else 0,
                "timestamp": event.timestamp
            })
            
            if self._flush_task is None or self._flush_task.done():
                self._flush_task = asyncio.create_task(self._scheduled_flush())

    async def _scheduled_flush(self):
        """
        Wait for the flush interval then send the aggregated summary.
        """
        await asyncio.sleep(self.flush_interval)
        await self.flush_now()

    async def flush_now(self):
        """
        Serializes the buffer into a single WhatsApp notification.
        """
        async with self._lock:
            if not self.buffer:
                return

            count = len(self.buffer)
            total_score = sum(item["score"] for item in self.buffer)
            avg_score = total_score / count if count > 0 else 0
            max_score = max(item["score"] for item in self.buffer) if count > 0 else 0

            summary_text = (
                f"🎮 [GAMING TICKER AGGREGATED]\n"
                f"event: Tetris Score Summary\n"
                f"count: {count} matches\n"
                f"avg_score: {avg_score:.2f}\n"
                f"high_score: {max_score}\n"
                f"window: {self.flush_interval}s\n"
                f"status: SETTLED"
            )

            # Clear buffer before sending to avoid double-processing if notify fails
            self.buffer = []

        # Send via the shared WhatsApp observer
        await self.whatsapp_observer._send_whatsapp_message(summary_text)
        logger.info(f"Aggregated {count} gaming events into WhatsApp ticker.")

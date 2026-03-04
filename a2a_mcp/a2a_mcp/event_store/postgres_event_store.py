import asyncio
import logging
from typing import List, Optional, Any
from .models import Event

logger = logging.getLogger(__name__)

class PostgresEventStore:
    def __init__(self, pool: Any, observers: Optional[List[Any]] = None):
        """
        Initializes the PostgresEventStore.

        Args:
            pool: The database connection pool (e.g., asyncpg.Pool).
            observers: A list of observer objects (e.g., WhatsAppEventObserver).
        """
        self.pool = pool
        self.observers = observers or []

    async def append_event(self, event: Event) -> Event:
        """
        Appends an event to the event store and notifies observers.

        This implementation simulates the database insertion.
        In a real implementation, this would use self.pool to insert into Postgres.
        """
        # Simulate database insertion logic
        # async with self.pool.acquire() as conn:
        #     async with conn.transaction():
        #         await self._insert_event_internal(conn, event)

        logger.info(f"Appended event: {event.execution_id} ({event.event_type})")

        # Fire observers POST-COMMIT (non-blocking)
        if self.observers:
            # We use create_task to ensure it doesn't block the caller
            asyncio.create_task(self._notify_observers(event))

        return event

    async def _notify_observers(self, event: Event):
        """Fire observers in parallel, swallow errors."""
        tasks = [obs.on_state_change(event) for obs in self.observers]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

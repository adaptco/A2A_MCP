import hashlib
import json
import datetime
from typing import Any, Dict, List, Optional

class PostgresEventStore:
    """
    Sovereignty Layer: Event Store for recording every agent action.
    Mock implementation for demo, using hash chains for integrity.
    """
    def __init__(self, pool: Any = None):
        self.pool = pool
        self.events = []
        self._last_hash = "0" * 64

    async def append_event(
        self, 
        tenant_id: str, 
        execution_id: str, 
        event_type: str, 
        payload: Dict[str, Any]
    ) -> str:
        """
        Append an event and return its Merkle-style hash.
        """
        timestamp = datetime.datetime.now().isoformat()
        
        # Create event data for hashing
        event_data = {
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "event_type": event_type,
            "payload": payload,
            "timestamp": timestamp,
            "previous_hash": self._last_hash
        }
        
        # Calculate hash
        event_string = json.dumps(event_data, sort_keys=True)
        event_hash = hashlib.sha256(event_string.encode()).hexdigest()
        
        # In a real impl: await self.pool.execute("INSERT INTO events ...")
        self.events.append({**event_data, "hash": event_hash})
        self._last_hash = event_hash
        
        print(f"🔗 Event Appended: {event_type} | Hash: {event_hash[:10]}...")
        return event_hash

    async def verify_integrity(self) -> bool:
        """
        Verify the hash chain integrity of the event store.
        """
        current_hash = "0" * 64
        for event in self.events:
            event_copy = event.copy()
            claimed_hash = event_copy.pop("hash")
            
            # Verify previous hash link
            if event_copy["previous_hash"] != current_hash:
                return False
                
            # Verify current hash
            recalculated_hash = hashlib.sha256(
                json.dumps(event_copy, sort_keys=True).encode()
            ).hexdigest()
            
            if recalculated_hash != claimed_hash:
                return False
                
            current_hash = recalculated_hash
        return True

    def get_history(self) -> List[Dict]:
        return self.events

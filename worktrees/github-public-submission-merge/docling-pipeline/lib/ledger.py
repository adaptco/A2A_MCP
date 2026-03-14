"""
Hash-chain ledger for deterministic, auditable document processing.
Append-only JSONL with cryptographic linking.
"""
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .canonical import jcs_canonical_bytes, sha256_hex


class Ledger:
    """
    Append-only JSONL ledger with hash-chain integrity.
    Each record includes prev_ledger_hash for chain verification.
    """
    
    def __init__(self, ledger_path: str = "/app/ledger/ledger.jsonl"):
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._prev_hash: Optional[str] = None
        self._load_last_hash()
    
    def _load_last_hash(self) -> None:
        """Load the hash of the last record for chain continuity."""
        if not self.ledger_path.exists():
            return
        
        last_line = None
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line.strip()
        
        if last_line:
            record = json.loads(last_line)
            self._prev_hash = record.get("integrity", {}).get("sha256_canonical")
    
    def append(self, record: dict) -> dict:
        """
        Append a record to the ledger with hash-chain linking.
        Returns the record with integrity fields populated.
        """
        with self._lock:
            # Add timestamp
            record["ledger_timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Remove integrity for hashing
            record_without_integrity = {k: v for k, v in record.items() if k != "integrity"}
            
            # Compute canonical hash
            canonical_bytes = jcs_canonical_bytes(record_without_integrity)
            sha256_canonical = sha256_hex(canonical_bytes)
            
            # Add integrity block
            record["integrity"] = {
                "sha256_canonical": sha256_canonical,
                "prev_ledger_hash": self._prev_hash
            }
            
            # Write to ledger
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
            
            # Update chain
            self._prev_hash = sha256_canonical
            
            return record
    
    def verify_chain(self) -> tuple[bool, Optional[int]]:
        """
        Verify the entire hash chain.
        Returns (is_valid, first_broken_line_number).
        """
        if not self.ledger_path.exists():
            return True, None
        
        prev_hash = None
        line_number = 0
        
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line_number += 1
                if not line.strip():
                    continue
                
                record = json.loads(line.strip())
                integrity = record.get("integrity", {})
                
                # Check prev_hash link
                if integrity.get("prev_ledger_hash") != prev_hash:
                    return False, line_number
                
                # Verify sha256_canonical
                record_without_integrity = {k: v for k, v in record.items() if k != "integrity"}
                computed_hash = sha256_hex(jcs_canonical_bytes(record_without_integrity))
                
                if computed_hash != integrity.get("sha256_canonical"):
                    return False, line_number
                
                prev_hash = integrity["sha256_canonical"]
        
        return True, None


# Global ledger instance
_ledger: Optional[Ledger] = None


def get_ledger() -> Ledger:
    """Get or create the global ledger instance."""
    global _ledger
    if _ledger is None:
        ledger_path = os.environ.get("LEDGER_PATH", "/app/ledger/ledger.jsonl")
        _ledger = Ledger(ledger_path)
    return _ledger

#!/usr/bin/env python3
"""
Determinism Test Suite for Docling Pipeline v1.0.0
Verifies hash-anchored, deterministic processing.
"""

import json
import time
import requests
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Configuration
API_URL = "http://localhost:8000"
LEDGER_PATH = Path("./ledger/ledger.jsonl")
PIPELINE_VERSION = "v1.0.0"


class DeterminismTest:
    """Test suite for pipeline determinism."""
    
    def __init__(self):
        self.results = []
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def check_health(self) -> bool:
        """Check if the pipeline is healthy."""
        try:
            response = requests.get(f"{API_URL}/health", timeout=5)
            if response.status_code == 200:
                self.log("✓ Pipeline is healthy")
                return True
            else:
                self.log(f"✗ Health check failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"✗ Cannot connect to pipeline: {e}", "ERROR")
            return False
    
    def ingest_document(self, file_path: Path) -> str:
        """Ingest a document and return bundle_id."""
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f)}
            data = {'pipeline_version': PIPELINE_VERSION}
            
            response = requests.post(f"{API_URL}/ingest", files=files, data=data)
            response.raise_for_status()
            
            result = response.json()
            bundle_id = result['bundle_id']
            self.log(f"✓ Ingested document: {bundle_id}")
            return bundle_id
    
    def wait_for_processing(self, bundle_id: str, timeout: int = 120) -> bool:
        """Wait for processing to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if LEDGER_PATH.exists():
                with open(LEDGER_PATH, 'r') as f:
                    for line in f:
                        record = json.loads(line)
                        if record.get('doc_id') == bundle_id:
                            self.log(f"✓ Processing complete for {bundle_id}")
                            return True
            time.sleep(2)
        
        self.log(f"✗ Processing timeout for {bundle_id}", "ERROR")
        return False
    
    def get_bundle_hashes(self, bundle_id: str) -> Dict[str, List[str]]:
        """Extract all hashes for a bundle."""
        hashes = []
        
        if not LEDGER_PATH.exists():
            return hashes
        
        with open(LEDGER_PATH, 'r') as f:
            for line in f:
                record = json.loads(line)
                if record.get('doc_id') == bundle_id:
                    hashes.append({
                        'chunk_id': record.get('chunk_id'),
                        'chunk_integrity_hash': record.get('chunk_integrity_hash'),
                        'integrity_hash': record.get('integrity_hash')
                    })
        
        return hashes
    
    def test_replay_determinism(self, test_file: Path) -> bool:
        """
        Test determinism by processing the same file twice.
        """
        self.log("=" * 60)
        self.log("TEST: Replay Determinism")
        self.log("=" * 60)
        
        # First run
        self.log("Run 1: Ingesting document...")
        bundle_id_1 = self.ingest_document(test_file)
        
        if not self.wait_for_processing(bundle_id_1):
            return False
        
        hashes_1 = self.get_bundle_hashes(bundle_id_1)
        self.log(f"Run 1: Captured {len(hashes_1)} chunk hashes")
        
        # Second run
        self.log("Run 2: Ingesting same document...")
        bundle_id_2 = self.ingest_document(test_file)
        
        if not self.wait_for_processing(bundle_id_2):
            return False
        
        hashes_2 = self.get_bundle_hashes(bundle_id_2)
        self.log(f"Run 2: Captured {len(hashes_2)} chunk hashes")
        
        # Compare
        if len(hashes_1) != len(hashes_2):
            self.log(f"✗ FAIL: Chunk count mismatch ({len(hashes_1)} vs {len(hashes_2)})", "ERROR")
            return False
        
        mismatches = 0
        for i, (h1, h2) in enumerate(zip(hashes_1, hashes_2)):
            if h1['chunk_integrity_hash'] != h2['chunk_integrity_hash']:
                self.log(f"✗ Chunk {i} hash mismatch", "ERROR")
                mismatches += 1
        
        if mismatches > 0:
            self.log(f"✗ FAIL: {mismatches} hash mismatches", "ERROR")
            return False
        
        self.log(f"✓ PASS: All {len(hashes_1)} chunk hashes match!")
        return True
    
    def test_hash_chain_integrity(self) -> bool:
        """
        Test ledger hash chain integrity.
        """
        self.log("=" * 60)
        self.log("TEST: Hash Chain Integrity")
        self.log("=" * 60)
        
        if not LEDGER_PATH.exists():
            self.log("✗ Ledger file not found", "ERROR")
            return False
        
        records = []
        with open(LEDGER_PATH, 'r') as f:
            for line in f:
                records.append(json.loads(line))
        
        self.log(f"Verifying {len(records)} ledger entries...")
        
        for i, record in enumerate(records):
            # Check integrity hash exists
            if 'integrity_hash' not in record:
                self.log(f"✗ Entry {i}: Missing integrity_hash", "ERROR")
                return False
            
            # Check chain link
            if i > 0:
                expected_prev = records[i-1]['integrity_hash']
                actual_prev = record.get('prev_ledger_hash')
                
                if expected_prev != actual_prev:
                    self.log(f"✗ Entry {i}: Chain broken", "ERROR")
                    return False
        
        self.log(f"✓ PASS: Hash chain intact for {len(records)} entries")
        return True
    
    def run_all_tests(self, test_file: Path) -> bool:
        """Run all tests."""
        self.log("=" * 60)
        self.log("DOCLING PIPELINE v1.0.0 - DETERMINISM TEST SUITE")
        self.log("=" * 60)
        
        # Health check
        if not self.check_health():
            return False
        
        # Test determinism
        if not self.test_replay_determinism(test_file):
            return False
        
        # Test hash chain
        if not self.test_hash_chain_integrity():
            return False
        
        self.log("=" * 60)
        self.log("✓ ALL TESTS PASSED")
        self.log("=" * 60)
        return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_determinism.py <test_file>")
        print("Example: python test_determinism.py test_document.txt")
        sys.exit(1)
    
    test_file = Path(sys.argv[1])
    
    if not test_file.exists():
        print(f"Error: File not found: {test_file}")
        sys.exit(1)
    
    tester = DeterminismTest()
    success = tester.run_all_tests(test_file)
    
    sys.exit(0 if success else 1)

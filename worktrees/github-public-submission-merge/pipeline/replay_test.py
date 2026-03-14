#!/usr/bin/env python3
"""
Replay Test for Docling Pipeline
Verifies deterministic processing by comparing hashes across multiple runs.
"""

import json
import time
import requests
from pathlib import Path
from qdrant_client import QdrantClient

API_URL = "http://localhost:8000"
QDRANT_URL = "http://localhost:6333"
LEDGER_PATH = Path("./ledger/ledger.jsonl")


def read_ledger():
    """Read all records from the ledger."""
    if not LEDGER_PATH.exists():
        return []
    
    records = []
    with open(LEDGER_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            records.append(json.loads(line))
    return records


def ingest_document(file_path: str, pipeline_version: str = "v1.0.0"):
    """Ingest a document and return bundle_id."""
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {'pipeline_version': pipeline_version}
        
        response = requests.post(f"{API_URL}/ingest", files=files, data=data)
        response.raise_for_status()
        
        result = response.json()
        return result['bundle_id']


def wait_for_processing(bundle_id: str, timeout: int = 60):
    """Wait for processing to complete by checking ledger."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        records = read_ledger()
        doc_records = [r for r in records if r.get('doc_id') == bundle_id]
        
        if doc_records:
            print(f"Found {len(doc_records)} records for bundle {bundle_id}")
            return True
        
        time.sleep(2)
    
    return False


def get_bundle_hashes(bundle_id: str):
    """Extract all hashes for a given bundle from the ledger."""
    records = read_ledger()
    bundle_records = [r for r in records if r.get('doc_id') == bundle_id]
    
    hashes = {
        'chunk_hashes': [],
        'embedding_hashes': []
    }
    
    for record in bundle_records:
        if 'chunk_id' in record:
            hashes['chunk_hashes'].append({
                'chunk_id': record['chunk_id'],
                'chunk_integrity_hash': record.get('chunk_integrity_hash'),
                'integrity_hash': record.get('integrity_hash')
            })
    
    return hashes


def purge_data(bundle_id: str):
    """Purge data for a bundle (for testing purposes)."""
    # In production, implement proper cleanup
    # For now, we'll just note that a full purge would require:
    # 1. Deleting from Qdrant
    # 2. Removing ledger entries (not recommended for append-only ledger)
    # 3. Deleting temporary files
    
    print(f"Note: Full purge not implemented. Bundle {bundle_id} data remains.")


def run_replay_test(test_file: str):
    """
    Run the replay test:
    1. Submit document
    2. Capture hashes
    3. Re-submit same document
    4. Compare hashes
    """
    print("=" * 60)
    print("DOCLING PIPELINE REPLAY TEST")
    print("=" * 60)
    
    # First run
    print("\n[1/4] First ingestion...")
    bundle_id_1 = ingest_document(test_file)
    print(f"Bundle ID: {bundle_id_1}")
    
    print("\n[2/4] Waiting for processing...")
    if not wait_for_processing(bundle_id_1, timeout=120):
        print("ERROR: Processing timeout")
        return False
    
    print("\n[3/4] Capturing hashes from first run...")
    hashes_1 = get_bundle_hashes(bundle_id_1)
    print(f"Captured {len(hashes_1['chunk_hashes'])} chunk hashes")
    
    # Second run
    print("\n[4/4] Second ingestion (same file)...")
    bundle_id_2 = ingest_document(test_file)
    print(f"Bundle ID: {bundle_id_2}")
    
    print("\nWaiting for processing...")
    if not wait_for_processing(bundle_id_2, timeout=120):
        print("ERROR: Processing timeout")
        return False
    
    print("\nCapturing hashes from second run...")
    hashes_2 = get_bundle_hashes(bundle_id_2)
    print(f"Captured {len(hashes_2['chunk_hashes'])} chunk hashes")
    
    # Compare
    print("\n" + "=" * 60)
    print("VERIFICATION RESULTS")
    print("=" * 60)
    
    # Compare chunk counts
    if len(hashes_1['chunk_hashes']) != len(hashes_2['chunk_hashes']):
        print(f"❌ FAIL: Chunk count mismatch")
        print(f"   Run 1: {len(hashes_1['chunk_hashes'])} chunks")
        print(f"   Run 2: {len(hashes_2['chunk_hashes'])} chunks")
        return False
    
    # Compare chunk integrity hashes
    mismatches = 0
    for i, (h1, h2) in enumerate(zip(hashes_1['chunk_hashes'], hashes_2['chunk_hashes'])):
        if h1['chunk_integrity_hash'] != h2['chunk_integrity_hash']:
            print(f"❌ Chunk {i} integrity hash mismatch")
            mismatches += 1
    
    if mismatches > 0:
        print(f"\n❌ FAIL: {mismatches} hash mismatches detected")
        return False
    
    print(f"\n✅ SUCCESS: All {len(hashes_1['chunk_hashes'])} chunk hashes match!")
    print("\nDeterminism verified:")
    print(f"  - Identical chunk counts")
    print(f"  - Identical chunk integrity hashes")
    print(f"  - Pipeline is deterministic")
    
    return True


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python replay_test.py <test_file>")
        print("Example: python replay_test.py test_document.txt")
        sys.exit(1)
    
    test_file = sys.argv[1]
    
    if not Path(test_file).exists():
        print(f"Error: File not found: {test_file}")
        sys.exit(1)
    
    success = run_replay_test(test_file)
    sys.exit(0 if success else 1)

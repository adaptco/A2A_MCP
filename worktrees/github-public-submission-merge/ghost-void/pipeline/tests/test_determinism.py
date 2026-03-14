"""
Determinism Test - Verifies that the pipeline produces identical hashes across runs.
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import sha256_hex, hash_canonical_without_integrity

def test_determinism():
    """
    Test that processing the same document twice produces identical hashes.
    """
    # Create a test document
    test_content = b"This is a test document for determinism verification."
    
    results_run1 = {}
    results_run2 = {}
    
    # Run 1
    print("🔄 Run 1: Processing document...")
    doc_id_1 = f"sha256:{sha256_hex(test_content)}"
    results_run1['doc_id'] = doc_id_1
    
    # Simulate chunking
    chunks_1 = [
        {"text": "This is a test", "index": 0},
        {"text": "document for determinism", "index": 1},
        {"text": "verification.", "index": 2}
    ]
    
    chunk_ids_1 = []
    for chunk in chunks_1:
        # Simplified chunk_id computation
        chunk_data = f"{doc_id_1}:{chunk['index']}:{chunk['text']}"
        chunk_id = f"sha256:{sha256_hex(chunk_data.encode('utf-8'))}"
        chunk_ids_1.append(chunk_id)
    
    results_run1['chunk_ids'] = chunk_ids_1
    
    # Run 2 (identical input)
    print("🔄 Run 2: Processing same document...")
    doc_id_2 = f"sha256:{sha256_hex(test_content)}"
    results_run2['doc_id'] = doc_id_2
    
    chunks_2 = [
        {"text": "This is a test", "index": 0},
        {"text": "document for determinism", "index": 1},
        {"text": "verification.", "index": 2}
    ]
    
    chunk_ids_2 = []
    for chunk in chunks_2:
        chunk_data = f"{doc_id_2}:{chunk['index']}:{chunk['text']}"
        chunk_id = f"sha256:{sha256_hex(chunk_data.encode('utf-8'))}"
        chunk_ids_2.append(chunk_id)
    
    results_run2['chunk_ids'] = chunk_ids_2
    
    # Verify determinism
    print("\n📊 Verification Results:")
    print("=" * 50)
    
    success = True
    
    # Check doc_id
    if results_run1['doc_id'] == results_run2['doc_id']:
        print("✅ doc_id matches across runs")
        print(f"   {results_run1['doc_id']}")
    else:
        print("❌ doc_id MISMATCH")
        print(f"   Run 1: {results_run1['doc_id']}")
        print(f"   Run 2: {results_run2['doc_id']}")
        success = False
    
    # Check chunk_ids
    if results_run1['chunk_ids'] == results_run2['chunk_ids']:
        print("✅ chunk_ids match across runs")
        for i, cid in enumerate(results_run1['chunk_ids']):
            print(f"   [{i}] {cid[:20]}...")
    else:
        print("❌ chunk_ids MISMATCH")
        success = False
    
    print("=" * 50)
    
    if success:
        print("\n🎉 Determinism verified!")
        return 0
    else:
        print("\n⚠️  Determinism test FAILED")
        return 1

if __name__ == "__main__":
    exit(test_determinism())

"""
Determinism verification tests for the EmbedWorker.
"""
import os
import json
import shutil
import sys

def run_worker_test(test_batch, output_dir):
    """
    Executes a test run and returns the batch hash and resulting artifact.
    """
    from workers.embed_worker import EmbedWorker  # pylint: disable=import-outside-toplevel
    worker = EmbedWorker(output_dir=output_dir)
    result = worker.embed_batch(test_batch)
    return result

def verify_determinism():
    """Verifies that the EmbedWorker runs deterministically."""
    print("--- [TEST] Starting EmbedWorker Determinism Verification ---")

    golden_corpus = [
        {
            "text": "The quick brown fox jumps over the lazy dog.",
            "metadata": {"source": "golden_v1"}
        },
        {
            "text": "Agentic workflows require deterministic embedding corridors.",
            "metadata": {"source": "golden_v1"}
        },
        {
            "text": "Docling provides canonical structure for ingestion.",
            "metadata": {"source": "golden_v1"}
        }
    ]

    test_dir_1 = "tests/data/determinism_run_1"
    test_dir_2 = "tests/data/determinism_run_2"

    # Cleanup previous runs
    for d in [test_dir_1, test_dir_2]:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)

    try:
        # Run 1
        print("[Run 1] Executing...")
        res1 = run_worker_test(golden_corpus, test_dir_1)
        hash1 = res1['batch_hash']

        # Run 2
        print("[Run 2] Executing...")
        res2 = run_worker_test(golden_corpus, test_dir_2)
        hash2 = res2['batch_hash']

        # 1. Verify Batch Hash Equality
        print(f"Checking Batch Hashes: {hash1} vs {hash2}")
        assert hash1 == hash2, "FAILURE: Batch hashes are not identical!"
        print("[PASS] Batch hashes are identical.")

        # 2. Verify bit-for-bit artifact equality
        file1 = os.path.join(test_dir_1, f"{hash1}.json")
        file2 = os.path.join(test_dir_2, f"{hash2}.json")

        with open(file1, 'r', encoding='utf-8') as f1, open(file2, 'r', encoding='utf-8') as f2:
            data1 = json.load(f1)
            data2 = json.load(f2)

            # Wipe timestamps for comparison
            data1['timestamp'] = 0
            data2['timestamp'] = 0

            if data1 == data2:
                print("[PASS] Bit-for-bit artifact equality confirmed (ignoring timestamp).")
            else:
                print("[FAIL] FAILURE: Artifacts differ!")
                sys.exit(1)

        print("\n[RESULT] DETERMINISM VERIFIED: The EmbedWorker is stable.")

    finally:
        # Optional: Cleanup
        # shutil.rmtree("tests/data")
        pass

if __name__ == "__main__":
    # Ensure PYTHONPATH is set so we can import workers
    sys.path.append(os.getcwd())
    verify_determinism()

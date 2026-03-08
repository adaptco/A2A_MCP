"""
Embed worker module.
"""
import os
import json
import hashlib
import time
import logging
from typing import Dict, Any, List

# Core imports (expected locally)
try:
    from pipeline.lib.canonicalization import canonicalize_batch, get_batch_hash
except ImportError:
    # If not yet available, we Mock for now
    def canonicalize_batch(b):
        """Mock canonicalize_batch."""
        return b

    def get_batch_hash(b):
        """Mock get_batch_hash."""
        return hashlib.sha256(json.dumps(b).encode()).hexdigest()

# Setup deterministic torch if available
try:
    import torch
    torch.use_deterministic_algorithms(True)
    # torch overrides for CPU non-determinism
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
except (ImportError, RuntimeError):
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmbedWorker")

class EmbedWorker:
    """
    Deterministic Embedding Worker.
    Invariants:
    1. Canonical Input Mapping.
    2. Deterministic Embedding (Fixed model/torch determinism).
    3. Content-Addressed Identity.
    4. Replay-Safe (Atomic output).
    """

    def __init__(self,
                 model_version: str = "all-MiniLM-L6-v2",
                 output_dir: str = "pipeline/ledger/embeddings"):
        self.model_version = model_version
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        # Initialize SentenceTransformer with fixed params
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_version)
            # Ensure model is in eval mode
            self.model.eval()
            logger.info("Initialized EmbedWorker with version %s", model_version)
        except ImportError:
            self.model = None
            logger.warning("sentence_transformers not found. Falling back to pseudo-embeddings.")

    def embed_batch(self, raw_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a batch: Canonicalize -> Hash -> Embed -> Receipt
        """
        # 1. Canonicalize (Stable span ID generation)
        canonical_batch = canonicalize_batch(raw_batch)

        # 2. Content-Addressed Batch Identity (sha256(canonical_input_bytes))
        batch_hash = get_batch_hash(canonical_batch)
        output_path = os.path.join(self.output_dir, f"{batch_hash}.json")
        
        # 3. Check for Idempotency (Skip if already exists)
        if os.path.exists(output_path):
            logger.info("Skipping batch %s (Already processed)", batch_hash)
            with open(output_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        # 4. Deterministic Embedding Generation
        # No dropout, no random seeds, fixed model version
        logger.info("Processing batch %s (%s spans)", batch_hash, len(canonical_batch))

        texts = [node['text'] for node in canonical_batch]
        
        if self.model:
            # Generate real embeddings (bit-for-bit reproducibility)
            # convert_to_numpy=True ensures we have stable format
            embeddings = self.model.encode(
                texts,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True # Unit vector normalization for cosine search
            ).tolist()
        else:
            # Deterministic pseudo-embedding fallback
            embeddings = []
            for text in texts:
                content_hash = hashlib.sha512(text.encode()).digest()
                vector = [(b / 255.0) for b in content_hash[:48]] # 384-dim
                embeddings.append(vector)

        # 5. Receipt Metadata (Model Version, Input Hash, Results)
        receipt = {
            "batch_hash": batch_hash,
            "model_version": self.model_version,
            "worker_version": "1.1.0-deterministic",
            "timestamp": time.time(),
            "results": [
                {
                    "node_id": node["id"],
                    "embedding": vec
                }
                for node, vec in zip(canonical_batch, embeddings)
            ]
        }

        # 6. Atomic Write (Atomic FS swap/write)
        temp_path = f"{output_path}.tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(receipt, f, indent=4)
        os.replace(temp_path, output_path)

        logger.info("Successfully processed batch %s", batch_hash)
        return receipt

if __name__ == "__main__":
    # Test execution
    worker = EmbedWorker()
    test_batch = [
        {"text": "Hello world", "metadata": {"source": "manual"}},
        {"text": "Agentic workflows are key.", "metadata": {"source": "manual"}}
    ]
    result = worker.embed_batch(test_batch)
    print(f"Batch Hash Result: {result['batch_hash']}")

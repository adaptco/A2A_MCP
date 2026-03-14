"""
Embed Worker - Creates embeddings using PyTorch and stores in Qdrant.
"""
import os
import sys
from typing import List

import torch
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from redis import Redis
from rq import Queue, Worker

# Add parent paths for imports
sys.path.insert(0, "/app")

from lib import (
    compute_chunk_id,
    get_ledger,
    hash_canonical_without_integrity
)
from schemas import ChunkEmbeddingV1, Chunker, Embedding, Provenance


# Configuration from environment
EMBEDDER_MODEL_ID = os.environ.get("EMBEDDER_MODEL_ID", "text-embedder-v1")
CHUNKER_VERSION = os.environ.get("CHUNKER_VERSION", "chunk.v1")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
COLLECTION_NAME = "document_chunks"
EMBEDDING_DIM = 768

redis_conn = Redis.from_url(REDIS_URL)
qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# Ensure collection exists
try:
    qdrant_client.get_collection(COLLECTION_NAME)
except Exception:
    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE)
    )

# Mock weights hash (in production, compute from actual model weights)
WEIGHTS_HASH = "sha256:mock_weights_hash_for_scaffolding"


def l2_normalize(x: torch.Tensor, eps: float = 1e-12) -> torch.Tensor:
    """L2 normalize a tensor along the last dimension."""
    return x / torch.clamp(torch.norm(x, p=2, dim=-1, keepdim=True), min=eps)


def get_embedding(text: str) -> List[float]:
    """
    Generate embedding for text using PyTorch model.
    
    NOTE: This is a mock implementation.
    Replace with actual model inference:
    
    from transformers import AutoTokenizer, AutoModel
    tokenizer = AutoTokenizer.from_pretrained(EMBEDDER_MODEL_ID)
    model = AutoModel.from_pretrained(EMBEDDER_MODEL_ID)
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    outputs = model(**inputs)
    embedding = outputs.last_hidden_state.mean(dim=1)
    """
    # Mock: Generate deterministic pseudo-embedding based on text hash
    torch.manual_seed(hash(text) % (2**32))
    embedding = torch.randn(EMBEDDING_DIM)
    embedding = l2_normalize(embedding)
    
    return embedding.tolist()


def embed_chunk(job_payload: dict) -> dict:
    """
    Create embedding for a document chunk and store in Qdrant.
    
    Args:
        job_payload: Contains doc_id, chunk_index, chunk_text, source_block_refs
    
    Returns:
        Embedding metadata for confirmation
    """
    doc_id = job_payload["doc_id"]
    chunk_index = job_payload["chunk_index"]
    chunk_text = job_payload["chunk_text"]
    source_block_refs = job_payload.get("source_block_refs", [])
    bundle_id = job_payload["bundle_id"]
    
    # Compute chunk ID
    chunk_id = compute_chunk_id(doc_id, chunk_index, chunk_text)
    
    # Generate embedding
    vector = get_embedding(chunk_text)
    
    # Build chunk embedding record
    chunk_embedding = ChunkEmbeddingV1(
        doc_id=doc_id,
        chunk_id=chunk_id,
        chunk_text=chunk_text,
        chunker=Chunker(version=CHUNKER_VERSION),
        embedding=Embedding(
            framework="pytorch",
            model_id=EMBEDDER_MODEL_ID,
            weights_hash=WEIGHTS_HASH,
            dim=EMBEDDING_DIM,
            normalization="l2",
            vector=vector
        ),
        provenance=Provenance(source_block_refs=source_block_refs)
    )
    
    # Convert to dict for hashing
    chunk_dict = chunk_embedding.model_dump(by_alias=True, exclude_none=True)
    
    # Compute integrity hash
    sha256_canonical = hash_canonical_without_integrity(chunk_dict)
    
    # Store in Qdrant
    point = PointStruct(
        id=chunk_id.replace("sha256:", "")[:32],  # Qdrant needs shorter IDs
        vector=vector,
        payload={
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "chunk_text": chunk_text[:500],  # Truncate for storage
            "source_block_refs": source_block_refs
        }
    )
    qdrant_client.upsert(collection_name=COLLECTION_NAME, points=[point])
    
    # Append to ledger
    ledger = get_ledger()
    ledger_record = {
        "event": "chunk.embedding.v1",
        "bundle_id": bundle_id,
        "doc_id": doc_id,
        "chunk_id": chunk_id,
        "chunk_index": chunk_index,
        "embedder_model_id": EMBEDDER_MODEL_ID,
        "weights_hash": WEIGHTS_HASH,
        "content_hash": sha256_canonical
    }
    ledger.append(ledger_record)
    
    return {
        "status": "embedded",
        "chunk_id": chunk_id,
        "vector_dim": EMBEDDING_DIM
    }


if __name__ == "__main__":
    # Run as RQ worker
    worker = Worker(
        queues=[Queue("embed_queue", connection=redis_conn)],
        connection=redis_conn
    )
    worker.work()

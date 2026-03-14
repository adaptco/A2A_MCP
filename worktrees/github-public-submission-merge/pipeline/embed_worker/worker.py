"""
Embedding Worker
Generates embeddings using PyTorch and stores in Qdrant.
"""

import json
import redis
import time
import torch
from pathlib import Path
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import sys

# Add parent directory to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.normalize import l2_normalize
from lib.canonical import append_to_ledger

# Redis connection
redis_client = redis.Redis(
    host='redis',
    port=6379,
    db=0,
    decode_responses=True
)

# Qdrant connection
qdrant_client = QdrantClient(host='qdrant', port=6333)

EMBED_QUEUE = "embed_queue"
COLLECTION_NAME = "docling_chunks"
LEDGER_PATH = Path("/data/ledger/ledger.jsonl")

# Model configuration (should be from ConfigMap in production)
MODEL_CONFIG = {
    "embedder_model_id": "sentence-transformers/all-mpnet-base-v2",
    "weights_hash": "sha256:4509c1ee9d2c8edeefc99bd9ca58668916bee2b9b0cf8bf505310e7b64baf670",
    "embedding_dim": 768
}

# Load model
print(f"Loading model: {MODEL_CONFIG['embedder_model_id']}")
model = SentenceTransformer(MODEL_CONFIG['embedder_model_id'])
model.eval()


def initialize_collection():
    """Initialize Qdrant collection if it doesn't exist."""
    collections = qdrant_client.get_collections().collections
    collection_names = [c.name for c in collections]
    
    if COLLECTION_NAME not in collection_names:
        print(f"Creating collection: {COLLECTION_NAME}")
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=MODEL_CONFIG['embedding_dim'],
                distance=Distance.COSINE
            )
        )


def process_batch(batch_payload: Dict[str, Any]) -> None:
    """
    Process a batch of chunks: generate embeddings and store in Qdrant.
    
    Args:
        batch_payload: Batch payload from docling_worker
    """
    batch_id = batch_payload['batch_id']
    chunks = batch_payload['chunks']
    
    print(f"Processing batch {batch_id} with {len(chunks)} chunks")
    
    try:
        # Extract text content
        texts = [chunk['text_content'] for chunk in chunks]
        
        # Generate embeddings (batch inference)
        with torch.no_grad():
            embeddings = model.encode(
                texts,
                convert_to_tensor=True,
                show_progress_bar=False
            )
            
            # L2 normalize
            embeddings = l2_normalize(embeddings)
            
            # Convert to list for storage
            embeddings_list = embeddings.cpu().tolist()
        
        # Prepare points for Qdrant
        points = []
        ledger_records = []
        
        for chunk, embedding in zip(chunks, embeddings_list):
            chunk_id = chunk['chunk_id']
            
            # Create embedding record
            embedding_record = {
                "chunk_id": chunk_id,
                "doc_id": chunk['doc_id'],
                "text_content": chunk['text_content'],
                "embedding": embedding,
                "embedder_model_id": MODEL_CONFIG['embedder_model_id'],
                "weights_hash": MODEL_CONFIG['weights_hash'],
                "chunk_integrity_hash": chunk['integrity_hash']
            }
            
            # Create Qdrant point
            point = PointStruct(
                id=chunk_id,
                vector=embedding,
                payload={
                    "doc_id": chunk['doc_id'],
                    "chunk_index": chunk['chunk_index'],
                    "text_content": chunk['text_content'],
                    "chunk_integrity_hash": chunk['integrity_hash']
                }
            )
            points.append(point)
            ledger_records.append(embedding_record)
        
        # Bulk upsert to Qdrant
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        
        # Append to ledger (batch write)
        for record in ledger_records:
            append_to_ledger(record, LEDGER_PATH)
        
        print(f"Successfully processed batch {batch_id}")
        
    except Exception as e:
        print(f"Error processing batch {batch_id}: {str(e)}")
        raise


def worker_loop():
    """Main worker loop."""
    print("Embedding worker started. Initializing collection...")
    initialize_collection()
    print("Waiting for tasks...")
    
    while True:
        try:
            # Blocking pop from queue (timeout 1 second)
            result = redis_client.blpop(EMBED_QUEUE, timeout=1)
            
            if result:
                _, task_json = result
                batch_payload = json.loads(task_json)
                process_batch(batch_payload)
            
        except KeyboardInterrupt:
            print("Worker shutting down...")
            break
        except Exception as e:
            print(f"Worker error: {str(e)}")
            time.sleep(1)


if __name__ == "__main__":
    worker_loop()

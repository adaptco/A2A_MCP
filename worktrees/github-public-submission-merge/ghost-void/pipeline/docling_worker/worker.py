"""
Docling Worker
Parses documents using IBM Docling and normalizes text.
"""

import json
import redis
import time
import uuid
from pathlib import Path
from typing import List, Dict, Any
import sys

# Add parent directory to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.canonical import hash_canonical_without_integrity
from lib.normalize import normalize_text

# Import Docling
try:
    from docling.document_converter import DocumentConverter
except ImportError:
    print("Warning: Docling not installed. Install with: pip install docling")
    DocumentConverter = None

# Redis connection
redis_client = redis.Redis(
    host='redis',
    port=6379,
    db=0,
    decode_responses=True
)

PARSE_QUEUE = "parse_queue"
EMBED_QUEUE = "embed_queue"
BATCH_SIZE = 32  # Chunks per batch for embedding


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Input text
        chunk_size: Maximum characters per chunk
        overlap: Overlap between chunks
    
    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < text_len:
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            
            if break_point > chunk_size // 2:
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1
        
        chunks.append(chunk.strip())
        start = end - overlap
    
    return [c for c in chunks if c]  # Filter empty chunks


def process_document(task_payload: Dict[str, Any]) -> None:
    """
    Process a document: parse with Docling, normalize, chunk, and enqueue for embedding.
    
    Args:
        task_payload: Task payload from ingest API
    """
    bundle_id = task_payload['bundle_id']
    file_path = Path(task_payload['file_path'])
    pipeline_version = task_payload['pipeline_version']
    
    print(f"Processing bundle {bundle_id}: {file_path}")
    
    try:
        # Parse with Docling
        if DocumentConverter is None:
            # Fallback: read as plain text
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_text = f.read()
        else:
            converter = DocumentConverter()
            result = converter.convert(str(file_path))
            raw_text = result.document.export_to_markdown()
        
        # Normalize text
        normalized_text = normalize_text(raw_text)
        
        # Create normalized document record
        doc_record = {
            "doc_id": bundle_id,
            "pipeline_version": pipeline_version,
            "content": normalized_text,
            "metadata": task_payload.get('metadata', {}),
            "docling_version": "0.4.0",  # Should be from config
            "normalizer_version": "norm.v1"
        }
        
        # Compute integrity hash
        hash_canonical_without_integrity(doc_record)
        
        # Chunk the text
        chunks = chunk_text(normalized_text)
        print(f"Created {len(chunks)} chunks for bundle {bundle_id}")
        
        # Create chunk records
        chunk_records = []
        for idx, chunk_text_content in enumerate(chunks):
            chunk_record = {
                "chunk_id": f"{bundle_id}_chunk_{idx}",
                "doc_id": bundle_id,
                "chunk_index": idx,
                "text_content": chunk_text_content,
                "pipeline_version": pipeline_version,
                "chunker_version": "chunk.v1"
            }
            hash_canonical_without_integrity(chunk_record)
            chunk_records.append(chunk_record)
        
        # Batch chunks for embedding
        batches = [
            chunk_records[i:i + BATCH_SIZE]
            for i in range(0, len(chunk_records), BATCH_SIZE)
        ]
        
        # Enqueue batches to embed_queue
        for batch_idx, batch in enumerate(batches):
            batch_payload = {
                "batch_id": f"{bundle_id}_batch_{batch_idx}",
                "doc_id": bundle_id,
                "chunks": batch,
                "pipeline_version": pipeline_version
            }
            hash_canonical_without_integrity(batch_payload)
            redis_client.rpush(EMBED_QUEUE, json.dumps(batch_payload))
        
        print(f"Enqueued {len(batches)} batches for embedding")
        
    except Exception as e:
        print(f"Error processing bundle {bundle_id}: {str(e)}")
        raise


def worker_loop():
    """Main worker loop."""
    print("Docling worker started. Waiting for tasks...")
    
    while True:
        try:
            # Blocking pop from queue (timeout 1 second)
            result = redis_client.blpop(PARSE_QUEUE, timeout=1)
            
            if result:
                _, task_json = result
                task_payload = json.loads(task_json)
                process_document(task_payload)
            
        except KeyboardInterrupt:
            print("Worker shutting down...")
            break
        except Exception as e:
            print(f"Worker error: {str(e)}")
            time.sleep(1)


if __name__ == "__main__":
    worker_loop()

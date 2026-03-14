"""
Docling Worker - Parses documents using IBM Docling and normalizes output.
"""
import os
import sys
from datetime import datetime, timezone

from redis import Redis
from rq import Queue, Worker

# Add parent paths for imports
sys.path.insert(0, "/app")

from lib import (
    compute_doc_id,
    get_ledger,
    hash_canonical_without_integrity,
    normalize_text
)
from schemas import (
    DocNormalizedV1,
    Source,
    Parser,
    Content,
    Page,
    TextBlock,
    TableBlock
)


# Configuration from environment
PIPELINE_VERSION = os.environ.get("PIPELINE_VERSION", "v0.1.0")
DOCLING_VERSION = os.environ.get("DOCLING_VERSION", "0.5.0")
NORMALIZER_VERSION = os.environ.get("NORMALIZER_VERSION", "norm.v1")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

redis_conn = Redis.from_url(REDIS_URL)
embed_queue = Queue("embed_queue", connection=redis_conn)


def parse_document(job_payload: dict) -> dict:
    """
    Parse a document using Docling and normalize the output.
    
    Args:
        job_payload: Contains bundle_id, content (hex), filename, etc.
    
    Returns:
        Parsed document metadata for ledger
    """
    bundle_id = job_payload["bundle_id"]
    content_hex = job_payload["content"]
    content_bytes = bytes.fromhex(content_hex)
    filename = job_payload["filename"]
    content_type = job_payload["content_type"]
    source_uri = job_payload["source_uri"]
    received_at = job_payload["received_at"]
    
    # Compute document ID from content
    doc_id = compute_doc_id(content_bytes)
    
    # Parse with Docling (mock implementation - replace with actual Docling call)
    # In production: from docling import DocumentParser
    pages = parse_with_docling(content_bytes, content_type)
    
    # Normalize all text blocks
    for page in pages:
        for block in page.blocks:
            if hasattr(block, "text"):
                block.text = normalize_text(block.text)
    
    # Build normalized document
    doc = DocNormalizedV1(
        doc_id=doc_id,
        source=Source(
            uri=source_uri,
            content_type=content_type,
            received_at=datetime.fromisoformat(received_at)
        ),
        parser=Parser(
            name="ibm-docling",
            version=DOCLING_VERSION,
            config_hash=f"sha256:{NORMALIZER_VERSION}"  # Simplified
        ),
        content=Content(
            title=extract_title(pages),
            pages=pages
        )
    )
    
    # Convert to dict for hashing
    doc_dict = doc.model_dump(by_alias=True, exclude_none=True)
    
    # Compute integrity hash
    sha256_canonical = hash_canonical_without_integrity(doc_dict)
    
    # Get ledger and append
    ledger = get_ledger()
    ledger_record = {
        "event": "doc.normalized.v1",
        "bundle_id": bundle_id,
        "doc_id": doc_id,
        "pipeline_version": PIPELINE_VERSION,
        "docling_version": DOCLING_VERSION,
        "normalizer_version": NORMALIZER_VERSION,
        "content_hash": sha256_canonical
    }
    ledger.append(ledger_record)
    
    # Enqueue chunks for embedding
    chunks = create_chunks(doc)
    for i, chunk in enumerate(chunks):
        embed_queue.enqueue(
            "tasks.embed_chunk",
            {
                "bundle_id": bundle_id,
                "doc_id": doc_id,
                "chunk_index": i,
                "chunk_text": chunk["text"],
                "source_block_refs": chunk["refs"]
            }
        )
    
    return {
        "status": "parsed",
        "doc_id": doc_id,
        "pages": len(pages),
        "chunks_queued": len(chunks)
    }


def parse_with_docling(content: bytes, content_type: str) -> list[Page]:
    """
    Parse document content using Docling.
    
    NOTE: This is a mock implementation.
    Replace with actual Docling integration:
    
    from docling import DocumentParser
    parser = DocumentParser()
    result = parser.parse(content, content_type)
    """
    # Mock: Return a single page with the content as text
    text = content.decode("utf-8", errors="replace")
    
    return [
        Page(
            page_index=0,
            blocks=[
                TextBlock(
                    type="text",
                    text=text,
                    block_index=0
                )
            ]
        )
    ]


def extract_title(pages: list[Page]) -> str | None:
    """Extract title from first text block if available."""
    if pages and pages[0].blocks:
        first_block = pages[0].blocks[0]
        if hasattr(first_block, "text"):
            # Take first line as title
            lines = first_block.text.split("\n")
            if lines:
                return lines[0][:200]  # Limit title length
    return None


def create_chunks(doc: DocNormalizedV1) -> list[dict]:
    """
    Create chunks from document using sliding window.
    
    Returns list of {"text": str, "refs": [block_refs]}
    """
    chunks = []
    max_tokens = 400
    overlap = 60
    
    # Collect all text blocks
    all_text = []
    for page in doc.content.pages:
        for block in page.blocks:
            if hasattr(block, "text"):
                ref = f"p{page.page_index}:b{block.block_index}"
                all_text.append((block.text, ref))
    
    # Simple chunking (word-based, not token-based for simplicity)
    combined = " ".join([t[0] for t in all_text])
    words = combined.split()
    
    i = 0
    chunk_index = 0
    while i < len(words):
        chunk_words = words[i:i + max_tokens]
        chunk_text = " ".join(chunk_words)
        
        # Determine which blocks contributed (simplified)
        refs = list(set([t[1] for t in all_text]))
        
        chunks.append({
            "text": chunk_text,
            "refs": refs
        })
        
        i += max_tokens - overlap
        chunk_index += 1
    
    return chunks


if __name__ == "__main__":
    # Run as RQ worker
    worker = Worker(
        queues=[Queue("parse_queue", connection=redis_conn)],
        connection=redis_conn
    )
    worker.work()

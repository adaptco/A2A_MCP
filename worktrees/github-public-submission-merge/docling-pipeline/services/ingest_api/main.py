"""
FastAPI Ingest API for Docling Pipeline.
Accepts documents and enqueues them for processing.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from redis import Redis
from rq import Queue

app = FastAPI(
    title="Docling Ingest API",
    description="Document ingestion endpoint for the Docling pipeline",
    version="0.1.0"
)

# Redis connection
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
redis_conn = Redis.from_url(redis_url)
parse_queue = Queue("parse_queue", connection=redis_conn)


class IngestResponse(BaseModel):
    """Response model for document ingestion."""
    bundle_id: str
    status: str
    queued_at: str
    message: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    redis: str
    timestamp: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    redis_status = "connected"
    try:
        redis_conn.ping()
    except Exception:
        redis_status = "disconnected"
    
    return HealthResponse(
        status="healthy" if redis_status == "connected" else "degraded",
        redis=redis_status,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    source_uri: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None)
):
    """
    Ingest a document for processing.
    
    Args:
        file: The document file to process
        source_uri: Optional source URI override
        metadata: Optional JSON metadata string
    
    Returns:
        IngestResponse with bundle_id for tracking
    """
    # Generate bundle ID
    bundle_id = f"bundle_{uuid.uuid4().hex[:12]}"
    
    # Read file content
    content = await file.read()
    
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    
    # Determine source URI
    if source_uri is None:
        source_uri = f"upload://{file.filename}"
    
    # Create job payload
    job_payload = {
        "bundle_id": bundle_id,
        "filename": file.filename,
        "content_type": file.content_type or "application/octet-stream",
        "source_uri": source_uri,
        "content": content.hex(),  # Hex-encode for JSON serialization
        "received_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata
    }
    
    # Enqueue for parsing
    try:
        job = parse_queue.enqueue(
            "tasks.parse_document",
            job_payload,
            job_id=bundle_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue job: {str(e)}")
    
    return IngestResponse(
        bundle_id=bundle_id,
        status="queued",
        queued_at=datetime.now(timezone.utc).isoformat(),
        message=f"Document '{file.filename}' queued for processing"
    )


@app.get("/status/{bundle_id}")
async def get_status(bundle_id: str):
    """Get the processing status of a bundle."""
    job = parse_queue.fetch_job(bundle_id)
    
    if job is None:
        raise HTTPException(status_code=404, detail="Bundle not found")
    
    return {
        "bundle_id": bundle_id,
        "status": job.get_status(),
        "result": job.result if job.is_finished else None,
        "error": str(job.exc_info) if job.is_failed else None
    }

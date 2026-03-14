"""
FastAPI Ingest Service
Handles file uploads and enqueues parsing tasks.
"""

import uuid
import redis
import json
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import sys

# Add parent directory to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.canonical import hash_canonical_without_integrity

app = FastAPI(title="Docling Ingest API")

# Redis connection
redis_client = redis.Redis(
    host='redis',
    port=6379,
    db=0,
    decode_responses=True
)

PARSE_QUEUE = "parse_queue"


class IngestResponse(BaseModel):
    bundle_id: str
    status: str
    message: str


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {str(e)}")


@app.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    pipeline_version: str = Form("v1.0.0"),
    metadata: Optional[str] = Form(None)
):
    """
    Ingest a document for processing.
    
    Args:
        file: Uploaded file
        pipeline_version: Pipeline version identifier
        metadata: Optional JSON metadata
    
    Returns:
        IngestResponse with bundle_id
    """
    try:
        # Generate bundle ID
        bundle_id = str(uuid.uuid4())
        
        # Parse metadata if provided
        meta_dict = {}
        if metadata:
            try:
                meta_dict = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON metadata")
        
        # Read file content
        content = await file.read()
        
        # Create task payload
        task_payload = {
            "bundle_id": bundle_id,
            "filename": file.filename,
            "content_size": len(content),
            "pipeline_version": pipeline_version,
            "metadata": meta_dict
        }
        
        # Compute integrity hash
        hash_canonical_without_integrity(task_payload)
        
        # Store file temporarily (in production, use object storage)
        temp_dir = Path("/tmp/docling_uploads")
        temp_dir.mkdir(parents=True, exist_ok=True)
        file_path = temp_dir / f"{bundle_id}_{file.filename}"
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Add file path to payload
        task_payload["file_path"] = str(file_path)
        
        # Enqueue to Redis
        redis_client.rpush(PARSE_QUEUE, json.dumps(task_payload))
        
        return IngestResponse(
            bundle_id=bundle_id,
            status="queued",
            message=f"Document queued for processing with bundle_id: {bundle_id}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.get("/status/{bundle_id}")
async def get_status(bundle_id: str):
    """
    Get processing status for a bundle.
    
    Args:
        bundle_id: Bundle identifier
    
    Returns:
        Status information
    """
    # In production, query a status database
    return {
        "bundle_id": bundle_id,
        "status": "processing",
        "message": "Status tracking not yet implemented"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

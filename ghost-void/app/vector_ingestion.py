# knowledge_ingestion.py (Updated)
from fastapi import FastAPI, HTTPException, Header
from oidc_token import verify_github_oidc_token
from pipeline.vector_ingestion import VectorIngestionEngine, upsert_to_knowledge_store

app_ingest = FastAPI()
vector_engine = VectorIngestionEngine()

@app_ingest.post("/ingest")
async def ingest_repository(snapshot: dict, authorization: str = Header(None)):
    """Authenticated endpoint that indexes repository snapshots into Vector DB."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing OIDC Token")
    
    token = authorization.split(" ")[1]
    try:
        # 1. Validate A2A Proof (Handshake)
        claims = verify_github_oidc_token(token)
        
        # 2. Process & Embed (Phase 3 Integration)
        vector_nodes = await vector_engine.process_snapshot(snapshot, claims)
        
        # 3. Persistence
        result = await upsert_to_knowledge_store(vector_nodes)
        
        return {
            "status": "success",
            "ingestion_id": claims.get("jti", "batch_gen"),
            "indexed_count": result["count"],
            "provenance": claims.get("repository")
        }
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Handshake failed: {str(e)}")

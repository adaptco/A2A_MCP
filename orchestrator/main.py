from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from orchestrator.database_utils import init_db, get_db
from schemas.database import ArtifactModel
# ... (Keep previous agent imports)

app = FastAPI(title="A2A MCP Orchestrator - Phase 1")

@app.on_event("startup")
def on_startup():
    init_db()

@app.post("/orchestrate")
async def orchestrate_persistent_flow(user_query: str, db: Session = Depends(get_db)):
    try:
        # 1. Research
        res_art = await researcher.run(topic=user_query)
        db_res = ArtifactModel(
            id=res_art.artifact_id,
            agent_name=res_art.metadata["agent"],
            version="1.0",
            type=res_art.type,
            content={"text": res_art.content}
        )
        db.add(db_res)
        db.commit()

        # 2. Development (Now pulling from DB context)
        cod_art = await coder.run(research_artifact=res_art)
        db_cod = ArtifactModel(
            id=cod_art.artifact_id,
            parent_artifact_id=res_art.artifact_id,
            agent_name=cod_art.metadata["agent"],
            version="1.0",
            type=cod_art.type,
            content={"text": cod_art.content}
        )
        db.add(db_cod)
        db.commit()

        # ... (Repeat for Tester)
        
        return {"status": "Persistent A2A Flow Complete", "root_id": res_art.artifact_id}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

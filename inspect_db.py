from orchestrator.storage import DBManager
from schemas.database import ArtifactModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:pass@localhost:5432/mcp_db")

def inspect_artifacts():
    """
    Retrieves and displays all persistent artifacts to verify 
    the A2A-MCP self-healing trace.
    """
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    print("\n--- 📜 A2A-MCP Artifact Trace Log ---")
    artifacts = db.query(ArtifactModel).order_by(ArtifactModel.created_at).all()

    if not artifacts:
        print("No artifacts found in the database.")
        return

    for art in artifacts:
        print(f"[{art.created_at.strftime('%H:%M:%S')}] {art.agent_name} (v{art.version})")
        print(f"  Type: {art.type}")
        print(f"  ID: {art.id}")
        print(f"  Parent: {art.parent_artifact_id}")
        print("-" * 40)

    db.close()

if __name__ == "__main__":
    inspect_artifacts()

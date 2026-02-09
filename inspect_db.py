from orchestrator.database_utils import SessionLocal
from schemas.database import ArtifactModel
import json

def inspect_artifacts():
    db = SessionLocal()
    try:
        artifacts = db.query(ArtifactModel).order_by(ArtifactModel.created_at).all()
        
        print(f"\n{'='*60}")
        print(f"{'AGENT':<15} | {'TYPE':<15} | {'ID':<10} | {'PARENT'}")
        print(f"{'-'*60}")
        
        for art in artifacts:
            parent = art.parent_artifact_id if art.parent_artifact_id else "ROOT"
            print(f"{art.agent_name:<15} | {art.type:<15} | {art.id[:8]:<10} | {parent[:8]}")
            
        print(f"{'='*60}\n")
        
    finally:
        db.close()

if __name__ == "__main__":
    inspect_artifacts()

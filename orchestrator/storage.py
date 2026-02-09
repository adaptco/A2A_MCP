from sqlalchemy import create_all
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from schemas.database import Base, ArtifactModel
from schemas.agent_artifacts import MCPArtifact
import os

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/mcp_db")

class DBManager:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        # Ensure tables exist (Robustness Directive)
        Base.metadata.create_all(bind=self.engine)

    def save_artifact(self, artifact: MCPArtifact):
        """
        Transcodes a Pydantic MCPArtifact into a persistent SQLAlchemy model.
        """
        db = self.SessionLocal()
        try:
            db_artifact = ArtifactModel(
                id=artifact.artifact_id,
                parent_artifact_id=artifact.parent_artifact_id,
                agent_name=artifact.agent_name,
                version=artifact.version,
                type=artifact.type,
                content=artifact.content
            )
            db.add(db_artifact)
            db.commit()
            db.refresh(db_artifact)
            return db_artifact
        except Exception as e:
            db.rollback()
            print(f"Error persisting artifact: {e}")
            raise
        finally:
            db.close()

    def get_artifact(self, artifact_id: str):
        """Retrieves an artifact by ID for agent context injection."""
        db = self.SessionLocal()
        artifact = db.query(ArtifactModel).filter(ArtifactModel.id == artifact_id).first()
        db.close()
        return artifact

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from schemas.database import Base, ArtifactModel
import os

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./a2a_mcp.db")

class DBManager:
    def __init__(self):
        # check_same_thread is required for SQLite
        connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
        self.engine = create_engine(DATABASE_URL, connect_args=connect_args)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

    def save_artifact(self, artifact):
        db = self.SessionLocal()
        try:
            db_artifact = ArtifactModel(
                id=artifact.artifact_id,
                parent_artifact_id=getattr(artifact, 'parent_artifact_id', None),
                agent_name=getattr(artifact, 'agent_name', 'UnknownAgent'),
                version=getattr(artifact, 'version', '1.0.0'),
                type=artifact.type,
                content=artifact.content
            )
            db.add(db_artifact)
            db.commit()
            return db_artifact
        finally:
            db.close()

    def get_artifact(self, artifact_id):
        db = self.SessionLocal()
        artifact = db.query(ArtifactModel).filter(ArtifactModel.id == artifact_id).first()
        db.close()
        return artifact

def init_db():
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

# All instructional text has been removed to prevent SyntaxErrors.
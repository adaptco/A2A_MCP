from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from schemas.database import Base, ArtifactModel, PlanStateModel
from schemas.agent_artifacts import MCPArtifact
import os
import json
from typing import Optional, Dict, Any

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./a2a_mcp.db")
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class DBManager:
    def __init__(self) -> None:
        self.engine = engine
        self.SessionLocal = SessionLocal
        Base.metadata.create_all(bind=self.engine)

    def save_artifact(self, artifact: MCPArtifact) -> ArtifactModel:
        """Save an MCPArtifact to the database."""
        db = self.SessionLocal()
        try:
            db_artifact = ArtifactModel(
                id=artifact.artifact_id,
                parent_artifact_id=getattr(artifact, 'parent_artifact_id', None),
                agent_name=getattr(artifact, 'agent_name', 'UnknownAgent'),
                version=getattr(artifact, 'version', '1.0.0'),
                type=artifact.type,
                content=artifact.content if isinstance(artifact.content, str) else json.dumps(artifact.content)
            )
            db.add(db_artifact)
            db.commit()
            return db_artifact
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_artifact(self, artifact_id: str) -> Optional[ArtifactModel]:
        """Retrieve an artifact by ID from the database."""
        db = self.SessionLocal()
        try:
            artifact = db.query(ArtifactModel).filter(ArtifactModel.id == artifact_id).first()
            return artifact
<<<<<<< HEAD
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(f"Error retrieving artifact {artifact_id}")
            raise
=======
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe
        finally:
            db.close()


_db_manager = DBManager()


def save_plan_state(plan_id: str, snapshot: Dict[str, Any]) -> None:
    """Save FSM plan state snapshot to the database."""
    db = _db_manager.SessionLocal()
    try:
        serialized_snapshot = json.dumps(snapshot)
        existing = db.query(PlanStateModel).filter(PlanStateModel.plan_id == plan_id).first()
        if existing:
            existing.snapshot = serialized_snapshot
        else:
            db.add(PlanStateModel(plan_id=plan_id, snapshot=serialized_snapshot))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def load_plan_state(plan_id: str) -> Optional[Dict[str, Any]]:
    """Load FSM plan state snapshot from the database."""
    db = _db_manager.SessionLocal()
    try:
        state = db.query(PlanStateModel).filter(PlanStateModel.plan_id == plan_id).first()
        if not state:
            return None
        return json.loads(state.snapshot)
    finally:
        db.close()

<<<<<<< HEAD
# Create engine for SessionLocal
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

# SessionLocal for backward compatibility (used by mcp_server.py)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
=======
def init_db() -> None:
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)

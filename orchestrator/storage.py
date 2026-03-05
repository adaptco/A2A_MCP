from __future__ import annotations

import atexit
import json
import os
from typing import Any, Dict, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from schemas.agent_artifacts import MCPArtifact
from schemas.database import Base, ArtifactModel, PlanStateModel

SQLITE_DEFAULT_PATH = "./a2a_mcp.db"


def resolve_database_url() -> str:
    """
    Resolve database URL from explicit URL or profile mode.

    Priority:
    1) DATABASE_URL
    2) DATABASE_MODE=postgres with POSTGRES_* vars
    3) DATABASE_MODE=sqlite with SQLITE_PATH
    """
    explicit_url = os.getenv("DATABASE_URL", "").strip()
    if explicit_url:
        return explicit_url

    database_mode = os.getenv("DATABASE_MODE", "sqlite").strip().lower()
    if database_mode == "postgres":
        user = os.getenv("POSTGRES_USER", "postgres").strip()
        password = os.getenv("POSTGRES_PASSWORD", "pass").strip()
        host = os.getenv("POSTGRES_HOST", "localhost").strip()
        port = os.getenv("POSTGRES_PORT", "5432").strip()
        database = os.getenv("POSTGRES_DB", "mcp_db").strip()
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"

    sqlite_path = os.getenv("SQLITE_PATH", SQLITE_DEFAULT_PATH).strip() or SQLITE_DEFAULT_PATH
    sqlite_path = sqlite_path.replace("\\", "/")
    return f"sqlite:///{sqlite_path}"


DATABASE_URL = resolve_database_url()


def _build_connect_args(database_url: str) -> dict:
    return {"check_same_thread": False} if "sqlite" in database_url else {}


class DBManager:
    """Manages database operations for artifacts and plan states."""
    
    _shared_engine = None
    _shared_session = None

    def __init__(self) -> None:
        if DBManager._shared_engine is None:
            connect_args = _build_connect_args(DATABASE_URL)
            DBManager._shared_engine = create_engine(DATABASE_URL, connect_args=connect_args)
            Base.metadata.create_all(bind=DBManager._shared_engine)
            DBManager._shared_session = sessionmaker(
                autocommit=False, autoflush=False, bind=DBManager._shared_engine
            )
        
        self.engine = DBManager._shared_engine
        self.SessionLocal = DBManager._shared_session

    def save_artifact(self, artifact: MCPArtifact | Any) -> ArtifactModel:
        """Save an MCPArtifact to the database."""
        db = self.SessionLocal()
        try:
            artifact_id = getattr(artifact, "artifact_id", None) or getattr(artifact, "id", None)
            db_artifact = ArtifactModel(
                id=artifact_id,
                parent_artifact_id=getattr(artifact, 'parent_artifact_id', None) or (artifact.metadata.get('parent_artifact_id') if hasattr(artifact, 'metadata') and isinstance(artifact.metadata, dict) else None),
                agent_name=getattr(artifact, 'agent_name', 'UnknownAgent') or (artifact.metadata.get('agent_name', 'UnknownAgent') if hasattr(artifact, 'metadata') and isinstance(artifact.metadata, dict) else 'UnknownAgent'),
                version=getattr(artifact, 'version', '1.0.0') or (artifact.metadata.get('version', '1.0.0') if hasattr(artifact, 'metadata') and isinstance(artifact.metadata, dict) else '1.0.0'),
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
        """Retrieve an artifact by ID."""
        db = self.SessionLocal()
        try:
            return db.query(ArtifactModel).filter(ArtifactModel.id == artifact_id).first()
        finally:
            db.close()

_db_manager = DBManager()
SessionLocal = _db_manager.SessionLocal

def save_plan_state(plan_id: str, snapshot: Dict[str, Any]) -> None:
    """Save FSM plan state snapshot."""
    from orchestrator.fsm_persistence import persist_state_machine_snapshot

    db = _db_manager.SessionLocal()
    try:
        serialized = json.dumps(snapshot)
        existing = db.query(PlanStateModel).filter(PlanStateModel.plan_id == plan_id).first()
        if existing:
            existing.snapshot = serialized
        else:
            db.add(PlanStateModel(plan_id=plan_id, snapshot=serialized))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    
    # Append-only FSM persistence
    try:
        persist_state_machine_snapshot(plan_id, snapshot)
    except ImportError:
        pass

def load_plan_state(plan_id: str) -> Optional[Dict[str, Any]]:
    """Load FSM plan state snapshot."""
    from orchestrator.fsm_persistence import load_state_machine_snapshot

    try:
        snapshot = load_state_machine_snapshot(plan_id)
        if snapshot is not None:
            return snapshot
    except ImportError:
        pass

    db = _db_manager.SessionLocal()
    try:
        state = db.query(PlanStateModel).filter(PlanStateModel.plan_id == plan_id).first()
        return json.loads(state.snapshot) if state else None
    finally:
        db.close()

def init_db() -> None:
    """Initialize database tables."""
    Base.metadata.create_all(bind=_db_manager.engine)

def _dispose_engine():
    if DBManager._shared_engine is not None:
        DBManager._shared_engine.dispose()

atexit.register(_dispose_engine)

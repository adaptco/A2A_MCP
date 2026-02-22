from __future__ import annotations

import atexit
import json
import os
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from schemas.agent_artifacts import MCPArtifact
from schemas.database import ArtifactModel, Base, PlanStateModel


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./a2a_mcp.db")


class DBManager:
    _shared_engine = None
    _shared_session_local = None

    def __init__(self) -> None:
        # Reuse a single engine/sessionmaker across all manager instances.
        if DBManager._shared_engine is None:
            connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
            DBManager._shared_engine = create_engine(DATABASE_URL, connect_args=connect_args)
            DBManager._shared_session_local = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=DBManager._shared_engine,
            )
            Base.metadata.create_all(bind=DBManager._shared_engine)

        self.engine = DBManager._shared_engine
        self.SessionLocal = DBManager._shared_session_local

    def save_artifact(self, artifact: MCPArtifact, session: Optional[Session] = None) -> ArtifactModel:
        """Save an MCPArtifact to the database.

        If an existing session is provided, it is used without closing.
        Otherwise, a new session is created and closed after the operation.
        """
        db = session or self.SessionLocal()
        should_close = session is None
        try:
            db_artifact = ArtifactModel(
                id=artifact.artifact_id,
                parent_artifact_id=getattr(artifact, "parent_artifact_id", None),
                agent_name=getattr(artifact, "agent_name", "UnknownAgent"),
                version=getattr(artifact, "version", "1.0.0"),
                type=artifact.type,
                content=artifact.content if isinstance(artifact.content, str) else json.dumps(artifact.content),
            )
            db.add(db_artifact)
            if should_close:
                db.commit()
            else:
                db.flush()
            return db_artifact
        except Exception:
            if should_close:
                db.rollback()
            raise
        finally:
            if should_close:
                db.close()


    def save_artifacts(self, artifacts: List[MCPArtifact]) -> List[ArtifactModel]:
        """Save multiple MCPArtifacts to the database in a single transaction."""
        db = self.SessionLocal()
        saved_models = []
        try:
            for artifact in artifacts:
                content_val = artifact.content if isinstance(artifact.content, str) else json.dumps(artifact.content)
                db_artifact = ArtifactModel(
                    id=artifact.artifact_id,
                    parent_artifact_id=getattr(artifact, "parent_artifact_id", None),
                    agent_name=getattr(artifact, "agent_name", "UnknownAgent"),
                    version=getattr(artifact, "version", "1.0.0"),
                    type=artifact.type,
                    content=content_val,
                )
                db.add(db_artifact)
                saved_models.append(db_artifact)
            db.commit()
            return saved_models
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    def get_artifact(self, artifact_id: str) -> Optional[ArtifactModel]:
        """Retrieve an artifact by ID from the database."""
        db = self.SessionLocal()
        try:
            return db.query(ArtifactModel).filter(ArtifactModel.id == artifact_id).first()
        finally:
            db.close()


_db_manager = DBManager()


# Engine/session for backward compatibility (used by mcp_server.py)
engine = _db_manager.engine
SessionLocal = _db_manager.SessionLocal


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


def _dispose_engine() -> None:
    if DBManager._shared_engine is not None:
        DBManager._shared_engine.dispose()


atexit.register(_dispose_engine)


def init_db() -> None:
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)

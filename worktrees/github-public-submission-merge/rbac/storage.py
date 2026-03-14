from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    JSON,
    String,
    create_engine,
    Enum as SAEnum,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from rbac.models import AgentRecord, AgentRole

Base = declarative_base()


# ── SQLAlchemy Model ─────────────────────────────────────────────────────

class AgentRecordModel(Base):
    """SQLAlchemy model for persisting AgentRecord."""

    __tablename__ = "agents"

    agent_id = Column(String, primary_key=True)
    agent_name = Column(String, nullable=False)
    role = Column(SAEnum(AgentRole), nullable=False)
    embedding_config = Column(JSON, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    def to_pydantic(self) -> AgentRecord:
        """Convert SQLAlchemy model to Pydantic model."""
        return AgentRecord(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            role=self.role,
            embedding_config=self.embedding_config,
            metadata=self.metadata_,
            active=self.active,
        )

    @classmethod
    def from_pydantic(cls, record: AgentRecord) -> AgentRecordModel:
        """Create SQLAlchemy model from Pydantic model."""
        return cls(
            agent_id=record.agent_id,
            agent_name=record.agent_name,
            role=record.role,
            embedding_config=record.embedding_config,
            metadata_=record.metadata,
            active=record.active,
        )


# ── Abstract Registry ────────────────────────────────────────────────────

class AgentRegistry(ABC):
    """Abstract interface for agent storage."""

    @abstractmethod
    def get(self, agent_id: str) -> Optional[AgentRecord]:
        """Retrieve an agent by ID."""
        ...

    @abstractmethod
    def register(self, record: AgentRecord) -> None:
        """Register or update an agent."""
        ...

    @abstractmethod
    def list_all(self) -> List[AgentRecord]:
        """List all registered agents."""
        ...

    @abstractmethod
    def deactivate(self, agent_id: str) -> bool:
        """Deactivate an agent."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Return the total number of registered agents."""
        ...


# ── In-Memory Implementation ─────────────────────────────────────────────

class InMemoryAgentRegistry(AgentRegistry):
    """In-memory implementation using a dictionary (original MVP)."""

    def __init__(self) -> None:
        self._store: Dict[str, AgentRecord] = {}

    def get(self, agent_id: str) -> Optional[AgentRecord]:
        return self._store.get(agent_id)

    def register(self, record: AgentRecord) -> None:
        self._store[record.agent_id] = record

    def list_all(self) -> List[AgentRecord]:
        return list(self._store.values())

    def deactivate(self, agent_id: str) -> bool:
        if agent_id in self._store:
            self._store[agent_id].active = False
            return True
        return False

    def count(self) -> int:
        return len(self._store)


# ── SQL Implementation ───────────────────────────────────────────────────

class SQLAgentRegistry(AgentRegistry):
    """Database-backed implementation using SQLAlchemy."""

    def __init__(self, db_url: str) -> None:
        connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
        self.engine = create_engine(db_url, connect_args=connect_args)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Ensure tables exist
        Base.metadata.create_all(bind=self.engine)

    def get(self, agent_id: str) -> Optional[AgentRecord]:
        session = self.SessionLocal()
        try:
            db_record = session.query(AgentRecordModel).filter(AgentRecordModel.agent_id == agent_id).first()
            if db_record:
                return db_record.to_pydantic()
            return None
        finally:
            session.close()

    def register(self, record: AgentRecord) -> None:
        session = self.SessionLocal()
        try:
            existing = session.query(AgentRecordModel).filter(AgentRecordModel.agent_id == record.agent_id).first()
            if existing:
                # Update existing
                existing.agent_name = record.agent_name
                existing.role = record.role
                existing.embedding_config = record.embedding_config
                existing.metadata_ = record.metadata
                existing.active = record.active
            else:
                # Create new
                new_record = AgentRecordModel.from_pydantic(record)
                session.add(new_record)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_all(self) -> List[AgentRecord]:
        session = self.SessionLocal()
        try:
            records = session.query(AgentRecordModel).all()
            return [r.to_pydantic() for r in records]
        finally:
            session.close()

    def deactivate(self, agent_id: str) -> None:
        session = self.SessionLocal()
        try:
            record = session.query(AgentRecordModel).filter(AgentRecordModel.agent_id == agent_id).first()
            if record:
                record.active = False
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def count(self) -> int:
        session = self.SessionLocal()
        try:
            return session.query(AgentRecordModel).count()
        finally:
            session.close()


# ── Factory ──────────────────────────────────────────────────────────────

def get_registry() -> AgentRegistry:
    """Return the configured AgentRegistry instance."""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return SQLAgentRegistry(db_url)
    return InMemoryAgentRegistry()

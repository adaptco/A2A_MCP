"""
RBAC Persistence — SQLAlchemy models and database management for agent records.
"""

import json
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Enum as SQLEnum,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from rbac.models import AgentRole

Base = declarative_base()

class DB_AgentRecord(Base):
    """SQLAlchemy model for an agent record."""
    __tablename__ = "agents"

    agent_id = Column(String, primary_key=True, index=True)
    agent_name = Column(String, nullable=False)
    role = Column(SQLEnum(AgentRole), nullable=False)
    # Store JSON as text for SQLite simplicity
    embedding_config_json = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    active = Column(Boolean, default=True)

    @property
    def embedding_config_data(self) -> Optional[Dict[str, Any]]:
        if not self.embedding_config_json:
            return None
        return json.loads(self.embedding_config_json)

    @embedding_config_data.setter
    def embedding_config_data(self, value: Optional[Dict[str, Any]]):
        self.embedding_config_json = json.dumps(value) if value else None

    @property
    def metadata_data(self) -> Dict[str, Any]:
        if not self.metadata_json:
            return {}
        return json.loads(self.metadata_json)

    @metadata_data.setter
    def metadata_data(self, value: Dict[str, Any]):
        self.metadata_json = json.dumps(value)


class Database:
    """Database manager for RBAC persistence."""

    def __init__(self, db_url: str = "sqlite:///./rbac.db"):
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

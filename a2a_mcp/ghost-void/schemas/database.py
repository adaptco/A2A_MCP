from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone
import uuid

Base = declarative_base()

class ArtifactModel(Base):
    __tablename__ = "artifacts"

    # Use a string UUID for the ID to match the A2A-MCP protocol
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_artifact_id = Column(String, nullable=True)
    agent_name = Column(String, nullable=False)
    version = Column(String, default="1.0.0")
    type = Column(String, nullable=False)  # e.g., 'code', 'test_report'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Artifact(id={self.id}, type={self.type}, agent={self.agent_name})>"


class PlanStateModel(Base):
    __tablename__ = "plan_states"

    plan_id = Column(Text, primary_key=True)
    snapshot = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<PlanState(plan_id={self.plan_id})>"

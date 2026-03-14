from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, String, JSON

from .base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    actor_system = Column(String, nullable=False)
    action = Column(String, nullable=False)
    before = Column(JSON, default=dict)
    after = Column(JSON, default=dict)
    gate_results = Column(JSON, default=list)
    request_id = Column(String, nullable=True)

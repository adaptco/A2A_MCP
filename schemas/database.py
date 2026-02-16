from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ArtifactModel(Base):
    __tablename__ = "artifacts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_artifact_id = Column(String, nullable=True)
    agent_name = Column(String, nullable=False)
    version = Column(String, default="1.0.0")
    type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utc_now)

    def __repr__(self) -> str:
        return f"<Artifact(id={self.id}, type={self.type}, agent={self.agent_name})>"


class PlanStateModel(Base):
    __tablename__ = "plan_states"

    plan_id = Column(Text, primary_key=True)
    snapshot = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<PlanState(plan_id={self.plan_id})>"


class TelemetryEventModel(Base):
    """Stores raw telemetry events from system execution."""

    __tablename__ = "telemetry_events"

    event_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=_utc_now, nullable=False)
    component = Column(String, nullable=False)
    event_type = Column(String, nullable=False)

    input_embedding = Column(JSON, nullable=True)
    output_embedding = Column(JSON, nullable=True)
    embedding_distance = Column(Float, nullable=True)

    metadata_json = Column("metadata", JSON, default=dict, nullable=False)
    duration_ms = Column(Float, nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    artifact_id = Column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<TelemetryEvent(id={self.event_id}, component={self.component}, type={self.event_type})>"


class DiagnosticReportModel(Base):
    """Stores formal diagnostic reports with DTC findings."""

    __tablename__ = "diagnostic_reports"

    report_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=_utc_now, nullable=False)

    execution_phase = Column(String, nullable=False)
    trigger_event = Column(String, nullable=False)

    detected_dtcs = Column(JSON, default=list, nullable=False)
    dtc_details = Column(JSON, default=dict, nullable=False)

    embedding_trajectory = Column(JSON, default=list, nullable=False)
    vector_divergence_points = Column(JSON, default=list, nullable=False)

    recommendations = Column(JSON, default=list, nullable=False)
    critical_actions = Column(JSON, default=list, nullable=False)

    max_severity = Column(String, default="low", nullable=False)
    summary = Column(Text, default="", nullable=False)
    structural_gaps_count = Column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<DiagnosticReport(id={self.report_id}, phase={self.execution_phase})>"


class StructuralGapModel(Base):
    """Stores detected structural gaps between components."""

    __tablename__ = "structural_gaps"

    gap_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=_utc_now, nullable=False)

    source_component = Column(String, nullable=False)
    target_component = Column(String, nullable=False)
    artifact_type = Column(String, nullable=False)

    expected_schema = Column(JSON, nullable=False)
    actual_schema = Column(JSON, nullable=False)
    missing_fields = Column(JSON, default=list, nullable=False)
    extra_fields = Column(JSON, default=list, nullable=False)

    expected_embedding = Column(JSON, nullable=True)
    actual_embedding = Column(JSON, nullable=True)
    semantic_distance = Column(Float, nullable=True)

    related_dtc = Column(String, nullable=True)
    severity = Column(String, default="medium", nullable=False)
    report_id = Column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<StructuralGap(id={self.gap_id}, {self.source_component}->{self.target_component})>"


class TransformerDiffModel(Base):
    """Tracks LLM output vs expected embeddings."""

    __tablename__ = "transformer_diffs"

    diff_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=_utc_now, nullable=False)

    prompt_id = Column(String, nullable=False)
    generation_id = Column(String, nullable=False)

    prompt_embedding = Column(JSON, nullable=False)
    generated_embedding = Column(JSON, nullable=False)
    expected_embedding = Column(JSON, nullable=False)

    prompt_to_generated_distance = Column(Float, nullable=False)
    generated_to_expected_distance = Column(Float, nullable=False)

    generated_artifact_id = Column(String, nullable=False)
    status = Column(String, nullable=False)

    def __repr__(self) -> str:
        return f"<TransformerDiff(id={self.diff_id}, status={self.status})>"


class DMNTokenModel(Base):
    """Tokens formatted for DMN decision model consumption."""

    __tablename__ = "dmn_tokens"

    token_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=_utc_now, nullable=False)

    loose_thread_id = Column(String, nullable=False)
    vector = Column(JSON, nullable=False)

    problem_statement = Column(Text, nullable=False)
    context_artifacts = Column(JSON, default=list, nullable=False)

    constraints_json = Column(JSON, default=list, nullable=False)

    decision_criteria_input = Column(JSON, default=dict, nullable=False)
    expected_decision_score = Column(Float, nullable=True)

    dmn_decision_output = Column(String, nullable=True)
    decision_confidence = Column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<DMNToken(id={self.token_id}, status={self.dmn_decision_output})>"

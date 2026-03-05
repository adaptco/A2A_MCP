from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, DateTime, Float, Boolean, JSON, Integer,
    LargeBinary, BigInteger, PrimaryKeyConstraint, UniqueConstraint, Index, ForeignKey
)
from sqlalchemy.orm import declarative_base


def _utc_now():
    return datetime.now(timezone.utc)


Base = declarative_base()

class ArtifactModel(Base):
    """Sovereign artifact record."""
    __tablename__ = "artifacts"

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
    """Finite state machine snapshot storage."""
    __tablename__ = "plan_states"

    plan_id = Column(Text, primary_key=True)
    snapshot = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<PlanState(plan_id={self.plan_id})>"


class FSMExecutionModel(Base):
    __tablename__ = "fsm_execution"

    tenant_id = Column(Text, nullable=False)
    execution_id = Column(Text, primary_key=True)
    fsm_id = Column(Text, nullable=False)
    started_at = Column(DateTime, nullable=False, default=_utc_now)
    finalized_at = Column(DateTime, nullable=True)
    head_seq = Column(BigInteger, nullable=False, default=0)
    head_hash = Column(LargeBinary, nullable=True)
    status = Column(String, nullable=False, default="RUNNING")
    policy_hash = Column(LargeBinary, nullable=False, default=b"")
    role_matrix_ver = Column(String, nullable=False, default="unknown")
    materiality_ver = Column(String, nullable=False, default="unknown")
    system_version = Column(String, nullable=False, default="1.0.0")
    hash_version = Column(Integer, nullable=False, default=1)

    __table_args__ = (
        Index("ix_fsm_execution_tenant_fsm", "tenant_id", "fsm_id"),
    )


class FSMEventModel(Base):
    __tablename__ = "fsm_event"

    tenant_id = Column(Text, nullable=False)
    fsm_id = Column(Text, nullable=False)
    execution_id = Column(Text, nullable=False)
    seq = Column(BigInteger, nullable=False)
    event_type = Column(Text, nullable=False)
    event_version = Column(Integer, nullable=False)
    occurred_at = Column(DateTime, nullable=False)
    payload_canonical = Column(LargeBinary, nullable=False)
    payload_hash = Column(LargeBinary, nullable=False)
    prev_event_hash = Column(LargeBinary, nullable=True)
    event_hash = Column(LargeBinary, nullable=False)
    system_version = Column(Text, nullable=False)
    hash_version = Column(Integer, nullable=False)
    certification = Column(Text, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "execution_id", "seq", name="pk_fsm_event"),
        UniqueConstraint("tenant_id", "execution_id", "event_hash", name="uq_fsm_event_hash"),
        Index("ix_fsm_event_tenant_execution", "tenant_id", "execution_id"),
        Index("ix_fsm_event_tenant_fsm", "tenant_id", "fsm_id"),
    )


class FSMSnapshotModel(Base):
    __tablename__ = "fsm_snapshot"

    tenant_id = Column(Text, nullable=False)
    execution_id = Column(Text, nullable=False)
    snapshot_seq = Column(BigInteger, nullable=False)
    snapshot_canonical = Column(LargeBinary, nullable=False)
    snapshot_hash = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utc_now)

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "execution_id", "snapshot_seq", name="pk_fsm_snapshot"),
    )


# ============================================================================
# Agent Control Schema (ACS) Models
# ============================================================================

class ActionModel(Base):
    """Canonical action registry entry."""

    __tablename__ = "actions"

    action_id = Column(String(255), primary_key=True)
    namespace = Column(String(100), nullable=False)
    name = Column(String(100), nullable=False)
    version = Column(Integer, nullable=False)
    input_schema = Column(JSON, nullable=False)
    output_schema = Column(JSON, nullable=False)
    auth_config = Column(JSON, nullable=False)
    policy_config = Column(JSON, nullable=False)
    execution_config = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=_utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("namespace", "name", "version", name="uq_actions_namespace_name_version"),
    )


class RunModel(Base):
    """Workflow run metadata."""

    __tablename__ = "runs"

    run_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(255), nullable=False)
    tenant_id = Column(String(100), nullable=False)
    actor_id = Column(String(255), nullable=False)
    dag_spec = Column(JSON, nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    created_at = Column(DateTime, default=_utc_now, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_runs_tenant_workflow", "tenant_id", "workflow_id"),
    )


class StepModel(Base):
    """A single actionable step in a workflow run."""

    __tablename__ = "steps"

    step_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), ForeignKey("runs.run_id"), nullable=False)
    node_id = Column(String(100), nullable=False)
    action_id = Column(String(255), ForeignKey("actions.action_id"), nullable=True)
    inputs = Column(JSON, nullable=True)
    outputs = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    attempt_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=_utc_now, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("run_id", "node_id", name="uq_steps_run_node"),
        Index("ix_steps_run_status", "run_id", "status"),
    )


class ApprovalModel(Base):
    """Human or automated approval gate state."""

    __tablename__ = "approvals"

    approval_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    step_id = Column(String(36), ForeignKey("steps.step_id"), nullable=False)
    policy_name = Column(String(100), nullable=False)
    approver_group = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    approver_id = Column(String(255), nullable=True)
    decision_reason = Column(Text, nullable=True)
    requested_at = Column(DateTime, default=_utc_now, nullable=False)
    decided_at = Column(DateTime, nullable=True)


class EventModel(Base):
    """Execution event log for runs and steps."""

    __tablename__ = "events"

    event_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), ForeignKey("runs.run_id"), nullable=False)
    step_id = Column(String(36), ForeignKey("steps.step_id"), nullable=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=_utc_now, nullable=False)

    __table_args__ = (
        Index("ix_events_run_created", "run_id", "created_at"),
    )


class ActionArtifactModel(Base):
    """Immutable artifacts emitted by ACS steps."""

    __tablename__ = "action_artifacts"

    artifact_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    step_id = Column(String(36), ForeignKey("steps.step_id"), nullable=False)
    artifact_type = Column(String(100), nullable=False)
    content_hash = Column(String(64), nullable=False)
    metadata_json = Column("metadata", JSON, nullable=False)
    storage_path = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utc_now, nullable=False)


# ============================================================================
# Telemetry Storage Models - Supporting Diagnostic Telemetry System
# ============================================================================

class TelemetryEventModel(Base):
    """Raw telemetry events from system execution."""
    __tablename__ = "telemetry_events"

    event_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
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

    def __repr__(self):
        return f"<TelemetryEvent(id={self.event_id}, component={self.component})>"


class DiagnosticReportModel(Base):
    """Formal diagnostic reports with DTC findings."""
    __tablename__ = "diagnostic_reports"

    report_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    execution_phase = Column(String, nullable=False)
    trigger_event = Column(String, nullable=False)
    detected_dtcs = Column(JSON, default=[], nullable=False)
    dtc_details = Column(JSON, default={}, nullable=False)
    embedding_trajectory = Column(JSON, default=[], nullable=False)
    recommendations = Column(JSON, default=[], nullable=False)
    max_severity = Column(String, default="low", nullable=False)
    summary = Column(Text, default="", nullable=False)

    def __repr__(self):
        return f"<DiagnosticReport(id={self.report_id})>"


class StructuralGapModel(Base):
    """Stores detected structural gaps between components."""
    __tablename__ = "structural_gaps"

    gap_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    source_component = Column(String, nullable=False)
    target_component = Column(String, nullable=False)
    artifact_type = Column(String, nullable=False)
    expected_schema = Column(JSON, nullable=False)
    actual_schema = Column(JSON, nullable=False)
    missing_fields = Column(JSON, default=[], nullable=False)
    extra_fields = Column(JSON, default=[], nullable=False)
    expected_embedding = Column(JSON, nullable=True)
    actual_embedding = Column(JSON, nullable=True)
    semantic_distance = Column(Float, nullable=True)
    related_dtc = Column(String, nullable=True)
    severity = Column(String, default="medium", nullable=False)
    report_id = Column(String, nullable=True)

    def __repr__(self):
        return f"<StructuralGap(id={self.gap_id}, {self.source_component}ΓåÆ{self.target_component})>"


class TransformerDiffModel(Base):
    """Tracks LLM output vs expected embeddings."""
    __tablename__ = "transformer_diffs"

    diff_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    prompt_id = Column(String, nullable=False)
    generation_id = Column(String, nullable=False)
    prompt_embedding = Column(JSON, nullable=False)
    generated_embedding = Column(JSON, nullable=False)
    expected_embedding = Column(JSON, nullable=False)
    prompt_to_generated_distance = Column(Float, nullable=False)
    generated_to_expected_distance = Column(Float, nullable=False)
    generated_artifact_id = Column(String, nullable=False)
    status = Column(String, nullable=False)  # ALIGNED, DRIFTED, CRITICAL_MISS

    def __repr__(self):
        return f"<TransformerDiff(id={self.diff_id}, status={self.status})>"


class DMNTokenModel(Base):
    """Tokens formatted for DMN decision model consumption."""
    __tablename__ = "dmn_tokens"

    token_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    loose_thread_id = Column(String, nullable=False)
    vector = Column(JSON, nullable=False)
    problem_statement = Column(Text, nullable=False)
    dmn_decision_output = Column(String, nullable=True)
    decision_confidence = Column(Float, nullable=True)

    def __repr__(self):
        return f"<DMNToken(id={self.token_id}, status={self.dmn_decision_output})>"

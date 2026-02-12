from sqlalchemy import Column, String, Text, DateTime, Float, Boolean, JSON, Integer
from sqlalchemy.orm import declarative_base
from datetime import datetime
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
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Artifact(id={self.id}, type={self.type}, agent={self.agent_name})>"


class PlanStateModel(Base):
    __tablename__ = "plan_states"

    plan_id = Column(Text, primary_key=True)
    snapshot = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<PlanState(plan_id={self.plan_id})>"


# ============================================================================
# Telemetry Storage Models - Supporting Diagnostic Telemetry System
# ============================================================================

class TelemetryEventModel(Base):
    """Stores raw telemetry events from system execution"""
    __tablename__ = "telemetry_events"

    event_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    component = Column(String, nullable=False)  # e.g., 'CoderAgent', 'Judge'
    event_type = Column(String, nullable=False)  # e.g., 'execution_start'

    # Vector tracking
    input_embedding = Column(JSON, nullable=True)  # List[float] stored as JSON
    output_embedding = Column(JSON, nullable=True)
    embedding_distance = Column(Float, nullable=True)

    # Metadata
    metadata_json = Column("metadata", JSON, default=dict, nullable=False)
    duration_ms = Column(Float, nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)

    # Artifact linkage
    artifact_id = Column(String, nullable=True)  # Reference to ArtifactModel

    def __repr__(self):
        return f"<TelemetryEvent(id={self.event_id}, component={self.component}, type={self.event_type})>"


class DiagnosticReportModel(Base):
    """Stores formal diagnostic reports with DTC findings"""
    __tablename__ = "diagnostic_reports"

    report_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    execution_phase = Column(String, nullable=False)  # e.g., 'transformer_output'
    trigger_event = Column(String, nullable=False)

    # DTC findings (stored as JSON array)
    detected_dtcs = Column(JSON, default=[], nullable=False)  # List[str]
    dtc_details = Column(JSON, default={}, nullable=False)    # Dict

    # Vector analysis
    embedding_trajectory = Column(JSON, default=[], nullable=False)  # List of [component, vector]
    vector_divergence_points = Column(JSON, default=[], nullable=False)

    # Recommendations
    recommendations = Column(JSON, default=[], nullable=False)
    critical_actions = Column(JSON, default=[], nullable=False)

    max_severity = Column(String, default="low", nullable=False)  # critical, high, medium, low
    summary = Column(Text, default="", nullable=False)

    # Structural gaps count
    structural_gaps_count = Column(Integer, default=0, nullable=False)

    def __repr__(self):
        return f"<DiagnosticReport(id={self.report_id}, phase={self.execution_phase})>"


class StructuralGapModel(Base):
    """Stores detected structural gaps between components"""
    __tablename__ = "structural_gaps"

    gap_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    source_component = Column(String, nullable=False)
    target_component = Column(String, nullable=False)
    artifact_type = Column(String, nullable=False)

    # Schema comparison
    expected_schema = Column(JSON, nullable=False)
    actual_schema = Column(JSON, nullable=False)
    missing_fields = Column(JSON, default=[], nullable=False)
    extra_fields = Column(JSON, default=[], nullable=False)

    # Semantic gap (embedding-based)
    expected_embedding = Column(JSON, nullable=True)
    actual_embedding = Column(JSON, nullable=True)
    semantic_distance = Column(Float, nullable=True)

    # Associated DTC
    related_dtc = Column(String, nullable=True)
    severity = Column(String, default="medium", nullable=False)

    # Diagnostic report linkage
    report_id = Column(String, nullable=True)

    def __repr__(self):
        return f"<StructuralGap(id={self.gap_id}, {self.source_component}→{self.target_component})>"


class TransformerDiffModel(Base):
    """Tracks LLM output vs expected embeddings"""
    __tablename__ = "transformer_diffs"

    diff_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    prompt_id = Column(String, nullable=False)
    generation_id = Column(String, nullable=False)

    # Embeddings
    prompt_embedding = Column(JSON, nullable=False)
    generated_embedding = Column(JSON, nullable=False)
    expected_embedding = Column(JSON, nullable=False)

    # Diff metrics
    prompt_to_generated_distance = Column(Float, nullable=False)
    generated_to_expected_distance = Column(Float, nullable=False)

    # Artifacts
    generated_artifact_id = Column(String, nullable=False)
    status = Column(String, nullable=False)  # ALIGNED, DRIFTED, CRITICAL_MISS

    def __repr__(self):
        return f"<TransformerDiff(id={self.diff_id}, status={self.status})>"


class DMNTokenModel(Base):
    """Tokens formatted for DMN decision model consumption"""
    __tablename__ = "dmn_tokens"

    token_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    loose_thread_id = Column(String, nullable=False)  # Unresolved issue reference
    vector = Column(JSON, nullable=False)  # 768-dim embedding

    problem_statement = Column(Text, nullable=False)
    context_artifacts = Column(JSON, default=[], nullable=False)

    # Constraints extracted (stored as JSON)
    constraints_json = Column(JSON, default=[], nullable=False)

    # Decision inputs for Judge
    decision_criteria_input = Column(JSON, default={}, nullable=False)
    expected_decision_score = Column(Float, nullable=True)

    # DMN execution result
    dmn_decision_output = Column(String, nullable=True)
    decision_confidence = Column(Float, nullable=True)

    def __repr__(self):
        return f"<DMNToken(id={self.token_id}, status={self.dmn_decision_output})>"

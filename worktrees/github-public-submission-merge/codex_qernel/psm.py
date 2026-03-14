"""Permanent Stateful Model (PSM) helpers for Charley Fox Gaussian actions."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class PSMState:
    """Represents a stateful embedding reference for the Charley Fox Model."""

    state_id: str
    embedding: List[float]
    beta: float
    description: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "state_id": self.state_id,
            "embedding": self.embedding,
            "beta": self.beta,
            "description": self.description,
        }


@dataclass(frozen=True)
class GaussianActionResult:
    """Outcome of a Gaussian action synthesis."""

    state_id: str
    predicted_action: str
    divergence_score: float
    confidence: float
    flow_digest: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "state_id": self.state_id,
            "predicted_action": self.predicted_action,
            "divergence_score": self.divergence_score,
            "confidence": self.confidence,
            "flow_digest": self.flow_digest,
        }


_DEFAULT_STATES: Dict[str, PSMState] = {
    "cfm.qf4": PSMState(
        state_id="cfm.qf4",
        embedding=[0.92, 0.88, 0.81],
        beta=0.08,
        description="Anchor embedding capturing the 19.Qf4 pivot with low divergence tolerance.",
    ),
    "cfm.anchor": PSMState(
        state_id="cfm.anchor",
        embedding=[0.9, 0.9, 0.9],
        beta=0.05,
        description="Baseline Parker's Sandbox anchor for Gaussian action synthesis.",
    ),
}


def load_psm_state(state_id: str) -> PSMState:
    """Load a PSM state from the in-memory registry.

    The registry is intentionally minimal for offline testing. Production systems
    would retrieve the state from a verified store such as the Vector Warden.
    """

    state = _DEFAULT_STATES.get(state_id)
    if state is None:
        raise ValueError(f"Unknown PSM state id: {state_id}")
    return state


def _score_embedding_alignment(embedding: List[float], flow: str) -> float:
    base_score = sum(embedding) / max(len(embedding), 1)
    flow_weight = min(1.0, len(flow.strip()) / 256.0)
    alignment = max(0.0, min(1.0, base_score * 0.6 + (1.0 - flow_weight) * 0.4))
    return alignment


def gaussian_action_synth(*, axqos_flow: str, state: PSMState) -> GaussianActionResult:
    """Synthesize a Gaussian action using a deterministic alignment heuristic."""

    if not axqos_flow.strip():
        raise ValueError("AxQxOS flow is required for synthesis")

    alignment = _score_embedding_alignment(state.embedding, axqos_flow)
    divergence_score = round(max(0.0, state.beta * 0.5 + (1.0 - alignment) * 0.2), 4)
    confidence = round(max(0.0, min(1.0, alignment - divergence_score * 0.1)), 4)
    predicted_action = (
        "Commit_Structural_Lock" if confidence >= 0.82 and divergence_score <= state.beta else "Policy_Audit_Required"
    )
    flow_digest = hashlib.sha256(axqos_flow.encode("utf-8")).hexdigest()[:16]

    return GaussianActionResult(
        state_id=state.state_id,
        predicted_action=predicted_action,
        divergence_score=divergence_score,
        confidence=confidence,
        flow_digest=flow_digest,
    )


"""Triadic backbone definitions for ZERO-DRIFT attestation flows.

This module models the canonical flow topology described in the World OS briefing.
The data structures are deliberately lightweight so downstream services—dashboards,
ledger writers, or simulation harnesses—can import them without triggering heavy
orchestration logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional


WORLD_OS_LEDGER_ANCHOR = "WORLD_OS_INFINITE_GAME_DEPLOYED"
DEFAULT_SEAL_PROTOCOL = "APEX-SEAL"
DEFAULT_INTEGRITY_LAYERS: Dict[str, Dict[str, Any]] = {
    "proof": {
        "designation": "QRH Lock",
        "state": "ZERO-DRIFT_COMPLIANT",
    },
    "flow": {
        "designation": "Governed Stability",
        "state": "ZERO-DRIFT_COMPLIANT",
    },
    "execution": {
        "designation": "Operational Fidelity",
        "state": "ZERO-DRIFT_COMPLIANT",
    },
}


@dataclass(frozen=True)
class FlowEdge:
    """Represents a directional relationship between layers in the backbone."""

    source: str
    target: str
    channel: str
    guard: str

    def zero_drift_guarded(self) -> bool:
        """Return True when the guard enforces ZERO-DRIFT semantics."""
        return "ZERO_DRIFT" in self.guard.upper()


@dataclass
class TriadicBackbone:
    """Encapsulates the tri-layer attestation topology."""

    layers: Mapping[str, str]
    flows: Iterable[FlowEdge]
    integrity_protocol: str = "ZERO_DRIFT"
    _adjacency_cache: Dict[str, List[str]] = field(default_factory=dict, init=False, repr=False)

    def as_adjacency(self) -> Dict[str, List[str]]:
        """Return an adjacency list keyed by layer name."""
        if not self._adjacency_cache:
            adjacency: Dict[str, List[str]] = {layer: [] for layer in self.layers}
            for edge in self.flows:
                adjacency.setdefault(edge.source, []).append(edge.target)
            self._adjacency_cache = {node: sorted(targets) for node, targets in adjacency.items()}
        return dict(self._adjacency_cache)

    def zero_drift_attested(self) -> bool:
        """Verify that the topology enforces ZERO-DRIFT across all flows."""
        if self.integrity_protocol.upper() != "ZERO_DRIFT":
            return False
        return all(edge.zero_drift_guarded() for edge in self.flows)

    def ledger_anchor_packet(
        self,
        *,
        cycle_id: str,
        anchor: str = WORLD_OS_LEDGER_ANCHOR,
        integrity_layers: Optional[MutableMapping[str, Dict[str, Any]]] = None,
        seal_protocol: str = DEFAULT_SEAL_PROTOCOL,
    ) -> Dict[str, Any]:
        """Package an attestation envelope that binds the run to the ledger anchor."""

        layer_states: MutableMapping[str, Dict[str, Any]]
        if integrity_layers is None:
            layer_states = {k: dict(v) for k, v in DEFAULT_INTEGRITY_LAYERS.items()}
        else:
            layer_states = integrity_layers

        zero_drift_layers = all(
            "ZERO" in state.get("state", "").upper()
            and "DRIFT" in state.get("state", "").upper()
            for state in layer_states.values()
        )

        packet = {
            "ledger_anchor": anchor,
            "attestation_cycle_id": cycle_id,
            "seal_protocol": seal_protocol,
            "triadic_backbone": {
                "integrity_protocol": self.integrity_protocol,
                "layers": dict(self.layers),
            },
            "integrity_layers": layer_states,
            "zero_drift_guarded": self.zero_drift_attested() and zero_drift_layers,
        }

        return packet


DEFAULT_TRIADIC_BACKBONE = TriadicBackbone(
    layers={
        "codex_operational": "Codex commits and runtime patches",
        "chatgpt_creative": "Workspace capsules and scene definitions",
        "p3l_philosophical": "Purpose-driven execution contracts",
        "qube_core": "Central attestation nexus",
    },
    flows=(
        FlowEdge(
            source="codex_operational",
            target="qube_core",
            channel="commit_attestation",
            guard="ZERO_DRIFT_SIGNATURE",
        ),
        FlowEdge(
            source="chatgpt_creative",
            target="qube_core",
            channel="capsule_projection",
            guard="ZERO_DRIFT_SYNTHESIS",
        ),
        FlowEdge(
            source="p3l_philosophical",
            target="qube_core",
            channel="ethics_constraint",
            guard="ZERO_DRIFT_CANON",
        ),
        FlowEdge(
            source="qube_core",
            target="codex_operational",
            channel="attestation_receipt",
            guard="ZERO_DRIFT_FEEDBACK",
        ),
        FlowEdge(
            source="qube_core",
            target="chatgpt_creative",
            channel="capsule_alignment",
            guard="ZERO_DRIFT_FEEDBACK",
        ),
        FlowEdge(
            source="qube_core",
            target="p3l_philosophical",
            channel="integrity_protocol",
            guard="ZERO_DRIFT_FEEDBACK",
        ),
    ),
)


__all__ = [
    "FlowEdge",
    "TriadicBackbone",
    "DEFAULT_TRIADIC_BACKBONE",
    "WORLD_OS_LEDGER_ANCHOR",
    "DEFAULT_INTEGRITY_LAYERS",
    "DEFAULT_SEAL_PROTOCOL",
]

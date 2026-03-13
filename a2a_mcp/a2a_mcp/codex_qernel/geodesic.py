"""Geodesic terminal modeling for the AxQxOS bridge.

This module synthesizes a lightweight structural model that describes how the
AxQxOS bridge is anchored, tuned, and stabilized. The output is intended to be
consumed by CLI and orchestration layers that want a deterministic blueprint
for simulations or audits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class GeodesicSegment:
    """Represents a single segment in the geodesic lattice."""

    start_anchor: str
    end_anchor: str
    arc_length: float
    curvature: float
    load_factor: float
    stability_score: float

    def to_dict(self) -> Dict[str, float | str]:
        return {
            "start_anchor": self.start_anchor,
            "end_anchor": self.end_anchor,
            "arc_length": self.arc_length,
            "curvature": self.curvature,
            "load_factor": self.load_factor,
            "stability_score": self.stability_score,
        }


@dataclass(frozen=True)
class GeodesicTerminalModel:
    """Composite geodesic terminal blueprint."""

    bridge_name: str
    os_name: str
    span: float
    tension: float
    anchors: List[str]
    lattice_frequency: float
    segments: List[GeodesicSegment]

    def to_dict(self) -> Dict[str, object]:
        return {
            "bridge_name": self.bridge_name,
            "os_name": self.os_name,
            "span": self.span,
            "tension": self.tension,
            "anchors": self.anchors,
            "lattice_frequency": self.lattice_frequency,
            "segments": [segment.to_dict() for segment in self.segments],
        }


def _normalize_anchors(anchors: List[str]) -> List[str]:
    cleaned = [anchor.strip() for anchor in anchors if anchor.strip()]
    if len(cleaned) >= 2:
        return cleaned
    if not cleaned:
        return ["origin", "terminus"]
    return [cleaned[0], f"{cleaned[0]}-return"]


def build_geodesic_terminal(
    *,
    bridge_name: str,
    os_name: str,
    anchors: List[str],
    span: float = 120.0,
    tension: float = 0.82,
) -> GeodesicTerminalModel:
    """Create a deterministic geodesic terminal model.

    The model breaks the bridge into segments between anchors and assigns
    synthetic curvature/load metrics that mirror AxQxOS's bridge semantics.
    """

    resolved_anchors = _normalize_anchors(anchors)
    segment_count = max(1, len(resolved_anchors) - 1)
    segment_span = span / segment_count
    lattice_frequency = round((tension * segment_count) / max(span, 1e-6), 4)

    segments: List[GeodesicSegment] = []
    for idx in range(segment_count):
        start = resolved_anchors[idx]
        end = resolved_anchors[idx + 1]
        curvature = round(tension * 0.7 + (idx / max(segment_count - 1, 1)) * 0.08, 4)
        load_factor = round((segment_span / span) + tension * 0.15, 4)
        stability = round(min(1.0, (1.0 - abs(curvature - tension)) * 0.9 + 0.1), 4)
        segments.append(
            GeodesicSegment(
                start_anchor=start,
                end_anchor=end,
                arc_length=round(segment_span, 3),
                curvature=curvature,
                load_factor=load_factor,
                stability_score=stability,
            )
        )

    return GeodesicTerminalModel(
        bridge_name=bridge_name,
        os_name=os_name,
        span=span,
        tension=tension,
        anchors=resolved_anchors,
        lattice_frequency=lattice_frequency,
        segments=segments,
    )

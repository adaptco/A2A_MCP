"""CODEX qernel runtime implementation for AxQxOS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import json
import threading

from .config import QernelConfig
from .capsules import CapsuleManifest, discover_capsule_manifests, map_capsules_by_id
from .geodesic import GeodesicTerminalModel, build_geodesic_terminal
from .psm import GaussianActionResult, PSMState, gaussian_action_synth, load_psm_state


SCROLLSTREAM_CAPSULE_ID = "capsule.rehearsal.scrollstream.v1"

REHEARSAL_CYCLE = (
    {
        "cycle": "audit.summary",
        "agent": "celine.architect",
        "output": "Celine threads the summary braid, aligning architecture checkpoints for review.",
        "emotion": "anticipation",
    },
    {
        "cycle": "audit.proof",
        "agent": "luma.sentinel",
        "output": "Luma verifies integrity glyphs and seals the ledger proof for observers.",
        "emotion": "assurance",
    },
    {
        "cycle": "audit.execution",
        "agent": "dot.guardian",
        "output": "Dot executes rehearsal safeguards, projecting the replay glyph across the rail.",
        "emotion": "momentum",
    },
)


@dataclass(frozen=True)
class ScrollstreamLedgerEntry:
    """A single rehearsal ledger entry stored for replay."""

    ts: str
    capsule_id: str
    cycle: str
    agent: str
    output: str
    training_mode: bool
    signals: Dict[str, Any]
    emotion: str
    validations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts": self.ts,
            "capsule_id": self.capsule_id,
            "cycle": self.cycle,
            "agent": self.agent,
            "output": self.output,
            "training_mode": self.training_mode,
            "signals": self.signals,
            "emotion": self.emotion,
            "validations": self.validations,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True)
class QernelEvent:
    """Represents a single event emitted by the qernel."""

    ts: str
    event: str
    payload: Dict[str, Any]

    def to_json(self) -> str:
        body = {
            "ts": self.ts,
            "event": self.event,
            "payload": self.payload,
        }
        return json.dumps(body, ensure_ascii=False, separators=(",", ":"))


class CodexQernel:
    """Manage capsule manifests and operational events for AxQxOS."""

    def __init__(self, config: QernelConfig):
        self.config = config
        self._lock = threading.Lock()
        self._capsules: Dict[str, CapsuleManifest] = {}
        self._last_refresh: Optional[datetime] = None
        self.config.ensure_directories()
        if self.config.auto_refresh:
            self.refresh(emit_event=False)

    # Capsule management -------------------------------------------------
    def refresh(self, *, emit_event: bool = True) -> None:
        """Reload capsule manifests from disk."""

        manifests = discover_capsule_manifests(Path(self.config.capsules_dir))
        mapping = map_capsules_by_id(manifests)
        refreshed_at = datetime.now(timezone.utc)
        with self._lock:
            self._capsules = mapping
            self._last_refresh = refreshed_at
        if emit_event:
            self.record_event(
                "codex.qernel.refreshed",
                {
                    "capsule_count": len(mapping),
                    "capsules": sorted(mapping.keys()),
                },
            )

    def list_capsules(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [manifest.short_dict() for manifest in self._capsules.values()]

    def get_capsule(self, capsule_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            manifest = self._capsules.get(capsule_id)
            return manifest.raw if manifest else None

    # Event handling -----------------------------------------------------
    def record_event(self, event: str, payload: Dict[str, Any]) -> QernelEvent:
        timestamp = datetime.now(timezone.utc).isoformat()
        qernel_event = QernelEvent(ts=timestamp, event=event, payload=payload)
        log_path = Path(self.config.events_log)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(qernel_event.to_json() + "\n")
        return qernel_event

    def read_events(self, *, limit: int = 20) -> List[QernelEvent]:
        log_path = Path(self.config.events_log)
        if not log_path.exists():
            return []
        with log_path.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()
        events: List[QernelEvent] = []
        for raw in lines[-limit:]:
            raw = raw.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
                events.append(
                    QernelEvent(
                        ts=str(data.get("ts", "")),
                        event=str(data.get("event", "")),
                        payload=dict(data.get("payload", {})),
                    )
                )
            except json.JSONDecodeError:
                continue
        return events

    # PSM Gaussian action synthesis --------------------------------------
    def synthesize_gaussian_action(
        self, *, axqos_flow: str, state_id: str = "cfm.qf4"
    ) -> Dict[str, object]:
        """Run Gaussian action synthesis and persist the event payload."""

        state: PSMState = load_psm_state(state_id)
        result: GaussianActionResult = gaussian_action_synth(axqos_flow=axqos_flow, state=state)
        self.record_event(
            "codex.psm.gaussian_action_synthesized",
            {
                "state_id": state.state_id,
                "predicted_action": result.predicted_action,
                "divergence_score": result.divergence_score,
                "confidence": result.confidence,
                "flow_digest": result.flow_digest,
            },
        )
        return result.to_dict()

    # Scrollstream rehearsal ----------------------------------------------
    def emit_scrollstream_rehearsal(
        self,
        *,
        training_mode: bool = True,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> List[Dict[str, Any]]:
        """Emit the rehearsal scrollstream cycle and persist the ledger entries."""

        clock_fn: Callable[[], datetime]
        if clock is not None:
            clock_fn = clock
        else:
            clock_fn = lambda: datetime.now(timezone.utc)

        ledger_path = Path(self.config.scrollstream_ledger)
        ledger_path.parent.mkdir(parents=True, exist_ok=True)

        entries: List[ScrollstreamLedgerEntry] = []
        for stage in REHEARSAL_CYCLE:
            ts = clock_fn().isoformat()
            signals = {
                "hud_shimmer": "emission-confirmed",
                "replay_glyph": "pulse",
                "training_overlay": "deterministic" if training_mode else "live",
            }
            entry = ScrollstreamLedgerEntry(
                ts=ts,
                capsule_id=SCROLLSTREAM_CAPSULE_ID,
                cycle=stage["cycle"],
                agent=stage["agent"],
                output=stage["output"],
                training_mode=training_mode,
                signals=signals,
                emotion=stage["emotion"],
                validations=["sabrina.spark"],
            )
            entries.append(entry)

        with ledger_path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(entry.to_json() + "\n")

        self.record_event(
            "codex.scrollstream.rehearsal",
            {
                "capsule_id": SCROLLSTREAM_CAPSULE_ID,
                "training_mode": training_mode,
                "stages": [stage["cycle"] for stage in REHEARSAL_CYCLE],
                "ledger_path": ledger_path.as_posix(),
            },
        )

        return [entry.to_dict() for entry in entries]

    def read_scrollstream_ledger(self, *, limit: int = 10) -> List[Dict[str, Any]]:
        """Return recent rehearsal ledger entries for HUD replay."""

        ledger_path = Path(self.config.scrollstream_ledger)
        if not ledger_path.exists():
            return []
        with ledger_path.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()
        entries: List[Dict[str, Any]] = []
        for raw in lines[-limit:]:
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(entry, dict):
                continue
            entries.append(entry)
        return entries

    # Health -------------------------------------------------------------
    def health_status(self) -> Dict[str, Any]:
        with self._lock:
            refresh_at = self._last_refresh.isoformat() if self._last_refresh else None
            capsule_ids = sorted(self._capsules.keys())
        status = {
            "status": "ok",
            "os": self.config.os_name,
            "qernel_version": self.config.qernel_version,
            "capsules_loaded": len(capsule_ids),
            "capsules": capsule_ids,
            "last_refresh": refresh_at,
        }
        return status

    # Geodesic terminal modeling ----------------------------------------
    def model_geodesic_terminal(
        self,
        *,
        bridge_name: str = "AxQxOS bridge terminal",
        anchors: Optional[List[str]] = None,
        span: float = 120.0,
        tension: float = 0.82,
    ) -> Dict[str, Any]:
        """Create a geodesic terminal blueprint and record the event."""

        anchor_list = anchors or ["origin", "terminus"]
        model: GeodesicTerminalModel = build_geodesic_terminal(
            bridge_name=bridge_name,
            os_name=self.config.os_name,
            anchors=anchor_list,
            span=span,
            tension=tension,
        )

        self.record_event(
            "codex.bridge.geodesic.modeled",
            {
                "bridge_name": bridge_name,
                "anchors": model.anchors,
                "span": span,
                "tension": tension,
                "segments": len(model.segments),
            },
        )

        return model.to_dict()

# A2A_MCP/orchestrator/stateflow.py
"""
Stateflow / FSM for A2A_MCP

This implementation hardens the original stateflow with:
- thread-safety (RLock)
- explicit persistence hook (persistence_callback)
- serialization / deserialization (to_dict / from_dict)
- clear retry semantics and override auditing
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Callable, Dict, List, Optional, Any
import time
import threading
import json


class State(str, Enum):
    IDLE = "IDLE"
    SCHEDULED = "SCHEDULED"
    EXECUTING = "EXECUTING"
    EVALUATING = "EVALUATING"
    RETRY = "RETRY"
    REPAIR = "REPAIR"
    TERMINATED_SUCCESS = "TERMINATED_SUCCESS"
    TERMINATED_FAIL = "TERMINATED_FAIL"


@dataclass
class TransitionRecord:
    from_state: State
    to_state: State
    event: str
    timestamp: float = field(default_factory=time.time)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "event": self.event,
            "timestamp": self.timestamp,
            "meta": json.loads(json.dumps(self.meta, default=str)),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "TransitionRecord":
        return TransitionRecord(
            from_state=State(d["from_state"]),
            to_state=State(d["to_state"]),
            event=d["event"],
            timestamp=d.get("timestamp", time.time()),
            meta=d.get("meta", {}),
        )


class PartialVerdict(Exception):
    """Raised by a policy to indicate a partial verdict (i.e. RETRY)."""


class StateMachine:
    """
    Finite state machine that enforces the Stateflow / StateChart rules.

    persistence_callback: Optional[Callable[[plan_id: str, state_dict: dict], None]]
      - Called after every committed transition so the caller can persist FSM snapshots.

    Note: to keep the FSM lightweight and testable, persistence is handled via
    a caller-supplied callback rather than embedding DB logic here.
    """

    def __init__(self, max_retries: int = 3, persistence_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None):
        self.state: State = State.IDLE
        self.history: List[TransitionRecord] = []
        self.attempts: int = 0
        self.max_retries = int(max_retries)
        self.callbacks: Dict[State, List[Callable[[TransitionRecord], None]]] = {}
        self._lock = threading.RLock()
        self._persistence_callback = persistence_callback  # optional hook
        # optional plan id the FSM may be associated with (useful for persistence)
        self.plan_id: Optional[str] = None

    # event -> (allowed_from_states, to_state)
    _TRANSITIONS: Dict[str, Any] = {
        "OBJECTIVE_INGRESS": ([State.IDLE], State.SCHEDULED),
        "RUN_DISPATCHED": ([State.SCHEDULED], State.EXECUTING),
        "EXECUTION_COMPLETE": ([State.EXECUTING], State.EVALUATING),
        "EXECUTION_ERROR": ([State.EXECUTING], State.REPAIR),
        "VERDICT_PASS": ([State.EVALUATING], State.TERMINATED_SUCCESS),
        "VERDICT_PARTIAL": ([State.EVALUATING], State.RETRY),
        "VERDICT_FAIL": ([State.EVALUATING], State.TERMINATED_FAIL),
        "RETRY_DISPATCHED": ([State.RETRY], State.EXECUTING),
        "RETRY_LIMIT_EXCEEDED": ([State.RETRY], State.TERMINATED_FAIL),
        "REPAIR_COMPLETE": ([State.REPAIR], State.EXECUTING),
        "REPAIR_ABORT": ([State.REPAIR], State.TERMINATED_FAIL),
    }

    _OVERRIDE_TARGETS = {
        State.TERMINATED_SUCCESS,
        State.TERMINATED_FAIL,
        State.EXECUTING,
        State.EVALUATING,
        State.REPAIR,
        State.RETRY,
        State.SCHEDULED,
    }

    def register_callback(self, state: State, fn: Callable[[TransitionRecord], None]) -> None:
        """
        Register a callback to be invoked when the FSM enters `state`.
        The callback receives the TransitionRecord.
        """
        with self._lock:
            self.callbacks.setdefault(state, []).append(fn)

    def _record(self, from_state: State, to_state: State, event: str, meta: Optional[Dict[str, Any]] = None) -> TransitionRecord:
        rec = TransitionRecord(from_state=from_state, to_state=to_state, event=event, meta=meta or {})
        self.history.append(rec)
        return rec

    def _enter_state(self, rec: TransitionRecord) -> None:
        self.state = rec.to_state
        # persist snapshot after entering state
        if self._persistence_callback and callable(self._persistence_callback):
            try:
                snapshot = self.to_dict()
                if self.plan_id:
                    self._persistence_callback(self.plan_id, snapshot)
                else:
                    # allow persistence without plan_id by passing None
                    self._persistence_callback(None, snapshot)
            except Exception:
                # persistence errors should not crash the state machine
                pass

        for cb in list(self.callbacks.get(rec.to_state, [])):
            try:
                cb(rec)
            except Exception:
                # callbacks must not crash the state machine
                pass

    def trigger(self, event: str, **meta) -> TransitionRecord:
        """
        Trigger an event synchronously. Returns the TransitionRecord.

        Raises ValueError if the event is unknown or not valid in the current
        state.
        """
        with self._lock:
            if event not in self._TRANSITIONS:
                raise ValueError(f"Unknown event: {event}")

            valid_from, to_state = self._TRANSITIONS[event]
            if self.state not in valid_from:
                raise ValueError(f"Event '{event}' not valid from state {self.state}")

            # Special logic for retries
            if event == "VERDICT_PARTIAL":
                # entering RETRY increments attempts
                self.attempts += 1
                # if we've just reached or exceeded max_retries, escalate
                if self.attempts >= self.max_retries:
                    rec = self._record(self.state, State.TERMINATED_FAIL, "RETRY_LIMIT_EXCEEDED", meta)
                    self._enter_state(rec)
                    return rec

            if event == "RETRY_DISPATCHED":
                # reset attempts once retry is dispatched
                self.attempts = 0

            if event == "VERDICT_PASS":
                # upon pass, reset attempts
                self.attempts = 0

            rec = self._record(self.state, to_state, event, meta)
            self._enter_state(rec)
            return rec

    def evaluate_apply_policy(self, policy_fn: Callable[[], bool], **meta) -> TransitionRecord:
        """
        Representative inner transition for EVALUATING -> APPLY_POLICY.

        If policy_ok is True, emit VERDICT_PASS otherwise VERDICT_FAIL.
        If the policy wishes to request a retry, it may raise PartialVerdict.
        """
        with self._lock:
            if self.state != State.EVALUATING:
                raise ValueError("apply_policy may only be executed from EVALUATING state")
            try:
                ok = bool(policy_fn())
            except PartialVerdict:
                return self.trigger("VERDICT_PARTIAL", **meta)
            return self.trigger("VERDICT_PASS" if ok else "VERDICT_FAIL", **meta)

    def override(self, to_state: State, reason: str = "manual_override", override_by: Optional[str] = None, forward_only: bool = True) -> TransitionRecord:
        """
        Force the state machine into `to_state` via an OVERRIDE event.

        The FigJam board marks the OVERRIDE event as forward-only; we
        therefore allow overrides only to the configured override targets
        and optionally prevent overriding from terminated states when
        forward_only is True.
        """
        with self._lock:
            if to_state not in self._OVERRIDE_TARGETS:
                raise ValueError(f"Cannot override to {to_state}")

            if forward_only and self.state in (State.TERMINATED_SUCCESS, State.TERMINATED_FAIL):
                raise ValueError("Cannot override from a terminated state when forward_only=True")

            meta = {"reason": reason}
            if override_by:
                meta["override_by"] = override_by

            rec = self._record(self.state, to_state, "OVERRIDE_EVENT", meta)
            self._enter_state(rec)
            return rec

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize FSM snapshot to a JSON-friendly dict.
        """
        with self._lock:
            return {
                "plan_id": self.plan_id,
                "state": self.state.value,
                "attempts": self.attempts,
                "max_retries": self.max_retries,
                "history": [tr.to_dict() for tr in self.history],
            }

    @staticmethod
    def from_dict(d: Dict[str, Any], persistence_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None) -> "StateMachine":
        """
        Reconstruct a StateMachine from a snapshot created by to_dict().
        """
        sm = StateMachine(max_retries=d.get("max_retries", 3), persistence_callback=persistence_callback)
        sm.plan_id = d.get("plan_id")
        sm.state = State(d["state"])
        sm.attempts = int(d.get("attempts", 0))
        sm.history = [TransitionRecord.from_dict(h) for h in d.get("history", [])]
        return sm

    def current_state(self) -> State:
        with self._lock:
            return self.state

    def clear_history(self) -> None:
        with self._lock:
            self.history = []

    def __repr__(self) -> str:
        return f"<StateMachine state={self.state} attempts={self.attempts} history_len={len(self.history)}>"

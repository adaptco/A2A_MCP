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

from dataclasses import dataclass, field
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
        self._persistence_callback = persistence_callback
        self.plan_id: Optional[str] = None

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
        with self._lock:
            self.callbacks.setdefault(state, []).append(fn)

    def _record(self, from_state: State, to_state: State, event: str, meta: Optional[Dict[str, Any]] = None) -> TransitionRecord:
        rec = TransitionRecord(from_state=from_state, to_state=to_state, event=event, meta=meta or {})
        self.history.append(rec)
        return rec

    def _enter_state(self, rec: TransitionRecord) -> List[Callable[[TransitionRecord], None]]:
        self.state = rec.to_state
        return list(self.callbacks.get(rec.to_state, []))

    def _persist_snapshot(self, snapshot: Dict[str, Any], plan_id: Optional[str]) -> None:
        if self._persistence_callback and callable(self._persistence_callback):
            try:
                self._persistence_callback(plan_id, snapshot)
            except Exception:
                pass

    def _run_post_transition(self, rec: TransitionRecord, callbacks: List[Callable[[TransitionRecord], None]], snapshot: Dict[str, Any], plan_id: Optional[str]) -> None:
        self._persist_snapshot(snapshot, plan_id)
        for cb in callbacks:
            try:
                cb(rec)
            except Exception:
                pass

    def trigger(self, event: str, **meta) -> TransitionRecord:
        with self._lock:
            if event not in self._TRANSITIONS:
                raise ValueError(f"Unknown event: {event}")

            valid_from, to_state = self._TRANSITIONS[event]
            if self.state not in valid_from:
                raise ValueError(f"Event '{event}' not valid from state {self.state}")

            if event == "VERDICT_PARTIAL":
                self.attempts += 1
                if self.attempts >= self.max_retries:
                    rec = self._record(self.state, State.TERMINATED_FAIL, "RETRY_LIMIT_EXCEEDED", meta)
                    callbacks = self._enter_state(rec)
                    snapshot = self.to_dict()
                    plan_id = self.plan_id
                else:
                    rec = self._record(self.state, to_state, event, meta)
                    callbacks = self._enter_state(rec)
                    snapshot = self.to_dict()
                    plan_id = self.plan_id
            else:
                # Do not reset attempts on RETRY_DISPATCHED; only reset after PASS.
                if event == "VERDICT_PASS":
                    self.attempts = 0
                rec = self._record(self.state, to_state, event, meta)
                callbacks = self._enter_state(rec)
                snapshot = self.to_dict()
                plan_id = self.plan_id

        self._run_post_transition(rec, callbacks, snapshot, plan_id)
        return rec

    def evaluate_apply_policy(self, policy_fn: Callable[[], bool], **meta) -> TransitionRecord:
        with self._lock:
            if self.state != State.EVALUATING:
                raise ValueError("apply_policy may only be executed from EVALUATING state")
            try:
                ok = bool(policy_fn())
            except PartialVerdict:
                return self.trigger("VERDICT_PARTIAL", **meta)
            return self.trigger("VERDICT_PASS" if ok else "VERDICT_FAIL", **meta)

    def override(self, to_state: State, reason: str = "manual_override", override_by: Optional[str] = None, forward_only: bool = True) -> TransitionRecord:
        with self._lock:
            if to_state not in self._OVERRIDE_TARGETS:
                raise ValueError(f"Cannot override to {to_state}")
            if forward_only and self.state in (State.TERMINATED_SUCCESS, State.TERMINATED_FAIL):
                raise ValueError("Cannot override from a terminated state when forward_only=True")

            meta = {"reason": reason}
            if override_by:
                meta["override_by"] = override_by

            rec = self._record(self.state, to_state, "OVERRIDE_EVENT", meta)
            callbacks = self._enter_state(rec)
            snapshot = self.to_dict()
            plan_id = self.plan_id

        self._run_post_transition(rec, callbacks, snapshot, plan_id)
        return rec

    def to_dict(self) -> Dict[str, Any]:
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

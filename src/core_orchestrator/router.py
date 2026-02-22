"""Event routing primitives for the core orchestrator.

The router binds parsers – components that emit :class:`Event` objects – to
sinks, which are responsible for shipping those events to external systems.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import TYPE_CHECKING, Any, Dict, Iterable, MutableSequence, Optional, Protocol, Sequence

if TYPE_CHECKING:
    from .world_model import WorldModelIngress

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Event:
    """A normalized payload emitted by a parser.

    Attributes
    ----------
    source:
        A human readable identifier for the system that produced the event.
    type:
        The semantic type of the event.  Sinks can opt-in to particular types
        and ignore the rest.
    payload:
        The normalized payload that downstream sinks will consume.  The router
        treats this as an opaque mapping.
    raw:
        Optional raw metadata from the parser.  This is useful for debugging or
        when a sink requires fields that are not part of the normalized
        payload.
    tags:
        A set of arbitrary labels attached to the event.  Tags can be used to
        implement coarse routing rules without inspecting the payload.
    """

    source: str
    type: str
    payload: Dict[str, Any]
    raw: Optional[Dict[str, Any]] = None
    tags: set[str] = field(default_factory=set)

    def copy(self, **overrides: Any) -> "Event":
        """Return a shallow copy of the event with optional field overrides."""

        data = {
            "source": self.source,
            "type": self.type,
            "payload": dict(self.payload),
            "raw": None if self.raw is None else dict(self.raw),
            "tags": set(self.tags),
        }
        data.update(overrides)
        return Event(**data)


class Parser(Protocol):
    """Protocol representing a producer of normalized events."""

    name: str

    def fetch_events(self) -> Iterable[Event]:
        """Yield normalized events ready for routing."""


class Sink(Protocol):
    """Protocol that must be implemented by delivery sinks."""

    name: str

    def handles(self, event: Event) -> bool:
        """Return ``True`` if the sink wants to process ``event``."""

    def send(self, event: Event) -> Any:
        """Deliver ``event`` to the sink.

        Implementations may return auxiliary data such as request payloads to
        aid in debugging, but the router does not rely on a specific return
        type.
        """


class Router:
    """Coordinate event flow between parsers and sinks."""

    def __init__(
        self,
        parsers: Optional[Sequence[Parser]] = None,
        sinks: Optional[Sequence[Sink]] = None,
        *,
        logger: Optional[logging.Logger] = None,
        sentinel: Optional["Sentinel"] = None,
        ingress: Optional["WorldModelIngress"] = None,
    ) -> None:
        self._parsers: MutableSequence[Parser] = list(parsers or [])
        self._sinks: MutableSequence[Sink] = list(sinks or [])
        self._logger = logger or logging.getLogger(self.__class__.__name__)
        self._sentinel = sentinel
        self._ingress = ingress

    # ------------------------------------------------------------------
    # Registration helpers
    def add_parser(self, parser: Parser) -> None:
        """Register ``parser`` for subsequent dispatch cycles."""

        self._parsers.append(parser)
        self._logger.debug("Registered parser %s", parser.name)

    def add_sink(self, sink: Sink) -> None:
        """Register ``sink`` for subsequent dispatch cycles."""

        self._sinks.append(sink)
        self._logger.debug("Registered sink %s", sink.name)

    @property
    def parsers(self) -> Sequence[Parser]:
        return tuple(self._parsers)

    @property
    def sinks(self) -> Sequence[Sink]:
        return tuple(self._sinks)

    # ------------------------------------------------------------------
    def dispatch(self, *, limit: Optional[int] = None) -> int:
        """Consume events from each parser and fan them out to interested sinks.

        Parameters
        ----------
        limit:
            Optional hard cap on the number of events processed in this
            dispatch cycle.

        Returns
        -------
        int
            The number of events processed across all parsers.
        """

        processed = 0
        for parser in self._parsers:
            for event in parser.fetch_events():
                processed += 1
                self._deliver(event, parser)
                if limit is not None and processed >= limit:
                    return processed
        return processed

    # ------------------------------------------------------------------
    def _deliver(self, event: Event, parser: Parser) -> None:
        """Deliver ``event`` to all sinks that opt-in."""

        routed_event = event
        if self._ingress is not None:
            decision = self._ingress.gate_event(event)
            world_model = {
                "embedding": list(decision.event_embedding),
                "scores": [
                    {
                        "agent_id": score.agent_id,
                        "score": score.score,
                        "accepted": score.accepted,
                    }
                    for score in decision.scores
                ],
                "routed_agent_ids": list(decision.routed_agent_ids),
            }
            raw = dict(routed_event.raw or {})
            raw["world_model"] = world_model
            routed_event = routed_event.copy(raw=raw)

        self._record_with_sentinel(routed_event, parser)
        accepted = False
        for sink in self._sinks:
            if not sink.handles(routed_event):
                continue
            accepted = True
            try:
                sink.send(routed_event)
            except Exception:  # pragma: no cover - defensive logging
                self._logger.exception(
                    "Sink %s failed to handle %s event emitted by %s",
                    sink.name,
                    routed_event.type,
                    parser.name,
                )
        if not accepted:
            self._logger.debug(
                "No sinks accepted event %s emitted by parser %s", routed_event.type, parser.name
            )

    # ------------------------------------------------------------------
    def _record_with_sentinel(self, event: Event, parser: Parser) -> None:
        if self._sentinel is None:
            return
        try:
            self._sentinel.record(event)
        except Exception:  # pragma: no cover - defensive log for sentinel failures
            self._logger.exception(
                "Sentinel failed to record %s event emitted by %s",
                event.type,
                parser.name,
            )


class Sentinel(Protocol):
    """Protocol describing the SSOT sentinel contract."""

    def record(self, event: Event) -> Any:
        """Persist ``event`` in the sentinel."""


__all__ = ["Event", "Parser", "Router", "Sink", "Sentinel"]

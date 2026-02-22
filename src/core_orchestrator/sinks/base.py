"""Common sink primitives."""
from __future__ import annotations

import logging
from typing import Optional, Sequence

from ..router import Event


class BaseSink:
    """Base class that implements routing helpers for sinks."""

    name = "base"

    def __init__(
        self,
        *,
        supported_event_types: Optional[Sequence[str]] = None,
        dry_run: bool = True,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._supported_event_types = set(supported_event_types or [])
        self.dry_run = dry_run
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    def handles(self, event: Event) -> bool:
        if not self._supported_event_types:
            return True
        return event.type in self._supported_event_types

    # ------------------------------------------------------------------
    def send(self, event: Event):
        if not self.handles(event):
            raise ValueError(f"Sink {self.name} does not accept event type {event.type!r}")
        return self._send(event)

    # ------------------------------------------------------------------
    def _send(self, event: Event):  # pragma: no cover - abstract method
        raise NotImplementedError


__all__ = ["BaseSink"]

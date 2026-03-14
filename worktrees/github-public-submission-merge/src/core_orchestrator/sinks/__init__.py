"""Sink implementations for the core orchestrator."""

from .base import BaseSink
from .google_calendar import GoogleCalendarSink
from .notion import NotionSink
from .shopify import ShopifySink

__all__ = [
    "BaseSink",
    "GoogleCalendarSink",
    "NotionSink",
    "ShopifySink",
]

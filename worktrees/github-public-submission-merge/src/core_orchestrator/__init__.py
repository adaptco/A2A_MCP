"""Core orchestrator package for routing parsed events to downstream sinks."""

from .cli import main
from .databases import OrganizeSentinel
from .github_dispatch import make_tx_id, send_block
from .parsers import DiscordMessage, DiscordParser
from .router import Event, Router
from .world_model import IngressDecision, WorldModelIngress, normalized_dot_product
from .sinks import GoogleCalendarSink, NotionSink, ShopifySink

__all__ = [
    "DiscordMessage",
    "DiscordParser",
    "Event",
    "make_tx_id",
    "GoogleCalendarSink",
    "NotionSink",
    "OrganizeSentinel",
    "Router",
    "send_block",
    "ShopifySink",
    "main",
    "IngressDecision",
    "WorldModelIngress",
    "normalized_dot_product",
]
__version__ = "0.1.0"

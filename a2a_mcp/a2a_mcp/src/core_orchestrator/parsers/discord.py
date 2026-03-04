"""Discord parser implementation.

The real Discord API is intentionally abstracted behind a simple iterable so
that unit tests and local runs can operate with static payloads.  The parser
is responsible for normalizing those payloads into :class:`Event` objects that
sinks can reason about without speaking Discord's dialect.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

from ..router import Event

log = logging.getLogger(__name__)


def _parse_timestamp(value: Any) -> datetime:
    """Coerce ``value`` into an aware :class:`datetime` in UTC."""

    if isinstance(value, datetime):
        return value.astimezone(UTC)
    if value is None:
        return datetime.now(tz=UTC)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str):
        cleaned = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    raise TypeError(f"Unsupported timestamp value: {value!r}")


@dataclass(slots=True)
class DiscordMessage:
    """Representation of a Discord message we care about."""

    id: str
    content: str
    author: str
    channel: str
    created_at: datetime
    url: str | None = None
    metadata: MutableMapping[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        """Return a normalized payload that downstream sinks can consume."""

        return {
            "id": self.id,
            "content": self.content,
            "author": self.author,
            "channel": self.channel,
            "created_at": self.created_at.isoformat(),
            "url": self.url,
            **{k: v for k, v in self.metadata.items() if k not in {"event_type"}},
        }

    def to_raw(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


class DiscordParser:
    """Normalize Discord messages into :class:`Event` instances."""

    name = "discord"

    def __init__(
        self,
        messages: Sequence[Mapping[str, Any] | DiscordMessage],
        *,
        channel_whitelist: Sequence[str] | None = None,
        default_event_type: str = "message.created",
    ) -> None:
        self._messages = [self._coerce(message) for message in messages]
        self._channels = {channel.lower() for channel in channel_whitelist or []}
        self._default_event_type = default_event_type

    # ------------------------------------------------------------------
    @classmethod
    def from_json(cls, path: str | Path, **kwargs: Any) -> "DiscordParser":
        """Load Discord messages from a JSON file.

        The loader accepts either an array of messages or an object with a
        top-level ``messages`` key that contains the array.
        """

        payload = json.loads(Path(path).read_text())
        if isinstance(payload, Mapping):
            messages = payload.get("messages", [])
        else:
            messages = payload
        if not isinstance(messages, Sequence):
            raise TypeError("Expected the JSON payload to contain a sequence of messages")
        return cls(messages, **kwargs)

    @staticmethod
    def demo_messages() -> list[dict[str, Any]]:
        """Return a small set of canned messages for quick local runs."""

        now = datetime.now(tz=UTC)
        return [
            {
                "id": "example-1",
                "content": "Kickoff with ACME Corp on Tuesday at 9am",
                "author": "Alice",
                "channel": "sales",
                "created_at": now.isoformat(),
                "url": "https://discordapp.com/channels/demo/1",
                "scheduled_for": (now.replace(hour=9, minute=0, second=0, microsecond=0)).isoformat(),
                "duration_minutes": 60,
            },
            {
                "id": "example-2",
                "content": "Create product brief for spring campaign",
                "author": "Bob",
                "channel": "marketing",
                "created_at": now.isoformat(),
                "url": "https://discordapp.com/channels/demo/2",
                "event_type": "task.created",
                "priority": "high",
            },
        ]

    # ------------------------------------------------------------------
    def fetch_events(self) -> Iterable[Event]:
        """Yield normalized events for consumption by sinks."""

        for message in self._messages:
            if self._channels and message.channel.lower() not in self._channels:
                log.debug("Skipping message %s because channel %s is not whitelisted", message.id, message.channel)
                continue
            event_type = message.metadata.get("event_type", self._default_event_type)
            payload = message.to_payload()
            yield Event(
                source=self.name,
                type=event_type,
                payload=payload,
                raw={"discord": message.to_raw()},
            )

    # ------------------------------------------------------------------
    @staticmethod
    def _coerce(message: Mapping[str, Any] | DiscordMessage) -> DiscordMessage:
        if isinstance(message, DiscordMessage):
            return message
        if not isinstance(message, Mapping):
            raise TypeError(f"Cannot coerce {type(message)!r} into a DiscordMessage")
        metadata = {
            key: value
            for key, value in message.items()
            if key
            not in {
                "id",
                "content",
                "author",
                "channel",
                "created_at",
                "timestamp",
                "url",
            }
        }
        created_at = message.get("created_at") or message.get("timestamp")
        return DiscordMessage(
            id=str(message.get("id", "")),
            content=str(message.get("content", "")),
            author=str(message.get("author", "")),
            channel=str(message.get("channel", "")),
            created_at=_parse_timestamp(created_at),
            url=message.get("url"),
            metadata=metadata,
        )


__all__ = ["DiscordMessage", "DiscordParser"]

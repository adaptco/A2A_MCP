"""Google Calendar sink."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
import logging
from typing import Any, Dict, Optional, Sequence

from .base import BaseSink
from ..router import Event


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    if value is None:
        raise ValueError("Calendar events require a start time")
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str):
        cleaned = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    raise TypeError(f"Unsupported datetime value: {value!r}")


class GoogleCalendarSink(BaseSink):
    """Create event payloads that are compatible with Google Calendar."""

    name = "google_calendar"

    def __init__(
        self,
        calendar_id: str,
        *,
        api_token: Optional[str] = None,
        default_duration_minutes: int = 60,
        dry_run: bool = True,
        supported_event_types: Sequence[str] | None = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        super().__init__(
            supported_event_types=supported_event_types or ("message.created", "meeting.created"),
            dry_run=dry_run,
            logger=logger,
        )
        self.calendar_id = calendar_id
        self.api_token = api_token
        self.default_duration_minutes = default_duration_minutes

    # ------------------------------------------------------------------
    def build_event(self, event: Event) -> Dict[str, Any]:
        payload = event.payload
        start_raw = payload.get("scheduled_for") or payload.get("start_time") or payload.get("created_at")
        start_dt = _parse_datetime(start_raw)
        duration = int(payload.get("duration_minutes") or self.default_duration_minutes)
        end_dt = start_dt + timedelta(minutes=duration)

        body: Dict[str, Any] = {
            "summary": payload.get("content") or payload.get("title") or "Untitled Event",
            "start": {"dateTime": start_dt.isoformat()},
            "end": {"dateTime": end_dt.isoformat()},
            "description": payload.get("content"),
            "source": {
                "title": event.source,
                "url": payload.get("url"),
            },
        }
        location = payload.get("location")
        if location:
            body["location"] = str(location)
        attendees = payload.get("attendees")
        if attendees and isinstance(attendees, Sequence):
            body["attendees"] = [
                {"email": attendee} if "@" in str(attendee) else {"displayName": str(attendee)}
                for attendee in attendees
            ]
        return body

    # ------------------------------------------------------------------
    def _send(self, event: Event):
        body = self.build_event(event)
        if self.dry_run or not self.api_token:
            self.logger.info("[dry-run] would insert Google Calendar event: %s", body)
            return body
        raise RuntimeError("Live Google Calendar delivery is not implemented in this sample sink")


__all__ = ["GoogleCalendarSink"]

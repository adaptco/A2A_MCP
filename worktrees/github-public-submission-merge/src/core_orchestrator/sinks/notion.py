"""Notion sink implementation."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Sequence

from .base import BaseSink
from ..router import Event


class NotionSink(BaseSink):
    """Prepare Notion page payloads from orchestrated events."""

    name = "notion"

    def __init__(
        self,
        database_id: str,
        *,
        api_token: Optional[str] = None,
        dry_run: bool = True,
        supported_event_types: Sequence[str] | None = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        super().__init__(
            supported_event_types=supported_event_types or ("message.created", "task.created"),
            dry_run=dry_run,
            logger=logger,
        )
        self.database_id = database_id
        self.api_token = api_token

    # ------------------------------------------------------------------
    def build_payload(self, event: Event) -> Dict[str, Any]:
        payload = event.payload
        title = (payload.get("content") or payload.get("title") or "Untitled").strip()
        created_at = payload.get("created_at")
        properties: Dict[str, Any] = {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": title,
                        }
                    }
                ]
            },
            "Source": {
                "select": {
                    "name": event.source,
                }
            },
        }
        if payload.get("author"):
            properties["Author"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": str(payload["author"]),
                        }
                    }
                ]
            }
        if payload.get("channel"):
            properties["Channel"] = {
                "select": {
                    "name": str(payload["channel"]),
                }
            }
        if created_at:
            properties["Created"] = {
                "date": {"start": created_at},
            }
        if payload.get("priority"):
            properties["Priority"] = {
                "select": {
                    "name": str(payload["priority"]),
                }
            }

        return {
            "parent": {"database_id": self.database_id},
            "properties": properties,
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": payload.get("content", ""),
                                    "link": {"url": payload.get("url")}
                                    if payload.get("url")
                                    else None,
                                },
                            }
                        ]
                    },
                }
            ],
        }

    # ------------------------------------------------------------------
    def _send(self, event: Event):
        payload = self.build_payload(event)
        if self.dry_run or not self.api_token:
            self.logger.info("[dry-run] would create Notion page: %s", payload)
            return payload
        # Real API interactions are intentionally out of scope.  Surfacing a
        # descriptive error keeps the contract honest if someone disables the
        # dry-run safeguards without wiring an SDK.
        raise RuntimeError("Live Notion delivery is not implemented in this sample sink")


__all__ = ["NotionSink"]

"""Shopify sink."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Sequence

from .base import BaseSink
from ..router import Event


class ShopifySink(BaseSink):
    """Transform orchestrated events into Shopify-compatible payloads."""

    name = "shopify"

    def __init__(
        self,
        store_domain: str,
        *,
        access_token: Optional[str] = None,
        dry_run: bool = True,
        supported_event_types: Sequence[str] | None = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        super().__init__(
            supported_event_types=supported_event_types or ("task.created", "message.created"),
            dry_run=dry_run,
            logger=logger,
        )
        self.store_domain = store_domain
        self.access_token = access_token

    # ------------------------------------------------------------------
    def build_payload(self, event: Event) -> Dict[str, Any]:
        payload = event.payload
        tags = sorted(set(event.tags)) if event.tags else []
        attributes = []
        if payload.get("channel"):
            attributes.append({"name": "Channel", "value": payload["channel"]})
        if payload.get("author"):
            attributes.append({"name": "Author", "value": payload["author"]})
        if payload.get("priority"):
            attributes.append({"name": "Priority", "value": payload["priority"]})

        note = {
            "summary": payload.get("content") or payload.get("title") or "Untitled Shopify Task",
            "source": event.source,
            "body": payload.get("content"),
            "external_id": payload.get("id"),
            "metadata": attributes,
            "tags": tags,
        }
        url = payload.get("url")
        if url:
            note["reference_url"] = url
        return note

    # ------------------------------------------------------------------
    def _send(self, event: Event):
        note = self.build_payload(event)
        if self.dry_run or not self.access_token:
            self.logger.info("[dry-run] would upsert Shopify note: %s", note)
            return note
        raise RuntimeError("Live Shopify delivery is not implemented in this sample sink")


__all__ = ["ShopifySink"]

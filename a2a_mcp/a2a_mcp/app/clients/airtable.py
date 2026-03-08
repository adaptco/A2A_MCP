from __future__ import annotations

from typing import Any, Dict

import httpx

from ..config import settings


class AirtableClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_id: str | None = None,
        table: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.AIRTABLE_API_KEY
        self.base_id = base_id or settings.AIRTABLE_BASE_ID
        self.table = table or settings.AIRTABLE_TABLE
        self.client = httpx.AsyncClient(
            base_url=f"https://api.airtable.com/v0/{self.base_id}/{self.table}",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def upsert_task(self, record: Dict[str, Any]) -> str:
        resp = await self.client.post("/", json={"records": [{"fields": record}]})
        resp.raise_for_status()
        return resp.json()["records"][0]["id"]

    async def get_task_by_item_id(self, item_id: str) -> Dict[str, Any] | None:
        resp = await self.client.get(
            "/", params={"filterByFormula": f"{{item_id}}='{item_id}'"}
        )
        resp.raise_for_status()
        records = resp.json().get("records", [])
        return records[0] if records else None

    async def update_proposed_fields(
        self, airtable_id: str, fields: Dict[str, Any]
    ) -> None:
        resp = await self.client.patch(
            "/", json={"records": [{"id": airtable_id, "fields": fields}]}
        )
        resp.raise_for_status()

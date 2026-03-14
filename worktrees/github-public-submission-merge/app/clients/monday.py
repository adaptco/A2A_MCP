from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

import httpx

from ..config import settings


class MondayClient:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or settings.MONDAY_TOKEN
        self.client = httpx.AsyncClient(
            base_url="https://api.monday.com/v2",
            headers={"Authorization": self.token},
            trust_env=False,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def get_item(self, board_id: str, item_id: str) -> Dict[str, Any]:
        query = """
        query ($bid:[ID!], $iid:[ID!]) {
          boards(ids:$bid) {
            items_page(query_params:{ids:$iid}) {
              items { id name updated_at group { id title } column_values { id title text type value } subitems { id name } }
            }
          }
        }
        """
        variables = {"bid": board_id, "iid": item_id}
        resp = await self.client.post(
            "/", json={"query": query, "variables": variables}
        )
        resp.raise_for_status()
        data = resp.json()
        items = data["data"]["boards"][0]["items_page"]["items"]
        return items[0] if items else {}

    async def update_status(self, board_id: str, item_id: str, value: str) -> None:
        mutation = """
        mutation($bid:ID!, $iid:ID!, $col:ID!, $val:String!) {
          change_simple_column_value(board_id:$bid, item_id:$iid, column_id:$col, value:$val) { id }
        }
        """
        variables = {"bid": board_id, "iid": item_id, "col": "status", "val": value}
        resp = await self.client.post(
            "/", json={"query": mutation, "variables": variables}
        )
        resp.raise_for_status()

    async def update_dates(
        self, board_id: str, item_id: str, start: date | None, due: date | None
    ) -> None:
        mutation = """
        mutation($bid:ID!, $iid:ID!, $col:ID!, $val:JSON!) {
          change_column_value(board_id:$bid, item_id:$iid, column_id:$col, value:$val) { id }
        }
        """
        value = {}
        if start:
            value["start"] = start.isoformat()
        if due:
            value["end"] = due.isoformat()
        variables = {"bid": board_id, "iid": item_id, "col": "timeline", "val": value}
        resp = await self.client.post(
            "/", json={"query": mutation, "variables": variables}
        )
        resp.raise_for_status()

    async def list_dependencies(self, board_id: str, item_id: str) -> List[str]:
        query = """
        query ($bid:[ID!], $iid:[ID!]) {
          boards(ids:$bid) {
            items_page(query_params:{ids:$iid}) {
              items { dependency_links { item_ids } }
            }
          }
        }
        """
        variables = {"bid": board_id, "iid": item_id}
        resp = await self.client.post(
            "/", json={"query": query, "variables": variables}
        )
        resp.raise_for_status()
        data = resp.json()
        items = data["data"]["boards"][0]["items_page"]["items"]
        if not items:
            return []
        links = items[0].get("dependency_links", [])
        return [str(i) for link in links for i in link.get("item_ids", [])]

    async def create_webhook(self, board_id: str, url: str, event: str) -> str:
        mutation = """
        mutation($bid:ID!, $url:String!, $evt:WebhookEventType!) {
          create_webhook(board_id:$bid, url:$url, event:$evt) { id }
        }
        """
        variables = {"bid": board_id, "url": url, "evt": event}
        resp = await self.client.post(
            "/", json={"query": mutation, "variables": variables}
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"]["create_webhook"]["id"]

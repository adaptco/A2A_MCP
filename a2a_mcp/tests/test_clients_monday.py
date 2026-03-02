import pytest
import httpx

from app.clients.monday import MondayClient


@pytest.mark.asyncio
async def test_get_item_sends_auth_header():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(
            200,
            json={
                "data": {
                    "boards": [
                        {
                            "items_page": {
                                "items": [{"id": "1", "name": "T", "column_values": []}]
                            }
                        }
                    ]
                }
            },
        )

    transport = httpx.MockTransport(handler)
    client = MondayClient(token="tok")
    client.client._transport = transport
    item = await client.get_item("b", "1")
    assert item["id"] == "1"
    assert captured["auth"] == "tok"
    await client.close()

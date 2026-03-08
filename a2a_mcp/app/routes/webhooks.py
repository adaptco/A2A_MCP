from fastapi import APIRouter, Depends

from ..deps import get_session
from ..clients.monday import MondayClient
from ..services import normalize, sync
from ..schemas.events import MondayWebhookEvent, AirtableWebhookEvent

router = APIRouter()


@router.post("/webhook/monday")
async def webhook_monday(event: MondayWebhookEvent, session=Depends(get_session)):
    client = MondayClient()
    item = await client.get_item(event.board_id, event.item_id)
    task = normalize.normalize_monday_item(item)
    ctx = {"proposed_status": task.status, "actor_system": "monday"}
    await sync.upsert_and_sync(session, task, ctx, client)
    await client.close()
    return {"received": True}


@router.post("/webhook/airtable")
async def webhook_airtable(event: AirtableWebhookEvent, session=Depends(get_session)):
    record = {"id": event.record_id, "fields": event.fields}
    task = normalize.normalize_airtable_record(record)
    ctx = {"proposed_status": task.status, "actor_system": "airtable"}
    await sync.upsert_and_sync(session, task, ctx)
    return {"received": True}

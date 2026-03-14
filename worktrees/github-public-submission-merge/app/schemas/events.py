from pydantic import BaseModel


class MondayWebhookEvent(BaseModel):
    board_id: str
    item_id: str
    event: str


class AirtableWebhookEvent(BaseModel):
    record_id: str
    fields: dict

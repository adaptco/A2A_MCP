from pydantic import BaseModel
from typing import Optional
from enum import Enum

class Status(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    ERROR = "ERROR"

class OpenPoint(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: Status = Status.OPEN

class OpenPointCreate(BaseModel):
    title: str
    description: Optional[str] = None

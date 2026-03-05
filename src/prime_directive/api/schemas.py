from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    run_id: str

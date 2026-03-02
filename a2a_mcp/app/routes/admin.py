from fastapi import APIRouter

router = APIRouter()


@router.post("/admin/resync")
async def resync():  # pragma: no cover - stub
    return {"status": "not implemented"}

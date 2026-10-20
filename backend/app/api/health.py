import anyio
from fastapi import APIRouter, Depends
from supabase import Client

from app.deps import get_supabase
from app.errors import AppError

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
async def health_db(client: Client = Depends(get_supabase)) -> dict[str, str]:
    def _ping() -> None:
        client.table("resumes").select("id", count="exact", head=True).limit(1).execute()

    try:
        await anyio.to_thread.run_sync(_ping)
    except Exception as exc:
        raise AppError(500, "internal_error", "Database is unreachable.") from exc
    return {"status": "ok"}

from fastapi import APIRouter, Depends
from supabase import Client

from app.deps import get_current_user, get_supabase
from app.services.access import load_profile
from app.services.auth import CurrentUser

router = APIRouter(tags=["me"])


@router.get("/me")
async def me(
    user: CurrentUser = Depends(get_current_user),
    client: Client = Depends(get_supabase),
) -> dict[str, str | None]:
    """Works for pending/rejected users too, so the frontend can show the right screen."""
    profile = await load_profile(client, user)
    return {
        "id": user.id,
        "email": user.email,
        "role": profile.get("role") or "user",
        "status": profile.get("status") or "pending",
    }

import logging
import uuid
from typing import Literal

import anyio
from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.deps import get_admin, get_supabase
from app.errors import AppError
from app.repositories import profiles as profiles_repo
from app.schemas.admin import AdminStats, AdminUser
from app.services.access import AccessContext, invalidate_profile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats)
async def admin_stats(
    _: AccessContext = Depends(get_admin),
    client: Client = Depends(get_supabase),
) -> AdminStats:
    counts = await anyio.to_thread.run_sync(profiles_repo.status_counts, client)
    return AdminStats(**counts)


@router.get("/users", response_model=list[AdminUser])
async def admin_users(
    status: Literal["pending", "approved", "rejected"] | None = Query(default=None),
    _: AccessContext = Depends(get_admin),
    client: Client = Depends(get_supabase),
) -> list[AdminUser]:
    rows = await anyio.to_thread.run_sync(profiles_repo.list_users, client, status)
    return [AdminUser.model_validate(r) for r in rows]


async def _change_status(
    client: Client, admin: AccessContext, user_id: str, status: str
) -> AdminUser:
    try:
        target_id = str(uuid.UUID(user_id))
    except ValueError as exc:
        raise AppError(404, "not_found") from exc
    if target_id == admin.actor.id:
        raise AppError(422, "validation_error", "You can't change your own access.")
    target = await anyio.to_thread.run_sync(profiles_repo.get_profile, client, target_id)
    if not target:
        raise AppError(404, "not_found")
    if target.get("role") == "admin" and status != "approved":
        raise AppError(422, "validation_error", "Admins can't be rejected or have access revoked.")
    await anyio.to_thread.run_sync(profiles_repo.set_status, client, target_id, status, admin.actor.id)
    invalidate_profile(target_id)
    logger.info("Admin %s set user %s to %s", admin.actor.id, target_id, status)
    rows = await anyio.to_thread.run_sync(profiles_repo.list_users, client, None)
    row = next((r for r in rows if str(r["id"]) == target_id), None)
    if not row:
        raise AppError(404, "not_found")
    return AdminUser.model_validate(row)


@router.post("/users/{user_id}/approve", response_model=AdminUser)
async def approve_user(
    user_id: str,
    admin: AccessContext = Depends(get_admin),
    client: Client = Depends(get_supabase),
) -> AdminUser:
    return await _change_status(client, admin, user_id, "approved")


@router.post("/users/{user_id}/reject", response_model=AdminUser)
async def reject_user(
    user_id: str,
    admin: AccessContext = Depends(get_admin),
    client: Client = Depends(get_supabase),
) -> AdminUser:
    """Rejects a pending request, or revokes access of an approved user."""
    return await _change_status(client, admin, user_id, "rejected")

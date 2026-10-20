"""Approval gate, admin role and admin "view as user" (read-only impersonation).

`AccessContext.owner_id` is the library being accessed. It equals the caller's own id, except when an
admin sends `X-View-As: <user_id>`; then it is that user's id and the context is read-only. The
caller identity always comes from the verified token (DI-1); the header is honoured only for admins.
"""

import logging
import uuid
from dataclasses import dataclass
from threading import Lock
from typing import Any

import anyio
from cachetools import TTLCache
from supabase import Client

from app.errors import AppError
from app.repositories import profiles as profiles_repo
from app.services.auth import CurrentUser

logger = logging.getLogger(__name__)

_profile_cache: TTLCache[str, dict[str, Any]] = TTLCache(maxsize=4096, ttl=30)
_cache_lock = Lock()


@dataclass(frozen=True)
class AccessContext:
    actor: CurrentUser          # the person making the request
    actor_role: str
    owner_id: str               # whose library is being accessed
    owner_email: str | None
    viewing_as: bool            # True when an admin views another user's library

    @property
    def is_admin(self) -> bool:
        return self.actor_role == "admin"


def invalidate_profile(user_id: str) -> None:
    with _cache_lock:
        _profile_cache.pop(user_id, None)


async def load_profile(client: Client, user: CurrentUser) -> dict[str, Any]:
    with _cache_lock:
        cached = _profile_cache.get(user.id)
    if cached is not None:
        return cached
    profile = await anyio.to_thread.run_sync(profiles_repo.ensure_profile, client, user.id, user.email)
    with _cache_lock:
        _profile_cache[user.id] = profile
    return profile


def require_approved(profile: dict[str, Any]) -> None:
    status = profile.get("status")
    if status == "approved":
        return
    if status == "rejected":
        raise AppError(403, "account_rejected")
    raise AppError(403, "pending_approval")


async def resolve_access(client: Client, user: CurrentUser, view_as: str | None) -> AccessContext:
    profile = await load_profile(client, user)
    require_approved(profile)
    role = profile.get("role") or "user"

    if not view_as or view_as.strip() == user.id:
        return AccessContext(user, role, user.id, user.email, viewing_as=False)

    if role != "admin":
        raise AppError(403, "forbidden")
    try:
        target_id = str(uuid.UUID(view_as.strip()))
    except ValueError as exc:
        raise AppError(404, "not_found") from exc
    target = await anyio.to_thread.run_sync(profiles_repo.get_profile, client, target_id)
    if not target:
        raise AppError(404, "not_found")
    logger.info("Admin %s viewing library of %s", user.id, target_id)
    return AccessContext(user, role, target_id, target.get("email"), viewing_as=True)

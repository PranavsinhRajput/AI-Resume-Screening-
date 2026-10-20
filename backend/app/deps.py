from functools import lru_cache

from fastapi import Depends, Header
from supabase import Client, create_client

from app.config import Settings, get_settings
from app.errors import AppError
from app.services.access import AccessContext, resolve_access
from app.services.auth import CurrentUser, verify_token
from app.services.embeddings import Embedder, get_default_embedder
from app.services.llm import LLMGateway, get_default_llm


@lru_cache
def _supabase_client(url: str, key: str) -> Client:
    return create_client(url, key)


def get_supabase(settings: Settings = Depends(get_settings)) -> Client:
    """Service-role Supabase client. Server only — bypasses RLS, so every query must filter by owner_id."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise AppError(500, "internal_error")
    return _supabase_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


async def get_current_user(
    authorization: str | None = Header(default=None),
    client: Client = Depends(get_supabase),
) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "unauthorized")
    token = authorization.split(" ", 1)[1].strip()
    return await verify_token(client, token)


async def get_access(
    user: CurrentUser = Depends(get_current_user),
    client: Client = Depends(get_supabase),
    x_view_as: str | None = Header(default=None),
) -> AccessContext:
    """Approved user (or admin, optionally viewing another user's library read-only)."""
    return await resolve_access(client, user, x_view_as)


async def get_writable_access(access: AccessContext = Depends(get_access)) -> AccessContext:
    """Like get_access, but refuses changes while an admin is viewing someone else's library."""
    if access.viewing_as:
        raise AppError(403, "read_only")
    return access


async def get_admin(
    user: CurrentUser = Depends(get_current_user),
    client: Client = Depends(get_supabase),
) -> AccessContext:
    access = await resolve_access(client, user, None)
    if not access.is_admin:
        raise AppError(403, "forbidden")
    return access


def get_embedder() -> Embedder:
    return get_default_embedder()


def get_llm() -> LLMGateway:
    return get_default_llm()

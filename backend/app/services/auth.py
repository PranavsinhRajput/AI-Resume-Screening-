import hashlib
import logging
from dataclasses import dataclass
from threading import Lock

import anyio
from cachetools import TTLCache
from supabase import Client

from app.errors import AppError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None


_cache: TTLCache[str, CurrentUser] = TTLCache(maxsize=2048, ttl=60)
_cache_lock = Lock()


def _token_key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _get_user_sync(client: Client, token: str) -> CurrentUser:
    response = client.auth.get_user(token)
    user = getattr(response, "user", None)
    if user is None or not getattr(user, "id", None):
        raise AppError(401, "unauthorized")
    return CurrentUser(id=str(user.id), email=getattr(user, "email", None))


async def verify_token(client: Client, token: str) -> CurrentUser:
    """Verify a Supabase access token. The returned id is the ONLY source of owner_id (DI-1)."""
    if not token:
        raise AppError(401, "unauthorized")
    key = _token_key(token)
    with _cache_lock:
        cached = _cache.get(key)
    if cached is not None:
        return cached
    try:
        user = await anyio.to_thread.run_sync(_get_user_sync, client, token)
    except AppError:
        raise
    except Exception as exc:  # any auth failure is a 401
        logger.info("Token verification failed: %s", type(exc).__name__)
        raise AppError(401, "unauthorized") from exc
    with _cache_lock:
        _cache[key] = user
    return user

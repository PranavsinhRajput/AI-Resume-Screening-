"""Approval gate, admin role and X-View-As rules (no network: the profiles repo is faked)."""

import uuid

import pytest

from app.errors import AppError
from app.services import access
from app.services.auth import CurrentUser

ADMIN = CurrentUser(id=str(uuid.uuid4()), email="admin@x.io")
USER = CurrentUser(id=str(uuid.uuid4()), email="user@x.io")
OTHER = str(uuid.uuid4())


@pytest.fixture
def profiles(monkeypatch):
    store = {
        ADMIN.id: {"id": ADMIN.id, "email": ADMIN.email, "role": "admin", "status": "approved"},
        USER.id: {"id": USER.id, "email": USER.email, "role": "user", "status": "approved"},
        OTHER: {"id": OTHER, "email": "other@x.io", "role": "user", "status": "approved"},
    }
    monkeypatch.setattr(access.profiles_repo, "ensure_profile", lambda _c, uid, _e: store[uid])
    monkeypatch.setattr(access.profiles_repo, "get_profile", lambda _c, uid: store.get(uid))
    access._profile_cache.clear()
    yield store
    access._profile_cache.clear()


async def test_approved_user_gets_own_library(profiles):
    ctx = await access.resolve_access(None, USER, None)
    assert ctx.owner_id == USER.id and not ctx.viewing_as and not ctx.is_admin


@pytest.mark.parametrize("status,code", [("pending", "pending_approval"), ("rejected", "account_rejected")])
async def test_unapproved_user_blocked(profiles, status, code):
    profiles[USER.id]["status"] = status
    with pytest.raises(AppError) as err:
        await access.resolve_access(None, USER, None)
    assert err.value.status_code == 403 and err.value.code == code


async def test_non_admin_cannot_view_as(profiles):
    with pytest.raises(AppError) as err:
        await access.resolve_access(None, USER, OTHER)
    assert err.value.code == "forbidden"


async def test_admin_view_as_switches_owner(profiles):
    ctx = await access.resolve_access(None, ADMIN, OTHER)
    assert ctx.owner_id == OTHER and ctx.viewing_as and ctx.actor.id == ADMIN.id
    assert ctx.owner_email == "other@x.io"


async def test_admin_view_as_unknown_or_invalid_is_404(profiles):
    for target in (str(uuid.uuid4()), "not-a-uuid"):
        with pytest.raises(AppError) as err:
            await access.resolve_access(None, ADMIN, target)
        assert err.value.status_code == 404


async def test_view_as_self_is_normal_access(profiles):
    ctx = await access.resolve_access(None, ADMIN, ADMIN.id)
    assert not ctx.viewing_as and ctx.owner_id == ADMIN.id


async def test_invalidate_profile_picks_up_new_status(profiles):
    profiles[USER.id]["status"] = "pending"
    with pytest.raises(AppError):
        await access.resolve_access(None, USER, None)
    profiles[USER.id] = {**profiles[USER.id], "status": "approved"}
    access.invalidate_profile(USER.id)
    ctx = await access.resolve_access(None, USER, None)
    assert ctx.owner_id == USER.id

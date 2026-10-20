"""Data access for `profiles` (role + approval status). Sync functions; call via anyio.to_thread."""

from datetime import UTC, datetime
from typing import Any

from supabase import Client

COLUMNS = "id,email,role,status,created_at,reviewed_at"


def get_profile(client: Client, user_id: str) -> dict[str, Any] | None:
    res = client.table("profiles").select(COLUMNS).eq("id", user_id).limit(1).execute()
    return res.data[0] if res.data else None


def ensure_profile(client: Client, user_id: str, email: str | None) -> dict[str, Any]:
    """Return the profile, creating a pending one if the signup trigger didn't (e.g. user predates it)."""
    existing = get_profile(client, user_id)
    if existing:
        return existing
    client.table("profiles").upsert(
        {"id": user_id, "email": email}, on_conflict="id", ignore_duplicates=True
    ).execute()
    return get_profile(client, user_id) or {"id": user_id, "email": email, "role": "user", "status": "pending"}


def list_users(client: Client, status: str | None) -> list[dict[str, Any]]:
    res = client.rpc("admin_list_users", {"p_status": status}).execute()
    return list(res.data or [])


def set_status(client: Client, user_id: str, status: str, reviewer_id: str) -> dict[str, Any] | None:
    res = (
        client.table("profiles")
        .update(
            {"status": status, "reviewed_at": datetime.now(UTC).isoformat(), "reviewed_by": reviewer_id}
        )
        .eq("id", user_id)
        .execute()
    )
    return res.data[0] if res.data else None


def status_counts(client: Client) -> dict[str, int]:
    res = client.table("profiles").select("status").execute()
    counts = {"pending": 0, "approved": 0, "rejected": 0}
    for row in res.data or []:
        if row.get("status") in counts:
            counts[row["status"]] += 1
    return counts

"""Thin data access for `resumes` and `experiences`.

Every function that touches user data takes `owner_id` and filters by it (DI-1). These are sync
functions (supabase-py sync client); call them via `anyio.to_thread.run_sync`.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from supabase import Client

SUMMARY_COLUMNS = (
    "id,original_filename,status,error_message,candidate_name,total_experience_months,"
    "skills,location,created_at"
)
DETAIL_COLUMNS = (
    SUMMARY_COLUMNS
    + ",email,phone,links,headline,summary,education,certifications,projects,parse_warnings"
)
STATUSES = ("pending", "processing", "done", "failed")


def count_all(client: Client, owner_id: str) -> int:
    res = (
        client.table("resumes")
        .select("id", count="exact", head=True)
        .eq("owner_id", owner_id)
        .execute()
    )
    return int(res.count or 0)


def status_counts(client: Client, owner_id: str) -> dict[str, int]:
    res = client.table("resumes").select("status").eq("owner_id", owner_id).execute()
    counts = dict.fromkeys(STATUSES, 0)
    for row in res.data or []:
        status = row.get("status")
        if status in counts:
            counts[status] += 1
    return counts


def find_by_hash(client: Client, owner_id: str, file_hash: str) -> dict[str, Any] | None:
    res = (
        client.table("resumes")
        .select("id")
        .eq("owner_id", owner_id)
        .eq("file_hash", file_hash)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def insert_resume(client: Client, owner_id: str, row: dict[str, Any]) -> dict[str, Any]:
    payload = {**row, "owner_id": owner_id, "status": "pending"}
    res = client.table("resumes").insert(payload).execute()
    return res.data[0]


def list_resumes(
    client: Client, owner_id: str, status: str | None, page: int, page_size: int
) -> tuple[list[dict[str, Any]], int]:
    query = (
        client.table("resumes").select(SUMMARY_COLUMNS, count="exact").eq("owner_id", owner_id)
    )
    if status:
        query = query.eq("status", status)
    start = (page - 1) * page_size
    res = query.order("created_at", desc=True).range(start, start + page_size - 1).execute()
    return list(res.data or []), int(res.count or 0)


def get_resume(
    client: Client, owner_id: str, resume_id: str, columns: str = DETAIL_COLUMNS
) -> dict[str, Any] | None:
    res = (
        client.table("resumes")
        .select(columns)
        .eq("owner_id", owner_id)
        .eq("id", resume_id)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def get_resumes_by_ids(
    client: Client, owner_id: str, resume_ids: list[str], columns: str
) -> list[dict[str, Any]]:
    if not resume_ids:
        return []
    res = (
        client.table("resumes")
        .select(columns)
        .eq("owner_id", owner_id)
        .in_("id", resume_ids)
        .execute()
    )
    return list(res.data or [])


def list_experiences(client: Client, owner_id: str, resume_id: str) -> list[dict[str, Any]]:
    res = (
        client.table("experiences")
        .select("company,title,employment_type,start_date,end_date,is_current,location,description")
        .eq("owner_id", owner_id)
        .eq("resume_id", resume_id)
        .order("position")
        .execute()
    )
    return list(res.data or [])


def has_done(client: Client, owner_id: str) -> bool:
    res = (
        client.table("resumes")
        .select("id", count="exact", head=True)
        .eq("owner_id", owner_id)
        .eq("status", "done")
        .execute()
    )
    return int(res.count or 0) > 0


def delete_resume(client: Client, owner_id: str, resume_id: str) -> None:
    client.table("resumes").delete().eq("owner_id", owner_id).eq("id", resume_id).execute()


def update_resume(client: Client, owner_id: str, resume_id: str, fields: dict[str, Any]) -> None:
    client.table("resumes").update(fields).eq("owner_id", owner_id).eq("id", resume_id).execute()


def mark_failed(client: Client, owner_id: str, resume_id: str, message: str) -> None:
    update_resume(client, owner_id, resume_id, {"status": "failed", "error_message": message})


def retry_failed(client: Client, owner_id: str, resume_id: str) -> dict[str, Any] | None:
    res = (
        client.table("resumes")
        .update({"status": "pending", "error_message": None, "processing_started_at": None})
        .eq("owner_id", owner_id)
        .eq("id", resume_id)
        .eq("status", "failed")
        .execute()
    )
    return res.data[0] if res.data else None


def delete_experiences(client: Client, owner_id: str, resume_id: str) -> None:
    client.table("experiences").delete().eq("owner_id", owner_id).eq("resume_id", resume_id).execute()


def insert_experiences(
    client: Client, owner_id: str, resume_id: str, rows: list[dict[str, Any]]
) -> None:
    if not rows:
        return
    payload = [
        {**row, "owner_id": owner_id, "resume_id": resume_id, "position": i}
        for i, row in enumerate(rows)
    ]
    client.table("experiences").insert(payload).execute()


# ---------------- worker-level operations (system scope, not user requests) ----------------


def claim_next(client: Client) -> dict[str, Any] | None:
    res = client.rpc("claim_next_resume", {}).execute()
    data = res.data
    if isinstance(data, list):
        return data[0] if data else None
    return data or None


def requeue_stale(client: Client, stale_minutes: int) -> int:
    cutoff = (datetime.now(UTC) - timedelta(minutes=stale_minutes)).isoformat()
    res = (
        client.table("resumes")
        .update({"status": "pending", "processing_started_at": None})
        .eq("status", "processing")
        .lt("processing_started_at", cutoff)
        .execute()
    )
    return len(res.data or [])

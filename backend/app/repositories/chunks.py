"""Data access for `resume_chunks` and the vector-search RPC functions. Always scoped by owner_id."""

from typing import Any

from supabase import Client

INSERT_BATCH = 50


def delete_chunks(client: Client, owner_id: str, resume_id: str) -> None:
    client.table("resume_chunks").delete().eq("owner_id", owner_id).eq("resume_id", resume_id).execute()


def insert_chunks(
    client: Client,
    owner_id: str,
    resume_id: str,
    chunks: list[dict[str, Any]],
    embeddings: list[list[float]],
) -> None:
    rows = [
        {
            "owner_id": owner_id,
            "resume_id": resume_id,
            "chunk_index": chunk["chunk_index"],
            "section": chunk["section"],
            "content": chunk["content"],
            "embedding": vec,
        }
        for chunk, vec in zip(chunks, embeddings, strict=True)
    ]
    for i in range(0, len(rows), INSERT_BATCH):
        client.table("resume_chunks").insert(rows[i : i + INSERT_BATCH]).execute()


def search_resumes(
    client: Client,
    owner_id: str,
    query_embedding: list[float],
    min_experience_months: int | None,
    max_experience_months: int | None,
    required_skills: list[str] | None,
    location: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    res = client.rpc(
        "search_resumes",
        {
            "p_owner_id": owner_id,
            "p_query_embedding": query_embedding,
            "p_min_experience_months": min_experience_months,
            "p_max_experience_months": max_experience_months,
            "p_required_skills": required_skills or None,
            "p_location": location,
            "p_limit": limit,
        },
    ).execute()
    return list(res.data or [])


def get_top_chunks(
    client: Client,
    owner_id: str,
    resume_ids: list[str],
    query_embedding: list[float],
    per_resume: int = 3,
) -> list[dict[str, Any]]:
    if not resume_ids:
        return []
    res = client.rpc(
        "get_top_chunks",
        {
            "p_owner_id": owner_id,
            "p_resume_ids": resume_ids,
            "p_query_embedding": query_embedding,
            "p_per_resume": per_resume,
        },
    ).execute()
    return list(res.data or [])

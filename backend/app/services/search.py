"""Search orchestration: parse → retrieve → relax → verify → rank (architecture.md §8)."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import anyio
from supabase import Client

from app.config import Settings
from app.errors import AppError
from app.repositories import chunks as chunks_repo
from app.repositories import resumes as resumes_repo
from app.schemas.search import (
    CandidateVerdict,
    Interpretation,
    InterpretationFilters,
    ParsedQuery,
    QueryFilters,
    ResultCriterion,
    SearchResponse,
    SearchResult,
    Snippet,
)
from app.services.embeddings import Embedder
from app.services.llm import LLMGateway, LLMUnavailable
from app.services.query_parser import parse_query
from app.services.verifier import Candidate, verify_candidates

logger = logging.getLogger(__name__)

RELAX_ORDER = ["location", "required_skills", "max_experience_months", "min_experience_months"]
MAX_PARTIAL = 5
SNIPPET_CHARS = 300
CANDIDATE_COLUMNS = (
    "id,original_filename,candidate_name,total_experience_months,location,skills,headline,summary"
)


def format_experience(months: int | None) -> str:
    if months is None:
        return "unknown"
    if months <= 0:
        return "Fresher (0 yrs)"
    years, rem = divmod(months, 12)
    parts = []
    if years:
        parts.append(f"{years} yr" + ("s" if years != 1 else ""))
    if rem:
        parts.append(f"{rem} mo" + ("s" if rem != 1 else ""))
    return " ".join(parts)


def relax_filters(
    filters: QueryFilters,
    retrieve: Callable[[QueryFilters], list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[str], QueryFilters]:
    """Run retrieve(filters); while empty, drop filters in RELAX_ORDER (only ones that are set)."""
    current = filters.model_copy(deep=True)
    pool = retrieve(current)
    relaxed: list[str] = []
    for name in RELAX_ORDER:
        if pool:
            break
        value = getattr(current, name)
        if value in (None, [], ""):
            continue
        setattr(current, name, [] if name == "required_skills" else None)
        relaxed.append(name)
        pool = retrieve(current)
    return pool, relaxed, current


@dataclass
class RankInput:
    resume: dict[str, Any]
    vector_score: float
    chunks: list[dict[str, Any]]  # sorted by score desc


def _snippets(chunks: list[dict[str, Any]]) -> list[Snippet]:
    return [Snippet(section=c["section"], text=c["content"][:SNIPPET_CHARS]) for c in chunks[:2]]


def build_results(
    items: list[RankInput],
    parsed: ParsedQuery,
    verdicts: dict[str, CandidateVerdict] | None,
    top_k: int,
) -> list[SearchResult]:
    """Rank and assemble results. verdicts=None means degraded mode (order by vector score)."""
    required_flags = [c.required for c in parsed.verify_criteria]
    built: list[SearchResult] = []

    for item in items:
        rid = str(item.resume["id"])
        snippets = _snippets(item.chunks)
        best = snippets[0].text if snippets else ""
        fallback_reason = f"Matched on: {best[:160]}" if best else "Matched on overall similarity."

        if verdicts is None:
            criteria = [
                ResultCriterion(criterion=c.text, required=c.required, met=None, evidence=None)
                for c in parsed.verify_criteria
            ]
            score = round(item.vector_score * 100)
            reason = fallback_reason
            meets = True
        else:
            verdict = verdicts.get(rid)
            if verdict is None:
                criteria = [
                    ResultCriterion(criterion=c.text, required=c.required, met=None, evidence=None)
                    for c in parsed.verify_criteria
                ]
                score = round(item.vector_score * 100)
                reason = fallback_reason
            else:
                criteria = [
                    ResultCriterion(
                        criterion=parsed.verify_criteria[i].text,
                        required=required_flags[i],
                        met=chk.met,
                        evidence=chk.evidence,
                    )
                    for i, chk in enumerate(verdict.criteria[: len(parsed.verify_criteria)])
                ]
                score = verdict.match_score
                reason = verdict.reason.strip() or fallback_reason
            meets = all(c.met is True for c in criteria if c.required)

        built.append(
            SearchResult(
                rank=0,
                resume_id=rid,
                candidate_name=item.resume.get("candidate_name"),
                original_filename=item.resume.get("original_filename") or "",
                total_experience_months=item.resume.get("total_experience_months"),
                location=item.resume.get("location"),
                skills=list(item.resume.get("skills") or []),
                match_score=max(0, min(100, int(score))),
                vector_score=float(item.vector_score),
                reason=reason,
                meets_all_required=meets,
                criteria=criteria,
                snippets=snippets,
            )
        )

    if verdicts is None:
        built.sort(key=lambda r: -r.vector_score)
    else:
        built.sort(key=lambda r: (not r.meets_all_required, -r.match_score, -r.vector_score))

    full = [r for r in built if r.meets_all_required][:top_k]
    partial = [r for r in built if not r.meets_all_required][:MAX_PARTIAL]
    results = full + partial
    for i, r in enumerate(results, start=1):
        r.rank = i
    return results


async def run_search(
    *,
    owner_id: str,
    query: str,
    top_k: int,
    client: Client,
    settings: Settings,
    llm: LLMGateway,
    embedder: Embedder,
) -> SearchResponse:
    # 1. Guard
    if not await anyio.to_thread.run_sync(resumes_repo.has_done, client, owner_id):
        raise AppError(409, "no_resumes_ready")

    # 2. Parse
    outcome = await parse_query(llm, query)
    parsed = outcome.parsed

    # 3. Embed query
    qvec = await anyio.to_thread.run_sync(embedder.embed_query, parsed.semantic_query)

    # 4–5. Retrieve with relaxation
    def _retrieve(f: QueryFilters) -> list[dict[str, Any]]:
        return chunks_repo.search_resumes(
            client,
            owner_id,
            qvec,
            f.min_experience_months,
            f.max_experience_months,
            f.required_skills or None,
            f.location,
            settings.SEARCH_CANDIDATE_POOL,
        )

    pool, relaxed, _ = await anyio.to_thread.run_sync(relax_filters, parsed.filters, _retrieve)

    interpretation = Interpretation(
        summary=parsed.interpretation_summary,
        filters=InterpretationFilters(**parsed.filters.model_dump()),
        preferred_skills=parsed.preferred_skills,
        semantic_query=parsed.semantic_query,
        verify_criteria=parsed.verify_criteria,
        unsupported=parsed.unsupported,
        relaxed_filters=relaxed,
        used_raw_query=outcome.used_raw_query,
    )
    response = SearchResponse(
        query=query,
        interpretation=interpretation,
        parse_degraded=outcome.parse_degraded,
        candidates_considered=len(pool),
    )
    if not pool:
        return response

    scores = {str(p["resume_id"]): float(p["score"]) for p in pool}
    ids = list(scores.keys())

    # 6. Top chunks + resume rows (both owner-scoped)
    chunk_rows = await anyio.to_thread.run_sync(
        chunks_repo.get_top_chunks, client, owner_id, ids, qvec, 3
    )
    resume_rows = await anyio.to_thread.run_sync(
        resumes_repo.get_resumes_by_ids, client, owner_id, ids, CANDIDATE_COLUMNS
    )
    resumes_by_id = {str(r["id"]): r for r in resume_rows}
    chunks_by_id: dict[str, list[dict[str, Any]]] = {}
    for c in chunk_rows:
        chunks_by_id.setdefault(str(c["resume_id"]), []).append(c)
    for lst in chunks_by_id.values():
        lst.sort(key=lambda c: -float(c.get("score") or 0))

    items = [
        RankInput(resume=resumes_by_id[rid], vector_score=scores[rid], chunks=chunks_by_id.get(rid, []))
        for rid in ids
        if rid in resumes_by_id
    ]

    # 7. Verify
    candidates = [
        Candidate(
            resume_id=str(it.resume["id"]),
            headline=it.resume.get("headline"),
            experience_text=format_experience(it.resume.get("total_experience_months")),
            skills=list(it.resume.get("skills") or []),
            summary=it.resume.get("summary"),
            chunks=[c["content"] for c in it.chunks],
            vector_score=it.vector_score,
        )
        for it in items
    ]
    verdicts: dict[str, CandidateVerdict] | None
    try:
        verdicts = await verify_candidates(llm, query, parsed, candidates)
    except LLMUnavailable:
        logger.warning("Verify step degraded")
        verdicts = None
        response.llm_degraded = True

    # 8. Rank
    response.results = build_results(items, parsed, verdicts, top_k)
    return response

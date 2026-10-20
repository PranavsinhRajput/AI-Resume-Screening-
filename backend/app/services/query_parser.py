"""Prompt → ParsedQuery (architecture.md §8.1). LLM output is post-processed; never trusted as-is."""

from dataclasses import dataclass

from app.prompts.query_parse import QUERY_PARSE_SYSTEM, query_parse_user
from app.schemas.search import ParsedQuery, ParsedQueryGemini, QueryFilters
from app.services.llm import LLMGateway, LLMInvalidOutput, LLMUnavailable
from app.services.skills import normalize_skills

MAX_VERIFY_CRITERIA = 4


@dataclass
class ParseOutcome:
    parsed: ParsedQuery
    used_raw_query: bool
    parse_degraded: bool


def post_process(parsed: ParsedQuery, raw_query: str) -> tuple[ParsedQuery, bool]:
    """Clamp/swap experience, normalize skills, trim location, cap criteria, raw-query fallback."""
    f = parsed.filters
    mn = max(0, f.min_experience_months) if f.min_experience_months is not None else None
    mx = max(0, f.max_experience_months) if f.max_experience_months is not None else None
    if mn == 0:
        mn = None  # "at least 0 months" is not a filter
    if mn is not None and mx is not None and mn > mx:
        mn, mx = mx, mn
    location = f.location.strip() if f.location else None
    filters = QueryFilters(
        min_experience_months=mn,
        max_experience_months=mx,
        required_skills=normalize_skills(f.required_skills),
        location=location or None,
    )

    criteria = [c for c in parsed.verify_criteria if c.text and c.text.strip()][:MAX_VERIFY_CRITERIA]
    for c in criteria:
        c.text = c.text.strip()

    semantic = (parsed.semantic_query or "").strip()
    used_raw = False
    if not semantic:
        semantic = raw_query.strip()
        used_raw = True

    preferred = normalize_skills(parsed.preferred_skills)
    if preferred and not used_raw:
        missing = [s for s in preferred if s not in semantic.lower()]
        if missing:
            semantic = f"{semantic} Preferred skills: {', '.join(missing)}."

    summary = (parsed.interpretation_summary or "").strip() or raw_query.strip()

    return (
        ParsedQuery(
            filters=filters,
            preferred_skills=preferred,
            semantic_query=semantic,
            verify_criteria=criteria,
            unsupported=[u for u in parsed.unsupported if u.text and u.text.strip()],
            interpretation_summary=summary,
        ),
        used_raw,
    )


def degraded_parse(raw_query: str) -> ParsedQuery:
    return ParsedQuery(semantic_query=raw_query.strip(), interpretation_summary=raw_query.strip())


async def parse_query(llm: LLMGateway, raw_query: str) -> ParseOutcome:
    try:
        parsed = await llm.generate_json(
            QUERY_PARSE_SYSTEM,
            query_parse_user(raw_query),
            ParsedQuery,
            response_schema=ParsedQueryGemini,
        )
    except (LLMUnavailable, LLMInvalidOutput):
        return ParseOutcome(degraded_parse(raw_query), used_raw_query=False, parse_degraded=True)
    processed, used_raw = post_process(parsed, raw_query)
    return ParseOutcome(processed, used_raw_query=used_raw, parse_degraded=False)

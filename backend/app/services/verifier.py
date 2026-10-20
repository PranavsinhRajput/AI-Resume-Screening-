"""Candidates → VerifyResult via Gemini (architecture.md §8.2)."""

from dataclasses import dataclass, field
from html import escape

from app.prompts.verify import VERIFY_SYSTEM, verify_user
from app.schemas.search import CandidateVerdict, CriterionCheck, ParsedQuery, VerifyResult, VerifyResultGemini
from app.services.llm import LLMGateway, LLMInvalidOutput, LLMUnavailable

BATCH_THRESHOLD = 10
BATCH_SIZE = 8
MAX_SKILLS = 25
CHUNK_CHARS = 700


@dataclass
class Candidate:
    resume_id: str
    headline: str | None
    experience_text: str
    skills: list[str]
    summary: str | None
    chunks: list[str] = field(default_factory=list)
    vector_score: float = 0.0


def _two_sentences(text: str | None) -> str:
    if not text:
        return ""
    parts = [p.strip() for p in text.replace("\n", " ").split(". ") if p.strip()]
    out = ". ".join(parts[:2])
    return out if out.endswith(".") else out + "."


def candidate_xml(c: Candidate) -> str:
    chunks = "\n".join(
        f"<excerpt>{escape(t[:CHUNK_CHARS])}</excerpt>" for t in c.chunks[:3]
    )
    return (
        f'<candidate id="{escape(c.resume_id)}">\n'
        f"headline: {escape(c.headline or '')}\n"
        f"total experience: {escape(c.experience_text)}\n"
        f"skills: {escape(', '.join(c.skills[:MAX_SKILLS]))}\n"
        f"summary: {escape(_two_sentences(c.summary))}\n"
        f"{chunks}\n"
        f"</candidate>"
    )


async def verify_candidates(
    llm: LLMGateway, raw_query: str, parsed: ParsedQuery, candidates: list[Candidate]
) -> dict[str, CandidateVerdict]:
    """Return verdicts keyed by resume_id. Raises LLMUnavailable if any batch ultimately fails."""
    if not candidates:
        return {}
    batches = (
        [candidates[i : i + BATCH_SIZE] for i in range(0, len(candidates), BATCH_SIZE)]
        if len(candidates) > BATCH_THRESHOLD
        else [candidates]
    )
    criteria = [c.text for c in parsed.verify_criteria]
    valid_ids = {c.resume_id for c in candidates}
    verdicts: dict[str, CandidateVerdict] = {}

    for batch in batches:
        user = verify_user(
            raw_query, parsed.semantic_query, criteria, "\n\n".join(candidate_xml(c) for c in batch)
        )
        try:
            result = await llm.generate_json(
                VERIFY_SYSTEM, user, VerifyResult, response_schema=VerifyResultGemini
            )
        except LLMInvalidOutput as exc:
            raise LLMUnavailable("verify output invalid") from exc
        for v in result.candidates:
            if v.resume_id not in valid_ids or v.resume_id in verdicts:
                continue
            v.match_score = max(0, min(100, v.match_score))
            verdicts[v.resume_id] = _align_criteria(v, criteria)
    return verdicts


def _align_criteria(v: CandidateVerdict, criteria: list[str]) -> CandidateVerdict:
    """One entry per verify criterion, same order; missing entries become met=None."""
    aligned: list[CriterionCheck] = []
    for i, text in enumerate(criteria):
        if i < len(v.criteria):
            check = v.criteria[i]
            aligned.append(
                CriterionCheck(
                    criterion=text,
                    met=check.met,
                    evidence=check.evidence if check.met is True else None,
                )
            )
        else:
            aligned.append(CriterionCheck(criterion=text, met=None, evidence=None))
    v.criteria = aligned
    return v

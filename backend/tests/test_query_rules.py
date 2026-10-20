import pytest

from app.schemas.search import (
    CandidateVerdict,
    CriterionCheck,
    ParsedQuery,
    QueryFilters,
    UnsupportedItem,
    VerifyCriterion,
)
from app.services.llm import LLMUnavailable
from app.services.query_parser import parse_query, post_process
from app.services.search import RankInput, build_results, format_experience, relax_filters


class FakeLLM:
    def __init__(self, result=None, error: Exception | None = None):
        self.result = result
        self.error = error

    async def generate_json(self, system, user, schema, response_schema=None):
        if self.error:
            raise self.error
        return self.result


# ---------------- parse post-processing ----------------


def test_post_process_clamps_swaps_and_normalizes():
    parsed = ParsedQuery(
        filters=QueryFilters(
            min_experience_months=60, max_experience_months=24, required_skills=["Py", "ReactJS", "py"],
            location="  Pune ",
        ),
        semantic_query="AI engineer",
        verify_criteria=[VerifyCriterion(text=f"c{i}") for i in range(6)],
    )
    out, used_raw = post_process(parsed, "raw")
    assert out.filters.min_experience_months == 24
    assert out.filters.max_experience_months == 60
    assert out.filters.required_skills == ["python", "react"]
    assert out.filters.location == "Pune"
    assert len(out.verify_criteria) == 4
    assert used_raw is False


def test_negative_experience_becomes_none():
    f = QueryFilters.model_validate({"min_experience_months": -1, "max_experience_months": -1})
    assert f.min_experience_months is None and f.max_experience_months is None


def test_empty_semantic_query_uses_raw():
    out, used_raw = post_process(ParsedQuery(semantic_query=""), "show me the best resumes")
    assert used_raw is True
    assert out.semantic_query == "show me the best resumes"


def test_unsupported_kept_and_not_filtered():
    parsed = ParsedQuery(
        filters=QueryFilters(min_experience_months=36),
        semantic_query="software engineer",
        unsupported=[UnsupportedItem(text="only male candidates", reason="personal attribute")],
    )
    out, _ = post_process(parsed, "only male candidates with 3 years experience")
    assert out.filters.min_experience_months == 36
    assert out.unsupported[0].text == "only male candidates"


async def test_parse_degraded_on_llm_failure():
    outcome = await parse_query(FakeLLM(error=LLMUnavailable()), "python developers")
    assert outcome.parse_degraded is True
    assert outcome.parsed.semantic_query == "python developers"
    assert outcome.parsed.filters.required_skills == []


# ---------------- relaxation ----------------


def test_relaxation_order():
    filters = QueryFilters(
        min_experience_months=24, max_experience_months=60, required_skills=["python"], location="pune"
    )
    calls: list[QueryFilters] = []

    def retrieve(f):
        calls.append(f.model_copy())
        # Only succeeds once location and skills are both gone
        return [{"resume_id": "x", "score": 0.5}] if not f.location and not f.required_skills else []

    pool, relaxed, _ = relax_filters(filters, retrieve)
    assert pool
    assert relaxed == ["location", "required_skills"]
    assert len(calls) == 3


def test_relaxation_skips_unset_filters():
    filters = QueryFilters(min_experience_months=24)
    pool, relaxed, _ = relax_filters(filters, lambda f: [] if f.min_experience_months else [{"resume_id": "x"}])
    assert relaxed == ["min_experience_months"]
    assert pool


def test_no_relaxation_when_results():
    pool, relaxed, _ = relax_filters(QueryFilters(location="pune"), lambda f: [{"resume_id": "x"}])
    assert relaxed == []


# ---------------- ranking ----------------


def _item(rid: str, vscore: float) -> RankInput:
    return RankInput(
        resume={"id": rid, "original_filename": f"{rid}.pdf", "skills": [], "total_experience_months": 12},
        vector_score=vscore,
        chunks=[{"section": "raw", "content": f"snippet for {rid}", "score": vscore}],
    )


def _parsed_with_required() -> ParsedQuery:
    return ParsedQuery(semantic_query="x", verify_criteria=[VerifyCriterion(text="led a team", required=True)])


def test_ranking_meets_all_required_first():
    parsed = _parsed_with_required()
    items = [_item("a", 0.9), _item("b", 0.5), _item("c", 0.7)]
    verdicts = {
        "a": CandidateVerdict(resume_id="a", criteria=[CriterionCheck(met=False)], match_score=95, reason="r"),
        "b": CandidateVerdict(resume_id="b", criteria=[CriterionCheck(met=True, evidence="e")], match_score=60,
                              reason="r"),
        "c": CandidateVerdict(resume_id="c", criteria=[CriterionCheck(met=True, evidence="e")], match_score=80,
                              reason="r"),
    }
    results = build_results(items, parsed, verdicts, top_k=10)
    assert [r.resume_id for r in results] == ["c", "b", "a"]
    assert [r.rank for r in results] == [1, 2, 3]
    assert results[2].meets_all_required is False


def test_unknown_required_is_partial_not_dropped():
    parsed = _parsed_with_required()
    verdicts = {"a": CandidateVerdict(resume_id="a", criteria=[CriterionCheck(met=None)], match_score=70)}
    results = build_results([_item("a", 0.5)], parsed, verdicts, top_k=10)
    assert len(results) == 1 and results[0].meets_all_required is False


def test_partial_matches_capped_at_5():
    parsed = _parsed_with_required()
    items = [_item(str(i), 0.5) for i in range(8)]
    verdicts = {
        str(i): CandidateVerdict(resume_id=str(i), criteria=[CriterionCheck(met=False)], match_score=50)
        for i in range(8)
    }
    assert len(build_results(items, parsed, verdicts, top_k=10)) == 5


def test_degraded_mode_orders_by_vector_score():
    parsed = _parsed_with_required()
    results = build_results([_item("a", 0.4), _item("b", 0.8)], parsed, None, top_k=10)
    assert [r.resume_id for r in results] == ["b", "a"]
    assert results[0].match_score == 80
    assert results[0].reason.startswith("Matched on: ")
    assert all(r.meets_all_required for r in results)
    assert results[0].criteria[0].met is None


def test_missing_verdict_falls_back_to_vector_score():
    parsed = ParsedQuery(semantic_query="x")
    results = build_results([_item("a", 0.63)], parsed, {}, top_k=10)
    assert results[0].match_score == 63
    assert results[0].meets_all_required is True


@pytest.mark.parametrize(
    "months,expected", [(0, "Fresher (0 yrs)"), (28, "2 yrs 4 mos"), (12, "1 yr"), (5, "5 mos")]
)
def test_format_experience(months, expected):
    assert format_experience(months) == expected

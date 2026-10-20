from pydantic import BaseModel, Field, field_validator

# ---------------- LLM schemas ----------------


class QueryFilters(BaseModel):
    min_experience_months: int | None = None
    max_experience_months: int | None = None
    required_skills: list[str] = Field(default_factory=list)
    location: str | None = None

    @field_validator("location", mode="before")
    @classmethod
    def _blank(cls, v: object) -> object:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("min_experience_months", "max_experience_months", mode="before")
    @classmethod
    def _int(cls, v: object) -> object:
        # Gemini variant uses -1 / 0-less sentinels; treat negatives and blanks as "absent".
        if v in (None, ""):
            return None
        try:
            iv = int(float(str(v)))
        except (TypeError, ValueError):
            return None
        return None if iv < 0 else iv

    @field_validator("required_skills", mode="before")
    @classmethod
    def _list(cls, v: object) -> object:
        return v or []


class VerifyCriterion(BaseModel):
    text: str
    required: bool = True


class UnsupportedItem(BaseModel):
    text: str
    reason: str = ""


class ParsedQuery(BaseModel):
    filters: QueryFilters = Field(default_factory=QueryFilters)
    preferred_skills: list[str] = Field(default_factory=list)
    semantic_query: str = ""
    verify_criteria: list[VerifyCriterion] = Field(default_factory=list)
    unsupported: list[UnsupportedItem] = Field(default_factory=list)
    interpretation_summary: str = ""

    @field_validator("preferred_skills", "verify_criteria", "unsupported", mode="before")
    @classmethod
    def _lists(cls, v: object) -> object:
        return v or []

    @field_validator("semantic_query", "interpretation_summary", mode="before")
    @classmethod
    def _str(cls, v: object) -> object:
        return v or ""

    @field_validator("filters", mode="before")
    @classmethod
    def _filters(cls, v: object) -> object:
        return v or {}


class _GQueryFilters(BaseModel):
    """Gemini schema variant: -1 means 'no value', empty string means no location."""

    min_experience_months: int
    max_experience_months: int
    required_skills: list[str]
    location: str


class _GVerifyCriterion(BaseModel):
    text: str
    required: bool


class _GUnsupportedItem(BaseModel):
    text: str
    reason: str


class ParsedQueryGemini(BaseModel):
    filters: _GQueryFilters
    preferred_skills: list[str]
    semantic_query: str
    verify_criteria: list[_GVerifyCriterion]
    unsupported: list[_GUnsupportedItem]
    interpretation_summary: str


class CriterionCheck(BaseModel):
    criterion: str = ""
    met: bool | None = None
    evidence: str | None = None

    @field_validator("evidence", mode="before")
    @classmethod
    def _blank(cls, v: object) -> object:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("met", mode="before")
    @classmethod
    def _met(cls, v: object) -> object:
        if isinstance(v, str):
            low = v.strip().lower()
            if low in ("true", "yes", "met"):
                return True
            if low in ("false", "no", "not_met"):
                return False
            return None
        return v


class CandidateVerdict(BaseModel):
    resume_id: str
    criteria: list[CriterionCheck] = Field(default_factory=list)
    match_score: int = 0
    reason: str = ""

    @field_validator("match_score", mode="before")
    @classmethod
    def _score(cls, v: object) -> object:
        try:
            return int(round(float(str(v))))
        except (TypeError, ValueError):
            return 0

    @field_validator("criteria", mode="before")
    @classmethod
    def _lists(cls, v: object) -> object:
        return v or []


class VerifyResult(BaseModel):
    candidates: list[CandidateVerdict] = Field(default_factory=list)


class _GCriterionCheck(BaseModel):
    criterion: str
    met: str  # "true" | "false" | "unknown"
    evidence: str


class _GCandidateVerdict(BaseModel):
    resume_id: str
    criteria: list[_GCriterionCheck]
    match_score: int
    reason: str


class VerifyResultGemini(BaseModel):
    candidates: list[_GCandidateVerdict]


# ---------------- API schemas ----------------


class SearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    top_k: int | None = Field(default=None, ge=1)

    @field_validator("query")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Query must be at least 3 characters.")
        return v


class InterpretationFilters(BaseModel):
    min_experience_months: int | None = None
    max_experience_months: int | None = None
    required_skills: list[str] = Field(default_factory=list)
    location: str | None = None


class Interpretation(BaseModel):
    summary: str
    filters: InterpretationFilters
    preferred_skills: list[str] = Field(default_factory=list)
    semantic_query: str
    verify_criteria: list[VerifyCriterion] = Field(default_factory=list)
    unsupported: list[UnsupportedItem] = Field(default_factory=list)
    relaxed_filters: list[str] = Field(default_factory=list)
    used_raw_query: bool = False


class ResultCriterion(BaseModel):
    criterion: str
    required: bool
    met: bool | None = None
    evidence: str | None = None


class Snippet(BaseModel):
    section: str
    text: str


class SearchResult(BaseModel):
    rank: int
    resume_id: str
    candidate_name: str | None = None
    original_filename: str
    total_experience_months: int | None = None
    location: str | None = None
    skills: list[str] = Field(default_factory=list)
    match_score: int
    vector_score: float
    reason: str
    meets_all_required: bool
    criteria: list[ResultCriterion] = Field(default_factory=list)
    snippets: list[Snippet] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    interpretation: Interpretation
    llm_degraded: bool = False
    parse_degraded: bool = False
    candidates_considered: int = 0
    results: list[SearchResult] = Field(default_factory=list)

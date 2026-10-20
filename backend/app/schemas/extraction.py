"""LLM output schema for resume extraction.

Gemini's structured output does not like unions/nullable everywhere, so the schema sent to Gemini
uses plain strings/lists (empty = absent) and we validate leniently, converting "" to None afterwards.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

EmploymentType = Literal["full_time", "part_time", "internship", "contract", "freelance", "unknown"]


def _blank_to_none(v: object) -> object:
    if isinstance(v, str) and not v.strip():
        return None
    if isinstance(v, str) and v.strip().lower() in ("null", "none", "n/a"):
        return None
    return v


class Links(BaseModel):
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None

    _blank = field_validator("*", mode="before")(_blank_to_none)


class ExtractedExperience(BaseModel):
    company: str | None = None
    title: str | None = None
    employment_type: EmploymentType = "unknown"
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    location: str | None = None
    description: str = ""

    @field_validator("company", "title", "start_date", "end_date", "location", mode="before")
    @classmethod
    def _blank(cls, v: object) -> object:
        return _blank_to_none(v)

    @field_validator("employment_type", mode="before")
    @classmethod
    def _emp_type(cls, v: object) -> object:
        allowed = {"full_time", "part_time", "internship", "contract", "freelance", "unknown"}
        if isinstance(v, str):
            norm = v.strip().lower().replace("-", "_").replace(" ", "_")
            return norm if norm in allowed else "unknown"
        return "unknown"

    @field_validator("description", mode="before")
    @classmethod
    def _desc(cls, v: object) -> object:
        return v or ""


class ExtractedProject(BaseModel):
    name: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)

    @field_validator("name", "description", mode="before")
    @classmethod
    def _none_to_empty(cls, v: object) -> object:
        return v or ""


class ExtractedEducation(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    grade: str | None = None

    @field_validator("institution", "degree", "field_of_study", "grade", mode="before")
    @classmethod
    def _blank(cls, v: object) -> object:
        return _blank_to_none(v)

    @field_validator("start_year", "end_year", mode="before")
    @classmethod
    def _year(cls, v: object) -> object:
        if v in (None, "", 0):
            return None
        try:
            return int(str(v)[:4])
        except (TypeError, ValueError):
            return None


class ResumeExtraction(BaseModel):
    candidate_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    links: Links = Field(default_factory=Links)
    headline: str | None = None
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    experiences: list[ExtractedExperience] = Field(default_factory=list)
    projects: list[ExtractedProject] = Field(default_factory=list)
    education: list[ExtractedEducation] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)

    @field_validator("candidate_name", "email", "phone", "location", "headline", mode="before")
    @classmethod
    def _blank(cls, v: object) -> object:
        return _blank_to_none(v)

    @field_validator("summary", mode="before")
    @classmethod
    def _summary(cls, v: object) -> object:
        return v or ""

    @field_validator("links", mode="before")
    @classmethod
    def _links(cls, v: object) -> object:
        return v or {}

    @field_validator("skills", "certifications", "experiences", "projects", "education", mode="before")
    @classmethod
    def _lists(cls, v: object) -> object:
        return v or []


# ---- Gemini response_schema variant (no nullable unions; empty string/0 means absent) ----


class _GLinks(BaseModel):
    linkedin: str
    github: str
    portfolio: str


class _GExperience(BaseModel):
    company: str
    title: str
    employment_type: EmploymentType
    start_date: str
    end_date: str
    is_current: bool
    location: str
    description: str


class _GProject(BaseModel):
    name: str
    description: str
    technologies: list[str]


class _GEducation(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    start_year: int
    end_year: int
    grade: str


class ResumeExtractionGemini(BaseModel):
    candidate_name: str
    email: str
    phone: str
    location: str
    links: _GLinks
    headline: str
    summary: str
    skills: list[str]
    experiences: list[_GExperience]
    projects: list[_GProject]
    education: list[_GEducation]
    certifications: list[str]

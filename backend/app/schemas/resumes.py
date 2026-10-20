from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ResumeStatus = Literal["pending", "processing", "done", "failed"]
RejectReason = Literal[
    "not_a_pdf",
    "file_too_large",
    "corrupted_pdf",
    "password_protected",
    "too_many_pages",
    "duplicate",
    "too_many_files",
    "library_full",
]


class AcceptedFile(BaseModel):
    resume_id: str
    filename: str


class RejectedFile(BaseModel):
    filename: str
    reason: RejectReason
    message: str
    existing_resume_id: str | None = None


class UploadResult(BaseModel):
    accepted: list[AcceptedFile] = Field(default_factory=list)
    rejected: list[RejectedFile] = Field(default_factory=list)


class ResumeStats(BaseModel):
    total: int
    done: int
    pending: int
    processing: int
    failed: int
    limit: int


class ResumeSummary(BaseModel):
    id: str
    original_filename: str
    status: ResumeStatus
    error_message: str | None = None
    candidate_name: str | None = None
    total_experience_months: int | None = None
    skills: list[str] = Field(default_factory=list)
    location: str | None = None
    created_at: datetime


class ExperienceOut(BaseModel):
    company: str | None = None
    title: str | None = None
    employment_type: str = "unknown"
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    location: str | None = None
    description: str | None = None


class ResumeDetail(ResumeSummary):
    email: str | None = None
    phone: str | None = None
    links: dict[str, Any] = Field(default_factory=dict)
    headline: str | None = None
    summary: str | None = None
    education: list[dict[str, Any]] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    experiences: list[ExperienceOut] = Field(default_factory=list)
    parse_warnings: list[str] = Field(default_factory=list)


class DownloadUrl(BaseModel):
    url: str
    expires_in: int

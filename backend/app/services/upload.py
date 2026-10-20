"""Pure upload validation rules (project.md FR-UP-3, architecture.md §6.3).

Kept free of network calls so it can be unit-tested; the router supplies a `find_existing` lookup.
"""

import hashlib
import os
from collections.abc import Callable
from dataclasses import dataclass, field

from app.services.pdf_extract import inspect_pdf, looks_like_pdf


def reason_messages(max_file_mb: float, max_pages: int, max_files: int, max_resumes: int) -> dict[str, str]:
    mb = f"{max_file_mb:g}"
    return {
        "not_a_pdf": "Not a valid PDF.",
        "file_too_large": f"Larger than {mb} MB.",
        "corrupted_pdf": "File is corrupted.",
        "password_protected": "Password-protected PDFs aren't supported.",
        "too_many_pages": f"More than {max_pages} pages.",
        "duplicate": "Already in your library.",
        "too_many_files": f"Too many files in one upload (max {max_files}).",
        "library_full": (
            f"Library is full ({max_resumes} resumes). Delete some resumes to add more."
        ),
    }


def sanitize_filename(name: str | None) -> str:
    base = os.path.basename((name or "").replace("\\", "/")).strip()
    base = "".join(ch for ch in base if ch.isprintable())
    return (base or "resume.pdf")[:200]


@dataclass
class IncomingFile:
    filename: str
    data: bytes
    oversize: bool = False  # set when the reader stopped early because the file exceeded the limit


@dataclass
class ValidFile:
    filename: str
    data: bytes
    file_hash: str
    page_count: int


@dataclass
class Rejection:
    filename: str
    reason: str
    existing_resume_id: str | None = None


@dataclass
class ValidationOutcome:
    valid: list[ValidFile] = field(default_factory=list)
    rejected: list[Rejection] = field(default_factory=list)
    # Preserve the original order so rejections can be reported per file.
    order: list[tuple[str, int]] = field(default_factory=list)


def validate_files(
    files: list[IncomingFile],
    *,
    max_files: int,
    max_file_bytes: int,
    max_pages: int,
    free_slots: int,
    find_existing: Callable[[str], str | None],
) -> ValidationOutcome:
    """Apply every per-file rule in order. `library_full` is checked last so invalid files keep their reason."""
    out = ValidationOutcome()
    seen_hashes: set[str] = set()

    for idx, f in enumerate(files):
        name = sanitize_filename(f.filename)
        if idx >= max_files:
            out.rejected.append(Rejection(name, "too_many_files"))
            continue
        if f.oversize or len(f.data) > max_file_bytes:
            out.rejected.append(Rejection(name, "file_too_large"))
            continue
        if not looks_like_pdf(name, f.data):
            out.rejected.append(Rejection(name, "not_a_pdf"))
            continue
        inspection = inspect_pdf(f.data, max_pages)
        if inspection.problem is not None:
            out.rejected.append(Rejection(name, inspection.problem))
            continue
        file_hash = hashlib.sha256(f.data).hexdigest()
        if file_hash in seen_hashes:
            out.rejected.append(Rejection(name, "duplicate", None))
            continue
        existing = find_existing(file_hash)
        if existing:
            out.rejected.append(Rejection(name, "duplicate", existing))
            continue
        if len(out.valid) >= free_slots:
            out.rejected.append(Rejection(name, "library_full"))
            continue
        seen_hashes.add(file_hash)
        out.valid.append(ValidFile(name, f.data, file_hash, inspection.page_count or 0))

    return out

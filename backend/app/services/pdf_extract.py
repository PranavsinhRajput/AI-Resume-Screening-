"""PyMuPDF validation and text extraction. All functions are blocking — run them in a thread."""

import re
from dataclasses import dataclass
from typing import Literal

import pymupdf

PdfProblem = Literal["corrupted_pdf", "password_protected", "too_many_pages"]


@dataclass(frozen=True)
class PdfInspection:
    problem: PdfProblem | None
    page_count: int | None


def looks_like_pdf(filename: str, data: bytes) -> bool:
    return filename.lower().endswith(".pdf") and data[:4] == b"%PDF"


def inspect_pdf(data: bytes, max_pages: int) -> PdfInspection:
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        return PdfInspection("corrupted_pdf", None)
    try:
        if doc.needs_pass:
            return PdfInspection("password_protected", None)
        page_count = doc.page_count
        if page_count <= 0:
            return PdfInspection("corrupted_pdf", None)
        if page_count > max_pages:
            return PdfInspection("too_many_pages", page_count)
        return PdfInspection(None, page_count)
    except Exception:
        return PdfInspection("corrupted_pdf", None)
    finally:
        doc.close()


_MULTI_NEWLINES = re.compile(r"\n{3,}")
_TRAILING_SPACES = re.compile(r"[ \t]+\n")
_INLINE_SPACES = re.compile(r"[ \t]{2,}")


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = _TRAILING_SPACES.sub("\n", text)
    text = _INLINE_SPACES.sub(" ", text)
    text = _MULTI_NEWLINES.sub("\n\n", text)
    return text.strip()


def extract_text(data: bytes, max_chars: int) -> tuple[str, int]:
    """Return (normalized text truncated to max_chars, page_count). Reading order is preserved via sort=True."""
    doc = pymupdf.open(stream=data, filetype="pdf")
    try:
        pages = [page.get_text("text", sort=True) for page in doc]
        page_count = doc.page_count
    finally:
        doc.close()
    text = normalize_text("\n\n".join(pages))
    return text[:max_chars], page_count

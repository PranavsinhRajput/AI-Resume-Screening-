"""Build search chunks for a resume (architecture.md §7.6).

Structured chunks never include name, email, phone, or links. Raw-text windows have emails, phone
numbers and URLs stripped before windowing.
"""

import re
from typing import Any

from app.schemas.extraction import ResumeExtraction

WINDOW_WORDS = 250
OVERLAP_WORDS = 40
MAX_CHUNK_WORDS = 350
MIN_CHUNK_WORDS = 5
MAX_CHUNKS = 40

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL_RE = re.compile(r"(?:https?://|www\.)\S+|\b[\w.-]+\.(?:com|in|io|org|net|dev|me|ai|co)(?:/\S*)?", re.I)
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")


def scrub_pii(text: str) -> str:
    text = EMAIL_RE.sub(" ", text)
    text = URL_RE.sub(" ", text)
    text = PHONE_RE.sub(" ", text)
    return re.sub(r"[ \t]{2,}", " ", text)


def window_words(text: str, size: int = WINDOW_WORDS, overlap: int = OVERLAP_WORDS) -> list[str]:
    words = text.split()
    if not words:
        return []
    if len(words) <= size:
        return [" ".join(words)]
    step = max(1, size - overlap)
    windows: list[str] = []
    for start in range(0, len(words), step):
        piece = words[start : start + size]
        windows.append(" ".join(piece))
        if start + size >= len(words):
            break
    return windows


def _join(parts: list[str], sep: str = " ") -> str:
    return sep.join(p.strip() for p in parts if p and p.strip())


def _structured_chunks(ex: ResumeExtraction, skills: list[str]) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []

    summary_parts: list[str] = []
    if ex.headline:
        summary_parts.append(f"Profile: {ex.headline.strip().rstrip('.')}.")
    if ex.summary:
        summary_parts.append(ex.summary.strip())
    if skills:
        summary_parts.append(f"Skills: {', '.join(skills)}.")
    if summary_parts:
        chunks.append({"section": "summary", "content": _join(summary_parts)})

    for exp in ex.experiences:
        head_bits = []
        if exp.title and exp.company:
            head_bits.append(f"{exp.title} at {exp.company}")
        else:
            head_bits.append(exp.title or exp.company or "Role")
        period = f"{exp.start_date or 'unknown'} to {exp.end_date or ('Present' if exp.is_current else 'unknown')}"
        content = f"Experience: {head_bits[0]} ({period}, {exp.employment_type}). {exp.description or ''}"
        chunks.append({"section": "experience", "content": content.strip()})

    for proj in ex.projects:
        parts = [f"Project: {proj.name.strip().rstrip('.') or 'Untitled'}.", proj.description]
        if proj.technologies:
            parts.append(f"Technologies: {', '.join(t for t in proj.technologies if t)}.")
        chunks.append({"section": "project", "content": _join(parts)})

    edu_items: list[str] = []
    for ed in ex.education:
        desc = ed.degree or ""
        if ed.field_of_study:
            desc = f"{desc} in {ed.field_of_study}" if desc else ed.field_of_study
        if ed.institution:
            desc = f"{desc} at {ed.institution}" if desc else ed.institution
        years = "-".join(str(y) for y in (ed.start_year, ed.end_year) if y)
        if years:
            desc = f"{desc} ({years})"
        if ed.grade:
            desc = f"{desc}, grade {ed.grade}"
        if desc.strip():
            edu_items.append(desc.strip())
    if edu_items:
        chunks.append({"section": "education", "content": "Education: " + "; ".join(edu_items) + "."})

    certs = [c.strip() for c in ex.certifications if c and c.strip()]
    if certs:
        chunks.append({"section": "certification", "content": "Certifications: " + "; ".join(certs) + "."})

    return chunks


def build_chunks(ex: ResumeExtraction, skills: list[str], raw_text: str) -> list[dict[str, Any]]:
    """Return chunk dicts {chunk_index, section, content}."""
    structured: list[dict[str, str]] = []
    for chunk in _structured_chunks(ex, skills):
        if len(chunk["content"].split()) > MAX_CHUNK_WORDS:
            structured.extend({"section": chunk["section"], "content": w} for w in window_words(chunk["content"]))
        else:
            structured.append(chunk)

    raw = [{"section": "raw", "content": w} for w in window_words(scrub_pii(raw_text or ""))]

    structured = [c for c in structured if len(c["content"].split()) >= MIN_CHUNK_WORDS]
    raw = [c for c in raw if len(c["content"].split()) >= MIN_CHUNK_WORDS]

    # Cap: drop extra raw windows first, then structured overflow.
    structured = structured[:MAX_CHUNKS]
    raw = raw[: max(0, MAX_CHUNKS - len(structured))]

    return [
        {"chunk_index": i, "section": c["section"], "content": c["content"]}
        for i, c in enumerate(structured + raw)
    ]

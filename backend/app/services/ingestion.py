"""process_resume orchestrator (project.md §6.4, architecture.md §7.2).

Idempotent: existing experiences and chunks are deleted before new ones are written. Any failure
ends in status='failed' with a user-readable message — a resume is never left in 'processing'.
"""

import logging
from datetime import UTC, datetime
from typing import Any

import anyio
from supabase import Client

from app.config import Settings
from app.repositories import chunks as chunks_repo
from app.repositories import resumes as resumes_repo
from app.repositories import storage as storage_repo
from app.services.chunking import build_chunks
from app.services.embeddings import Embedder
from app.services.experience import compute_experience
from app.services.extraction import extract_resume
from app.services.llm import LLMGateway, LLMInvalidOutput, LLMUnavailable
from app.services.pdf_extract import extract_text
from app.services.skills import normalize_skills

logger = logging.getLogger(__name__)

MSG_NO_TEXT = "No readable text found. Scanned/image-only PDFs are not supported yet."
MSG_AI_BUSY = "AI service busy. Please retry."
MSG_BAD_LAYOUT = "Could not understand this resume's layout."
MSG_GENERIC = "Processing failed. Please retry."
MSG_FILE_MISSING = "The PDF file could not be loaded. Please delete and upload it again."


class ProcessingFailed(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.user_message = message


async def process_resume(
    resume: dict[str, Any],
    *,
    client: Client,
    settings: Settings,
    llm: LLMGateway,
    embedder: Embedder,
) -> None:
    resume_id: str = str(resume["id"])
    owner_id: str = str(resume["owner_id"])
    logger.info("Processing resume %s", resume_id)
    try:
        await _process(resume, resume_id, owner_id, client=client, settings=settings, llm=llm, embedder=embedder)
        logger.info("Resume %s done", resume_id)
    except ProcessingFailed as exc:
        logger.info("Resume %s failed: %s", resume_id, exc.user_message)
        await _mark_failed(client, owner_id, resume_id, exc.user_message)
    except Exception as exc:
        logger.error("Resume %s failed unexpectedly: %s", resume_id, type(exc).__name__)
        await _mark_failed(client, owner_id, resume_id, MSG_GENERIC)


async def _mark_failed(client: Client, owner_id: str, resume_id: str, message: str) -> None:
    try:
        await anyio.to_thread.run_sync(resumes_repo.mark_failed, client, owner_id, resume_id, message)
    except Exception as exc:
        logger.error("Could not mark resume %s failed: %s", resume_id, type(exc).__name__)


async def _process(
    resume: dict[str, Any],
    resume_id: str,
    owner_id: str,
    *,
    client: Client,
    settings: Settings,
    llm: LLMGateway,
    embedder: Embedder,
) -> None:
    # 1. Load PDF bytes
    try:
        data = await anyio.to_thread.run_sync(
            storage_repo.download_pdf, client, settings.STORAGE_BUCKET, owner_id, resume["file_path"]
        )
    except Exception as exc:
        raise ProcessingFailed(MSG_FILE_MISSING) from exc

    # 2. Extract text
    try:
        text, page_count = await anyio.to_thread.run_sync(extract_text, data, settings.MAX_TEXT_CHARS)
    except Exception as exc:
        raise ProcessingFailed(MSG_BAD_LAYOUT) from exc
    del data

    # 3. Readable text?
    if len(text.strip()) < settings.MIN_TEXT_CHARS:
        await anyio.to_thread.run_sync(
            resumes_repo.update_resume,
            client,
            owner_id,
            resume_id,
            {"page_count": page_count, "status": "failed", "error_message": MSG_NO_TEXT},
        )
        logger.info("Resume %s failed: no readable text", resume_id)
        return

    # 4. LLM extraction
    try:
        extraction = await extract_resume(llm, text)
    except LLMUnavailable as exc:
        raise ProcessingFailed(MSG_AI_BUSY) from exc
    except LLMInvalidOutput as exc:
        raise ProcessingFailed(MSG_BAD_LAYOUT) from exc

    # 5. Idempotency
    await anyio.to_thread.run_sync(resumes_repo.delete_experiences, client, owner_id, resume_id)
    await anyio.to_thread.run_sync(chunks_repo.delete_chunks, client, owner_id, resume_id)

    # 6. Experience (computed in code, never by the LLM)
    total_months, warnings = compute_experience(extraction.experiences, datetime.now(UTC).date())

    # 7. Skills
    skills = normalize_skills(extraction.skills)

    # 8. Save structured data
    fields: dict[str, Any] = {
        "page_count": page_count,
        "candidate_name": extraction.candidate_name,
        "email": extraction.email,
        "phone": extraction.phone,
        "location": extraction.location,
        "links": extraction.links.model_dump(),
        "headline": extraction.headline,
        "summary": extraction.summary or None,
        "skills": skills,
        "education": [e.model_dump() for e in extraction.education],
        "certifications": [c for c in extraction.certifications if c],
        "projects": [p.model_dump() for p in extraction.projects],
        "total_experience_months": total_months,
        "parse_warnings": warnings,
        "raw_text": text,
    }
    await anyio.to_thread.run_sync(resumes_repo.update_resume, client, owner_id, resume_id, fields)
    experience_rows = [
        {
            "company": e.company,
            "title": e.title,
            "employment_type": e.employment_type,
            "start_date": e.start_date,
            "end_date": e.end_date,
            "is_current": e.is_current,
            "location": e.location,
            "description": e.description,
        }
        for e in extraction.experiences
    ]
    await anyio.to_thread.run_sync(
        resumes_repo.insert_experiences, client, owner_id, resume_id, experience_rows
    )

    # 9. Chunks + embeddings
    chunks = build_chunks(extraction, skills, text)
    if chunks:
        vectors = await anyio.to_thread.run_sync(
            embedder.embed_passages, [c["content"] for c in chunks]
        )
        await anyio.to_thread.run_sync(
            chunks_repo.insert_chunks, client, owner_id, resume_id, chunks, vectors
        )

    # 10. Done
    await anyio.to_thread.run_sync(
        resumes_repo.update_resume, client, owner_id, resume_id, {"status": "done", "error_message": None}
    )

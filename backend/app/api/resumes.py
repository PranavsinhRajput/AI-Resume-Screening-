import logging
import uuid
from typing import Literal

import anyio
from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from supabase import Client

from app.config import Settings, get_settings
from app.deps import get_access, get_supabase, get_writable_access
from app.errors import AppError
from app.repositories import resumes as resumes_repo
from app.repositories import storage as storage_repo
from app.schemas.common import Page
from app.schemas.resumes import (
    AcceptedFile,
    DownloadUrl,
    ExperienceOut,
    RejectedFile,
    ResumeDetail,
    ResumeStats,
    ResumeSummary,
    UploadResult,
)
from app.services.access import AccessContext
from app.services.upload import IncomingFile, reason_messages, validate_files

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["resumes"])

READ_CHUNK = 64 * 1024


def _messages(settings: Settings) -> dict[str, str]:
    return reason_messages(
        settings.MAX_FILE_MB, settings.MAX_PAGES, settings.MAX_FILES_PER_UPLOAD, settings.MAX_RESUMES_PER_USER
    )


async def _read_limited(upload: UploadFile, limit: int) -> IncomingFile:
    """Read at most limit+1 bytes so oversize files are detected without buffering them fully."""
    buf = bytearray()
    while True:
        chunk = await upload.read(READ_CHUNK)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > limit:
            return IncomingFile(upload.filename or "", b"", oversize=True)
    return IncomingFile(upload.filename or "", bytes(buf))


def _is_unique_violation(exc: Exception) -> bool:
    text = str(exc).lower()
    return "23505" in text or "duplicate key" in text or "unique" in text


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=UploadResult)
async def upload_resumes(
    files: list[UploadFile] = File(...),
    access: AccessContext = Depends(get_writable_access),
    client: Client = Depends(get_supabase),
    settings: Settings = Depends(get_settings),
) -> UploadResult:
    owner_id = access.owner_id
    messages = _messages(settings)

    existing = await anyio.to_thread.run_sync(resumes_repo.count_all, client, owner_id)
    free_slots = max(0, settings.MAX_RESUMES_PER_USER - existing)

    incoming: list[IncomingFile] = []
    for idx, upload in enumerate(files):
        if idx >= settings.MAX_FILES_PER_UPLOAD:
            incoming.append(IncomingFile(upload.filename or "", b""))
        else:
            incoming.append(await _read_limited(upload, settings.max_file_bytes))
        await upload.close()

    def _find_existing(file_hash: str) -> str | None:
        row = resumes_repo.find_by_hash(client, owner_id, file_hash)
        return str(row["id"]) if row else None

    outcome = await anyio.to_thread.run_sync(
        lambda: validate_files(
            incoming,
            max_files=settings.MAX_FILES_PER_UPLOAD,
            max_file_bytes=settings.max_file_bytes,
            max_pages=settings.MAX_PAGES,
            free_slots=free_slots,
            find_existing=_find_existing,
        )
    )

    result = UploadResult()
    for rej in outcome.rejected:
        result.rejected.append(
            RejectedFile(
                filename=rej.filename,
                reason=rej.reason,  # type: ignore[arg-type]
                message=messages[rej.reason],
                existing_resume_id=rej.existing_resume_id,
            )
        )

    for valid in outcome.valid:
        resume_id = str(uuid.uuid4())
        try:
            path = await anyio.to_thread.run_sync(
                storage_repo.upload_pdf, client, settings.STORAGE_BUCKET, owner_id, resume_id, valid.data
            )
        except Exception as exc:
            logger.error("Storage upload failed: %s", type(exc).__name__)
            raise AppError(500, "internal_error") from exc
        try:
            await anyio.to_thread.run_sync(
                resumes_repo.insert_resume,
                client,
                owner_id,
                {
                    "id": resume_id,
                    "original_filename": valid.filename,
                    "file_path": path,
                    "file_size_bytes": len(valid.data),
                    "file_hash": valid.file_hash,
                    "page_count": valid.page_count,
                },
            )
        except Exception as exc:
            await anyio.to_thread.run_sync(
                storage_repo.delete_object, client, settings.STORAGE_BUCKET, owner_id, path
            )
            if _is_unique_violation(exc):
                existing_row = await anyio.to_thread.run_sync(
                    resumes_repo.find_by_hash, client, owner_id, valid.file_hash
                )
                result.rejected.append(
                    RejectedFile(
                        filename=valid.filename,
                        reason="duplicate",
                        message=messages["duplicate"],
                        existing_resume_id=str(existing_row["id"]) if existing_row else None,
                    )
                )
                continue
            logger.error("Resume insert failed: %s", type(exc).__name__)
            raise AppError(500, "internal_error") from exc
        result.accepted.append(AcceptedFile(resume_id=resume_id, filename=valid.filename))
        logger.info("Resume %s accepted (pending)", resume_id)

    return result


@router.get("/stats", response_model=ResumeStats)
async def resume_stats(
    access: AccessContext = Depends(get_access),
    client: Client = Depends(get_supabase),
    settings: Settings = Depends(get_settings),
) -> ResumeStats:
    counts = await anyio.to_thread.run_sync(resumes_repo.status_counts, client, access.owner_id)
    return ResumeStats(total=sum(counts.values()), limit=settings.MAX_RESUMES_PER_USER, **counts)


@router.get("", response_model=Page[ResumeSummary])
async def list_resumes(
    status_filter: Literal["pending", "processing", "done", "failed"] | None = Query(
        default=None, alias="status"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    access: AccessContext = Depends(get_access),
    client: Client = Depends(get_supabase),
) -> Page[ResumeSummary]:
    rows, total = await anyio.to_thread.run_sync(
        resumes_repo.list_resumes, client, access.owner_id, status_filter, page, page_size
    )
    return Page[ResumeSummary](
        items=[ResumeSummary.model_validate(r) for r in rows], total=total, page=page, page_size=page_size
    )


def _valid_uuid(resume_id: str) -> str:
    try:
        return str(uuid.UUID(resume_id))
    except ValueError as exc:
        raise AppError(404, "not_found") from exc


async def _load_owned(client: Client, owner_id: str, resume_id: str, columns: str) -> dict:
    row = await anyio.to_thread.run_sync(
        resumes_repo.get_resume, client, owner_id, _valid_uuid(resume_id), columns
    )
    if not row:
        raise AppError(404, "not_found")
    return row


@router.get("/{resume_id}", response_model=ResumeDetail)
async def get_resume(
    resume_id: str,
    access: AccessContext = Depends(get_access),
    client: Client = Depends(get_supabase),
) -> ResumeDetail:
    row = await _load_owned(client, access.owner_id, resume_id, resumes_repo.DETAIL_COLUMNS)
    experiences = await anyio.to_thread.run_sync(
        resumes_repo.list_experiences, client, access.owner_id, row["id"]
    )
    return ResumeDetail.model_validate(
        {**row, "experiences": [ExperienceOut.model_validate(e) for e in experiences]}
    )


@router.get("/{resume_id}/download-url", response_model=DownloadUrl)
async def download_url(
    resume_id: str,
    access: AccessContext = Depends(get_access),
    client: Client = Depends(get_supabase),
    settings: Settings = Depends(get_settings),
) -> DownloadUrl:
    row = await _load_owned(client, access.owner_id, resume_id, "id,file_path")
    url = await anyio.to_thread.run_sync(
        storage_repo.signed_url,
        client,
        settings.STORAGE_BUCKET,
        access.owner_id,
        row["file_path"],
        settings.SIGNED_URL_TTL_SECONDS,
    )
    return DownloadUrl(url=url, expires_in=settings.SIGNED_URL_TTL_SECONDS)


@router.post("/{resume_id}/retry", status_code=status.HTTP_202_ACCEPTED, response_model=ResumeSummary)
async def retry_resume(
    resume_id: str,
    access: AccessContext = Depends(get_writable_access),
    client: Client = Depends(get_supabase),
) -> ResumeSummary:
    row = await _load_owned(client, access.owner_id, resume_id, "id,status")
    if row["status"] != "failed":
        raise AppError(422, "validation_error", "Only failed resumes can be retried.")
    await anyio.to_thread.run_sync(resumes_repo.retry_failed, client, access.owner_id, row["id"])
    updated = await _load_owned(client, access.owner_id, row["id"], resumes_repo.SUMMARY_COLUMNS)
    logger.info("Resume %s requeued by user", row["id"])
    return ResumeSummary.model_validate(updated)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: str,
    access: AccessContext = Depends(get_writable_access),
    client: Client = Depends(get_supabase),
    settings: Settings = Depends(get_settings),
) -> Response:
    row = await _load_owned(client, access.owner_id, resume_id, "id,file_path")
    try:
        await anyio.to_thread.run_sync(
            storage_repo.delete_object, client, settings.STORAGE_BUCKET, access.owner_id, row["file_path"]
        )
    except Exception as exc:
        logger.warning("Storage delete failed for %s: %s", row["id"], type(exc).__name__)
    await anyio.to_thread.run_sync(resumes_repo.delete_resume, client, access.owner_id, row["id"])
    logger.info("Resume %s deleted", row["id"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)

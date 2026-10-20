"""Single background worker loop running inside the FastAPI process (architecture.md §7.1)."""

import asyncio
import logging

import anyio
from supabase import Client

from app.config import Settings
from app.repositories import resumes as resumes_repo
from app.services.embeddings import get_default_embedder
from app.services.ingestion import process_resume
from app.services.llm import get_default_llm

logger = logging.getLogger(__name__)


async def requeue_stale(client: Client, settings: Settings) -> None:
    try:
        count = await anyio.to_thread.run_sync(
            resumes_repo.requeue_stale, client, settings.STALE_PROCESSING_MINUTES
        )
        if count:
            logger.info("Requeued %d stale processing resumes", count)
    except Exception as exc:
        logger.error("Requeue of stale resumes failed: %s", type(exc).__name__)


async def run_worker(client: Client, settings: Settings, stop: asyncio.Event) -> None:
    await requeue_stale(client, settings)
    logger.info("Worker started")
    while not stop.is_set():
        try:
            row = await anyio.to_thread.run_sync(resumes_repo.claim_next, client)
            if row:
                embedder = await anyio.to_thread.run_sync(get_default_embedder)
                await process_resume(
                    row, client=client, settings=settings, llm=get_default_llm(), embedder=embedder
                )
                continue
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Worker iteration failed: %s", type(exc).__name__)
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.WORKER_POLL_SECONDS)
        except TimeoutError:
            pass
    logger.info("Worker stopped")

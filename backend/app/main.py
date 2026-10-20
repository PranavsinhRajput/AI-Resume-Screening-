import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client

from app.api import admin, health, me, resumes, search
from app.config import get_settings
from app.errors import register_error_handlers
from app.logging_config import configure_logging
from app.services.worker import run_worker

settings = get_settings()
configure_logging(settings.is_production)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    stop = asyncio.Event()
    tasks: list[asyncio.Task] = []
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        worker_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        tasks.append(asyncio.create_task(run_worker(worker_client, settings, stop)))
    else:
        logger.warning("Supabase is not configured; worker not started")
    try:
        yield
    finally:
        stop.set()
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task


app = FastAPI(
    title="Resume Screening AI",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-View-As"],
)

register_error_handlers(app)

app.include_router(health.router)
app.include_router(me.router)
app.include_router(resumes.router)
app.include_router(search.router)
app.include_router(admin.router)

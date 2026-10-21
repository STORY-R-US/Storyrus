"""Entrypoint da API."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import queue
from app.config import settings
from app.errors import register_exception_handlers
from app.middleware.request_id import RequestIdMiddleware
from app.observability import opik_trace
from app.observability.logging_setup import configure_logging
from app.routers import (
    auth,
    credits,
    jobs,
    local_storage,
    print_orders,
    projects,
    usage,
    users,
    voices,
    webhooks,
)
from app.services import jobs as jobs_svc
from app.services.transactional_email import email_configured, warn_if_email_unconfigured

configure_logging(
    level=settings.log_level,
    fmt=settings.resolved_log_format(),
    service="api",
)
opik_trace.configure()
warn_if_email_unconfigured()

# Ao enfileirar um job, notifica o worker via Redis (best-effort; degrada p/ polling).
jobs_svc.enqueue_fn = queue.notify


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task: asyncio.Task[None] | None = None
    if settings.job_pump_enabled():
        from app.workers.api_pump import bind, pump_forever

        task = asyncio.create_task(pump_forever())
        bind(asyncio.get_running_loop(), task)
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="Story R Us — API",
    version="0.1.0",
    description="Foto -> personagem -> ebook -> video. Pipeline assincrono.",
    lifespan=lifespan,
)

register_exception_handlers(app)

# Request ID primeiro (mais externo apos CORS? Starlette: ultimo add = mais externo).
# Queremos request_id em toda request, inclusive CORS preflight — adicionamos por ultimo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "dev" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestIdMiddleware)

app.include_router(auth.router)
app.include_router(credits.router)
app.include_router(projects.router)
app.include_router(jobs.router)
app.include_router(voices.router)
app.include_router(webhooks.router)
app.include_router(usage.router)
app.include_router(users.router)
app.include_router(print_orders.router)
app.include_router(local_storage.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    # STO-28: nao vazar quais provedores de IA estao configurados (ex. ElevenLabs).
    # email_configured é só booleano (chave Resend presente) — útil p/ ops de esqueci-senha.
    return {
        "status": "ok",
        "env": settings.app_env,
        "email_configured": email_configured(),
    }

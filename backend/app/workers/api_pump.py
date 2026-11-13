"""A API também consome a fila.

No Render free o worker dorme e não acorda quando um job entra no Postgres.
O navegador mantém a API acordada (polling da prévia). Cada livro enfileirado
acorda este loop na hora — ele não espera o intervalo se há trabalho.
`SKIP LOCKED` impede dois processos de pegarem o mesmo job.
"""

from __future__ import annotations

import asyncio
import logging
import threading

from app.config import settings
from app.database import SessionLocal
from app.services import process_lifecycle
from app.workers import runner

logger = logging.getLogger("api.job_pump")

_wake = threading.Event()
_loop: asyncio.AbstractEventLoop | None = None
_task: asyncio.Task[None] | None = None


def bind(loop: asyncio.AbstractEventLoop, task: asyncio.Task[None]) -> None:
    global _loop, _task
    process_lifecycle.reset()
    _loop = loop
    _task = task


def kick() -> None:
    """Acorda o pump agora. Se a tarefa morreu, sobe outra no loop da API."""
    if process_lifecycle.draining():
        return
    _wake.set()
    loop = _loop
    if loop is None or not settings.job_pump_enabled():
        return

    def _ensure() -> None:
        global _task
        if process_lifecycle.draining():
            return
        if _task is not None and not _task.done():
            return
        _task = asyncio.create_task(pump_forever())
        logger.warning("api job pump restarted")

    try:
        loop.call_soon_threadsafe(_ensure)
    except RuntimeError:
        logger.exception("api job pump kick failed")


async def pump_forever() -> None:
    logger.info("api job pump on (poll=%ss)", settings.worker_poll_interval_s)
    while not process_lifecycle.draining():
        db = SessionLocal()
        processed = 0
        try:
            processed = await runner.run_once(db)
        except Exception:
            logger.exception("api job pump tick failed")
            processed = 0
        finally:
            db.close()
        if processed == 0:
            await asyncio.to_thread(_wake.wait, settings.worker_poll_interval_s)
            _wake.clear()


async def shutdown(task: asyncio.Task | None = None, *, timeout: float = 270) -> None:
    """Let the current paid response be saved; do not start another request."""
    process_lifecycle.begin_shutdown()
    _wake.set()
    current = _task if _task is not None and not _task.done() else task
    if current is None:
        return
    try:
        await asyncio.wait_for(asyncio.shield(current), timeout=timeout)
    except TimeoutError:
        logger.error("job pump exceeded shutdown grace; paid journal preserves uncertainty")
        current.cancel()
        try:
            await current
        except asyncio.CancelledError:
            pass
    except asyncio.CancelledError:
        pass

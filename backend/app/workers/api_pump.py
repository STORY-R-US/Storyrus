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
from app.workers import runner

logger = logging.getLogger("api.job_pump")

_wake = threading.Event()
_loop: asyncio.AbstractEventLoop | None = None
_task: asyncio.Task[None] | None = None


def bind(loop: asyncio.AbstractEventLoop, task: asyncio.Task[None]) -> None:
    global _loop, _task
    _loop = loop
    _task = task


def kick() -> None:
    """Acorda o pump agora. Se a tarefa morreu, sobe outra no loop da API."""
    _wake.set()
    loop = _loop
    if loop is None or not settings.job_pump_enabled():
        return

    def _ensure() -> None:
        global _task
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
    while True:
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

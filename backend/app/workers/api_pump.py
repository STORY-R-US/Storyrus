"""A API também consome a fila.

No Render não há worker separado: a API processa a fila sozinha. O navegador
mantém a API acordada (polling da prévia). Cada livro enfileirado acorda este
loop na hora — ele não espera o intervalo se há trabalho.
`SKIP LOCKED` impede dois processos de pegarem o mesmo job.

A fila roda numa thread própria, com o seu próprio event loop. Antes ela
dividia o loop do uvicorn: enquanto um livro era montado (imagens, revisão,
PDF), o site respondia em 8–20 s e o health check do Render falhava.
Depois de cada job a memória volta ao sistema (gc + malloc_trim), porque a
instância tem só 512 MB.
"""

from __future__ import annotations

import asyncio
import ctypes
import gc
import logging
import sys
import threading

from app.config import settings
from app.database import SessionLocal
from app.services import process_lifecycle
from app.workers import runner

logger = logging.getLogger("api.job_pump")

_wake = threading.Event()
_thread: threading.Thread | None = None
_thread_lock = threading.Lock()


def release_memory() -> None:
    """Devolve ao sistema a memória dos buffers grandes do último job."""
    gc.collect()
    if not sys.platform.startswith("linux"):
        return
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:  # noqa: BLE001 — só um alívio; sem glibc segue igual
        pass


def _run_thread() -> None:
    try:
        asyncio.run(pump_forever())
    except Exception:
        logger.exception("api job pump thread crashed")


def start() -> threading.Thread:
    """Sobe a thread da fila (uma só por processo)."""
    global _thread
    with _thread_lock:
        if _thread is not None and _thread.is_alive():
            return _thread
        process_lifecycle.reset()
        _thread = threading.Thread(target=_run_thread, name="api-job-pump", daemon=True)
        _thread.start()
        return _thread


def kick() -> None:
    """Acorda o pump agora. Se a thread morreu, sobe outra."""
    if process_lifecycle.draining():
        return
    _wake.set()
    if not settings.job_pump_enabled():
        return
    with _thread_lock:
        alive = _thread is not None and _thread.is_alive()
    if _thread is not None and not alive:
        logger.warning("api job pump restarted")
        start()


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
        if processed:
            release_memory()
        else:
            await asyncio.to_thread(_wake.wait, settings.worker_poll_interval_s)
            _wake.clear()


def stop(timeout: float = 270) -> None:
    """Deixa o job atual salvar a resposta paga; não começa outro."""
    process_lifecycle.begin_shutdown()
    _wake.set()
    current = _thread
    if current is None or not current.is_alive():
        return
    current.join(timeout)
    if current.is_alive():
        logger.error("job pump exceeded shutdown grace; paid journal preserves uncertainty")


async def shutdown(timeout: float = 270) -> None:
    await asyncio.to_thread(stop, timeout)

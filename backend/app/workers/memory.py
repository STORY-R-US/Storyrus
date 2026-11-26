"""Devolve ao sistema a memória dos buffers grandes (imagens, PDF).

A API de produção tem 512 MB e processa a fila no mesmo processo: depois de
cada job e antes da montagem final do livro, a memória livre volta ao sistema.
"""

from __future__ import annotations

import ctypes
import gc
import sys


def release_memory() -> None:
    gc.collect()
    if not sys.platform.startswith("linux"):
        return
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:  # noqa: BLE001 — só um alívio; sem glibc segue igual
        pass

"""Pedido do handler para voltar à fila mais tarde, sem segurar o worker."""

from __future__ import annotations


class JobDeferred(Exception):
    """O job espera um provedor externo (ex.: Kling) e deve ser retomado depois.

    O runner devolve o job para PENDING com `retry_at`, sem contar tentativa,
    sem estorno e sem bloquear os outros jobs da fila.
    """

    def __init__(self, seconds: float = 30.0):
        super().__init__(f"retomar em {seconds}s")
        self.seconds = float(seconds)

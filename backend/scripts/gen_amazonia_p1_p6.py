# -*- coding: utf-8 -*-
"""Gera as páginas 1–6 do alfabeto da Amazônia com o Matteo aprovado.

P1 é dedicatória (sem cena). P3 e P4 já realistas são preservadas.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))
os.chdir(BACKEND)

from _amazonia_common import BookSpec, add_common_args, run  # noqa: E402

from app.ai_clients.factory import get_image_provider  # noqa: E402

SPEC = BookSpec(
    template_id="alfabeto_amazonia",
    child_name="Matteo",
    out_dir=BACKEND / "scripts" / "out" / "amazonia-matteo",
    photo=REPO / "apps" / "web" / "public" / "exemplos" / "foto-matteo.png",
    pdf_name="livro-matteo-amazonia-p1-p6.pdf",
    max_page=6,
    keep={3, 4},
    log_prefix="p1-p6",
)


if __name__ == "__main__":
    parser = add_common_args(
        argparse.ArgumentParser(description="Gera paginas 1-6 Amazonia/Matteo")
    )
    raise SystemExit(run(SPEC, parser.parse_args(), get_image_provider))

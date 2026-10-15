# -*- coding: utf-8 -*-
"""Produz o exemplar Matteo do alfabeto da Amazônia (avatar + páginas + PDF).

Retoma páginas já geradas e, com o livro completo, publica as artes na landing.

Uso (a partir de backend/):

  python scripts/gen_amazonia_matteo.py
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

LANDING_MAP = {
    "capa-amazonia.jpg": "page-03.png",
    "amazonia-1.jpg": "page-03.png",
    "amazonia-3.jpg": "page-15.png",
    "amazonia-4.jpg": "page-17.png",
    "amazonia-5.jpg": "page-22.png",
    "amazonia-6.jpg": "page-29.png",
}

SPEC = BookSpec(
    template_id="alfabeto_amazonia",
    child_name="Matteo",
    out_dir=BACKEND / "scripts" / "out" / "amazonia-matteo",
    photo=REPO / "apps" / "web" / "public" / "exemplos" / "foto-matteo.png",
    pdf_name="livro-matteo-amazonia.pdf",
    concurrency=6,
    log_prefix="amazonia",
    landing_dir=REPO / "apps" / "web" / "public" / "exemplos",
    landing_map=LANDING_MAP,
)


if __name__ == "__main__":
    parser = add_common_args(
        argparse.ArgumentParser(description="Gera o exemplar Matteo da Amazonia")
    )
    raise SystemExit(run(SPEC, parser.parse_args(), get_image_provider))

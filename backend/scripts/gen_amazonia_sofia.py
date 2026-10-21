# -*- coding: utf-8 -*-
"""Gera avatar + páginas do alfabeto da Amazônia com a Sofia.

Uso (a partir de backend/):

  python scripts/gen_amazonia_sofia.py --regen-avatar --only 3
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
    child_name="Sofia",
    gender="girl",
    out_dir=BACKEND / "scripts" / "out" / "amazonia-sofia",
    photo=REPO / "apps" / "web" / "public" / "exemplos" / "foto-sofia.png",
    pdf_name="livro-sofia-amazonia-p3.pdf",
    max_page=4,
    log_prefix="amazonia-sofia",
)


if __name__ == "__main__":
    parser = add_common_args(
        argparse.ArgumentParser(description="Gera paginas Amazonia/Sofia")
    )
    raise SystemExit(run(SPEC, parser.parse_args(), get_image_provider))

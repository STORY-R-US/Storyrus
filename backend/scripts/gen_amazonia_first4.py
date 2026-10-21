# -*- coding: utf-8 -*-
"""Gera as 4 primeiras páginas do alfabeto da Amazônia com o Matteo aprovado.

Retoma de onde parou: o avatar aprovado e as páginas prontas são reusados.

Uso (a partir de backend/):

  python scripts/gen_amazonia_first4.py
  python scripts/gen_amazonia_first4.py --only 3          # refaz só a página 3
  python scripts/gen_amazonia_first4.py --regen-avatar    # refaz o avatar
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
    pdf_name="livro-matteo-amazonia-p1-p4.pdf",
    max_page=4,
    log_prefix="amazonia-4",
)


if __name__ == "__main__":
    parser = add_common_args(
        argparse.ArgumentParser(description="Gera primeiras paginas Amazonia/Matteo")
    )
    raise SystemExit(run(SPEC, parser.parse_args(), get_image_provider))

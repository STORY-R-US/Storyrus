# -*- coding: utf-8 -*-
"""Gera o avatar-base num modelo especifico, sem tocar no avatar aprovado.

Mesmo caminho da producao (`handlers._handle_avatar`): `generate_character` com
[recorte do rosto, foto inteira] e depois `_refine_identity` em 2 passes.

Escreve em `scripts/out/avatar/<modelo>/`, entao rodar em outro modelo nao
sobrescreve nada: o `character.png` de `out/amazonia-matteo/` e o `character_ref`
das 29 paginas ja geradas e nao pode ser perdido.

Custo: 1 + `--passes` chamadas (default 3).

Uso (a partir de backend/):

  python scripts/gen_avatar_model.py --model gpt-image-1
  python scripts/gen_avatar_model.py --report-only --model gpt-image-1
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from PIL import Image, ImageDraw  # noqa: E402

from app.ai_clients.book_prompts import AVATAR_PROMPT  # noqa: E402
from app.ai_clients.book_prompts import STYLE as BOOK_STYLE  # noqa: E402
from app.ai_clients.face_detect import face_reference, identity_images  # noqa: E402
from app.ai_clients.factory import get_image_provider  # noqa: E402
from app.config import settings  # noqa: E402
from app.workers.handlers import _refine_identity  # noqa: E402

PHOTO = REPO / "apps" / "web" / "public" / "exemplos" / "foto-matteo.png"
APPROVED = BACKEND / "scripts" / "out" / "amazonia-matteo" / "character.png"
BASE_OUT = BACKEND / "scripts" / "out" / "avatar"
CELL = 560


def log(msg: str) -> None:
    print(f"[avatar] {msg}", flush=True)


def out_dir(model: str) -> Path:
    return BASE_OUT / model


def _cell(source: Path | bytes, label: str, draw_label: bool = True) -> Image.Image:
    canvas = Image.new("RGB", (CELL, CELL + 22), (255, 255, 255))
    if isinstance(source, Path):
        if not source.exists():
            ImageDraw.Draw(canvas).text((8, CELL // 2), f"{label}: ausente", fill=(150, 20, 20))
            return canvas
        im = Image.open(source).convert("RGB")
    else:
        from io import BytesIO

        im = Image.open(BytesIO(source)).convert("RGB")
    im.thumbnail((CELL, CELL))
    canvas.paste(im, ((CELL - im.width) // 2, 22 + (CELL - im.height) // 2))
    if draw_label:
        ImageDraw.Draw(canvas).text((8, 6), label, fill=(20, 20, 20))
    return canvas


def contact_sheet(out: Path, model: str) -> Path:
    """Recorte do rosto, avatar aprovado, novo cru e novo refinado, na mesma linha."""
    cells = [
        _cell(out / "face-crop.jpg", "1. RECORTE DA FOTO (verdade)"),
        _cell(APPROVED, "2. AVATAR APROVADO (atual)"),
        _cell(out / "character-raw.png", f"3. {model} CRU"),
        _cell(out / "character.png", f"4. {model} + 2 refinos"),
    ]
    sheet = Image.new("RGB", (CELL * len(cells), CELL + 22), (250, 248, 244))
    for col, cell in enumerate(cells):
        sheet.paste(cell, (CELL * col, 0))
    dest = out / "comparacao.png"
    sheet.save(dest, "PNG")
    return dest


async def main(model: str | None, passes: int, report_only: bool) -> int:
    model_id = model or settings.openai_image_model
    if model:
        settings.openai_image_model = model
    out = out_dir(model_id)
    out.mkdir(parents=True, exist_ok=True)

    if report_only:
        log(f"comparacao: {contact_sheet(out, model_id)}")
        return 0
    if not settings.openai_api_key:
        log("OPENAI_API_KEY ausente")
        return 1
    if not PHOTO.exists():
        log(f"foto nao encontrada: {PHOTO}")
        return 1

    unit = settings.price_openai_image_usd
    calls = 1 + max(0, passes)
    budget = f"~${unit * calls:.2f}"
    log(
        f"modelo={model_id} provider=openai "
        f"| {calls} chamadas (1 geracao + {passes} refinos) ({budget})"
    )

    photo = PHOTO.read_bytes()
    log("localizando o rosto da crianca...")
    crop = await face_reference(photo)
    (out / "face-crop.jpg").write_bytes(crop)
    log(f"recorte salvo ({len(crop)} bytes)")

    provider = get_image_provider()
    log("gerando o avatar (recorte do rosto + foto inteira)...")
    try:
        result = await provider.generate_character(
            prompt=AVATAR_PROMPT,
            reference_images=await identity_images(photo),
            style=BOOK_STYLE,
        )
    except Exception as exc:  # noqa: BLE001 - lane fora nao e erro nosso
        log(f"FALHOU na geracao: {type(exc).__name__}: {exc}")
        return 1
    (out / "character-raw.png").write_bytes(result.image_bytes)
    log(f"cru salvo ({len(result.image_bytes)} bytes) meta={result.meta}")

    if passes > 0:
        log(f"refinando a identidade ({passes} passes, mesmo caminho do worker)...")
        refined = await _refine_identity(provider, crop, result, BOOK_STYLE, passes=passes)
        if refined.image_bytes == result.image_bytes:
            # `_refine_identity` engole excecao e devolve o original.
            log("AVISO: refino nao alterou a imagem — provavelmente falhou e foi ignorado")
        result = refined
    (out / "character.png").write_bytes(result.image_bytes)
    log(f"final salvo em {out / 'character.png'} meta={result.meta}")
    log(f"comparacao: {contact_sheet(out, model_id)}")
    log(f"o avatar aprovado em {APPROVED.parent.name}/ NAO foi tocado")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera o avatar-base num modelo especifico")
    parser.add_argument("--model", default=None, help="Default: OPENAI_IMAGE_MODEL.")
    parser.add_argument("--passes", type=int, default=2, help="Refinos de identidade (default 2).")
    parser.add_argument(
        "--report-only", action="store_true", help="Refaz a folha sem gastar imagem."
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.model, args.passes, args.report_only)))

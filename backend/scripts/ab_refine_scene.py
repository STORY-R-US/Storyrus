# -*- coding: utf-8 -*-
"""Mede se o segundo passe de identidade por pagina (`EBOOK_REFINE_SCENE`) paga.

Comparacao PAREADA: cada pagina e gerada UMA vez e o refino e aplicado sobre
essa mesma arte. Duas rodadas independentes nao serviriam — a variacao entre
duas amostras do modelo esconderia o efeito do refino.

Custo: 2 chamadas por pagina (1 crua + 1 refinada), no modelo de `settings`.

Uso (a partir de backend/):

  python scripts/ab_refine_scene.py                  # paginas 2, 5, 6
  python scripts/ab_refine_scene.py --pages 5
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
# Loja do SO: valida TLS mesmo com antivirus/proxy reassinando (o certifi que o
# httpx fixa nao conhece esses roots).

from PIL import Image, ImageDraw  # noqa: E402

from app.ai_clients.book_prompts import STYLE as BOOK_STYLE  # noqa: E402
from app.ai_clients.book_prompts import (  # noqa: E402
    build_scene_prompt,
    infer_expression,
    scene_extras_for_template,
)
from app.ai_clients.face_detect import face_reference  # noqa: E402
from app.ai_clients.factory import get_image_provider  # noqa: E402
from app.config import settings  # noqa: E402
from app.story_templates import illustration_notes, page_layouts, render_template  # noqa: E402
from app.workers.handlers import _parse_pages  # noqa: E402

TEMPLATE_ID = "alfabeto_amazonia"
CHILD_NAME = "Matteo"
PHOTO = REPO / "apps" / "web" / "public" / "exemplos" / "foto-matteo.png"
AVATAR = BACKEND / "scripts" / "out" / "amazonia-matteo" / "character.png"
BASE_OUT = BACKEND / "scripts" / "out" / "ab-refine-scene"
CELL = 620


def out_dir(model: str) -> Path:
    """Uma pasta por modelo: rodar no Pro nao pode apagar a rodada do Flash."""
    return BASE_OUT / model

# Preco por imagem (USD) para o relatorio; so os dois modelos em uso hoje.


def log(msg: str) -> None:
    print(f"[ab-refino] {msg}", flush=True)


def _unit_cost() -> float | None:
    return float(settings.price_openai_image_usd)


async def one_page(
    provider, *, out: Path, idx: int, caption: str, note: str, char: bytes, crop: bytes
):
    """Gera a arte crua e a versao refinada da MESMA arte. Devolve (raw, refined)."""
    prompt = build_scene_prompt(
        page=idx,
        text=caption,
        scene=(note or caption)[:900],
        expression=infer_expression(caption, note),
        # Mesmos extras do worker: medir com prompt diferente do de producao
        # mediria outra coisa.
        extras=scene_extras_for_template(TEMPLATE_ID),
        child_name=CHILD_NAME,
    )
    log(f"pagina {idx:02d}: gerando arte crua...")
    raw = await provider.generate_scene(
        prompt=prompt, character_ref=char, style=BOOK_STYLE, photo=crop
    )
    (out / f"page-{idx:02d}-raw.png").write_bytes(raw.image_bytes)

    log(f"pagina {idx:02d}: refinando a MESMA arte...")
    refined = await provider.refine_scene(
        character_ref=char, scene=raw.image_bytes, style=BOOK_STYLE, photo=crop
    )
    (out / f"page-{idx:02d}-refined.png").write_bytes(refined.image_bytes)
    return raw, refined


def diff_report(out: Path, pages: list[int]) -> Path | None:
    """Quanto e onde o refino mudou a arte. Sem isso a comparacao vira palpite.

    Julgar identidade em miniatura nao decide nada: o que decide e o tamanho da
    mudanca e se ela cai no ROSTO (efeito pretendido) ou espalhada pela cena
    (o refino redesenhou o que nao devia).
    """
    from PIL import ImageChops

    rows = []
    for idx in pages:
        raw_path = out / f"page-{idx:02d}-raw.png"
        ref_path = out / f"page-{idx:02d}-refined.png"
        if not (raw_path.exists() and ref_path.exists()):
            continue
        raw = Image.open(raw_path).convert("RGB")
        ref = Image.open(ref_path).convert("RGB")
        if ref.size != raw.size:
            ref = ref.resize(raw.size)
        diff = ImageChops.difference(raw, ref).convert("L")
        pixels = list(diff.getdata())
        total = len(pixels)
        mean = sum(pixels) / total
        changed = sum(1 for p in pixels if p > 24) / total
        box = diff.point(lambda p: 255 if p > 48 else 0).getbbox()
        rows.append((idx, raw, ref, diff, mean, changed, box))
        log(
            f"pagina {idx:02d}: mudanca media {mean:5.1f}/255 | "
            f"{changed * 100:5.1f}% dos pixels acima do ruido | regiao {box}"
        )

    if not rows:
        return None
    sheet = Image.new("RGB", (CELL * 3, 34 + CELL * len(rows)), (250, 248, 244))
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 10), f"ZOOM na regiao que mudou: SEM refino [{out.name}]", fill=(20, 20, 20))
    draw.text((CELL + 10, 10), "COM refino", fill=(20, 20, 20))
    draw.text((CELL * 2 + 10, 10), "mapa da diferenca", fill=(20, 20, 20))
    for row, (idx, raw, ref, diff, mean, changed, box) in enumerate(rows):
        y = 34 + row * CELL
        crop = box or (0, 0, raw.width, raw.height)
        for col, im in ((0, raw), (1, ref), (2, diff.convert("RGB"))):
            cell = im.crop(crop)
            cell.thumbnail((CELL, CELL))
            canvas = Image.new("RGB", (CELL, CELL), (255, 255, 255))
            canvas.paste(cell, ((CELL - cell.width) // 2, (CELL - cell.height) // 2))
            sheet.paste(canvas, (CELL * col, y))
        draw.text((6, y + 6), f"p{idx:02d} {mean:.1f}/255", fill=(150, 20, 20))
    dest = out / "diferenca.png"
    sheet.save(dest, "PNG")
    return dest


def _fit(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGB")
    im.thumbnail((CELL, CELL))
    canvas = Image.new("RGB", (CELL, CELL), (255, 255, 255))
    canvas.paste(im, ((CELL - im.width) // 2, (CELL - im.height) // 2))
    return canvas


def contact_sheet(out: Path, pages: list[int]) -> Path:
    """Grade para julgar a olho: coluna 1 crua, coluna 2 refinada, 1 linha por pagina."""
    header = 34
    sheet = Image.new("RGB", (CELL * 3, header + CELL * len(pages)), (250, 248, 244))
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 10), f"REFERENCIA (avatar) - modelo: {out.name}", fill=(20, 20, 20))
    draw.text((CELL + 10, 10), "SEM refino (1 chamada)", fill=(20, 20, 20))
    draw.text((CELL * 2 + 10, 10), "COM refino (2 chamadas)", fill=(20, 20, 20))

    ref = _fit(AVATAR)
    for row, idx in enumerate(pages):
        y = header + row * CELL
        sheet.paste(ref, (0, y))
        draw.text((10, y + 8), f"p{idx:02d}", fill=(120, 20, 20))
        for col, kind in ((1, "raw"), (2, "refined")):
            path = out / f"page-{idx:02d}-{kind}.png"
            if path.exists():
                sheet.paste(_fit(path), (CELL * col, y))
    dest = out / "comparacao.png"
    sheet.save(dest, "PNG")
    return dest


async def main(pages: list[int], model: str | None, report_only: bool) -> int:
    if model:
        settings.openai_image_model = model
    model_id = settings.openai_image_model
    out = out_dir(model_id)

    if report_only:
        out.mkdir(parents=True, exist_ok=True)
        sheet = contact_sheet(out, pages)
        report = diff_report(out, pages)
        log(f"comparacao: {sheet}")
        log(f"diferenca: {report}" if report else "sem pares para comparar")
        return 0
    if not settings.openai_api_key:
        log("OPENAI_API_KEY ausente")
        return 1
    if not AVATAR.exists():
        log(f"avatar aprovado nao encontrado: {AVATAR}")
        return 1
    out.mkdir(parents=True, exist_ok=True)

    unit = _unit_cost()
    budget = f"~${unit * 2 * len(pages):.2f}" if unit else "custo desconhecido"
    log(
        f"modelo={model_id} provider=openai "
        f"| {len(pages)} paginas x 2 chamadas = {len(pages) * 2} imagens ({budget})"
    )

    char = AVATAR.read_bytes()
    crop = await face_reference(PHOTO.read_bytes())
    story = render_template(TEMPLATE_ID, CHILD_NAME, gender="boy")
    captions = _parse_pages(story)
    notes = illustration_notes(TEMPLATE_ID, CHILD_NAME)
    layouts = page_layouts(TEMPLATE_ID)

    provider = get_image_provider()
    done: list[int] = []
    for idx in pages:
        if idx - 1 >= len(captions):
            log(f"pagina {idx:02d} fora do template — ignorada")
            continue
        if layouts[idx - 1] == "dedication":
            log(f"pagina {idx:02d} e dedicatoria (sem ilustracao) — ignorada")
            continue
        try:
            raw, refined = await one_page(
                provider,
                out=out,
                idx=idx,
                caption=captions[idx - 1],
                note=notes[idx - 1] if idx - 1 < len(notes) else "",
                char=char,
                crop=crop,
            )
        except Exception as exc:  # noqa: BLE001 - um erro nao deve perder as paginas ok
            log(f"pagina {idx:02d} FALHOU: {type(exc).__name__}: {exc}")
            continue
        log(f"pagina {idx:02d} ok (crua={raw.meta} refinada={refined.meta})")
        done.append(idx)

    if not done:
        log("nenhuma pagina gerada — nada para comparar")
        return 1
    dest = contact_sheet(out, done)
    log(f"comparacao: {dest}")
    report = diff_report(out, done)
    if report:
        log(f"diferenca: {report}")
    log(f"gastou {len(done) * 2} imagens" + (f" (~${unit * 2 * len(done):.2f})" if unit else ""))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A/B pareado do refino de cena")
    parser.add_argument("--pages", nargs="+", type=int, default=[2, 5, 6], metavar="N")
    parser.add_argument(
        "--model",
        default=None,
        help="Fixa o modelo do experimento (default: OPENAI_IMAGE_MODEL).",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Refaz as folhas de comparacao do que ja existe, sem gastar imagem.",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.pages, args.model, args.report_only)))

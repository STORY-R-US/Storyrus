# -*- coding: utf-8 -*-
"""Gera avatares TMT das fotos em `../CRIANÇAS APROVADAS`.

Cada foto vira `avatar-<slug>.png` na mesma pasta. Artefatos de trabalho
ficam em `scripts/out/avatar/aprovados/<slug>/`. O character.png do livro
Matteo (`out/amazonia-matteo/`) nao e tocado.

Mesmo caminho da producao: recorte do rosto + generate_character CGI + 1 refine Gemini.

Uso (a partir de backend/):

  python scripts/gen_avatars_aprovados.py
  python scripts/gen_avatars_aprovados.py --only emilia facundo
  python scripts/gen_avatars_aprovados.py --force --only martin
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import unicodedata
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
PHOTOS_DIR = REPO.parent / "CRIANÇAS APROVADAS"
BOOK_CHAR = BACKEND / "scripts" / "out" / "amazonia-matteo" / "character.png"
BASE_OUT = BACKEND / "scripts" / "out" / "avatar" / "aprovados"
CELL = 560
MIN_BYTES = 1000
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
SKIP_PREFIXES = ("avatar-", "character", "face-crop", "comparacao")


def slugify(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    slug = "".join(c.lower() if c.isalnum() else "-" for c in ascii_name).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "crianca"


def _is_source_photo(path: Path) -> bool:
    if path.suffix.lower() not in IMAGE_EXTS:
        return False
    stem = path.stem.lower()
    return not any(stem.startswith(p) for p in SKIP_PREFIXES)


@dataclass(frozen=True)
class Child:
    slug: str
    photo: Path

    @property
    def out_dir(self) -> Path:
        dest = BASE_OUT / self.slug
        if dest.resolve() == BOOK_CHAR.parent.resolve():
            raise RuntimeError(f"recusa: saida colidiria com {BOOK_CHAR}")
        return dest

    @property
    def published(self) -> Path:
        return self.photo.with_name(f"avatar-{self.slug}.png")


def discover(photos_dir: Path) -> list[Child]:
    """Fotos soltas ou uma pasta por crianca."""
    if not photos_dir.is_dir():
        return []
    found: dict[str, Child] = {}

    def add(slug: str, photo: Path) -> None:
        if slug and slug not in found:
            found[slug] = Child(slug, photo)

    for child_dir in sorted(p for p in photos_dir.iterdir() if p.is_dir()):
        photos = [p for p in sorted(child_dir.iterdir()) if p.is_file() and _is_source_photo(p)]
        if photos:
            add(slugify(child_dir.name), photos[0])

    for photo in sorted(p for p in photos_dir.iterdir() if p.is_file() and _is_source_photo(p)):
        add(slugify(photo.stem), photo)

    return list(found.values())


def children(only: list[str] | None = None, *, photos_dir: Path | None = None) -> list[Child]:
    rows = discover(photos_dir or PHOTOS_DIR)
    if not rows:
        raise ValueError(f"nenhuma foto em {photos_dir or PHOTOS_DIR}")
    wanted = {slugify(s) for s in (only or [])}
    if wanted:
        known = {c.slug for c in rows}
        unknown = wanted - known
        if unknown:
            raise ValueError(f"crianca desconhecida: {sorted(unknown)}")
        rows = [c for c in rows if c.slug in wanted]
    return rows


def is_ready(path: Path) -> bool:
    return path.exists() and path.stat().st_size > MIN_BYTES


def log(msg: str) -> None:
    print(f"[avatar] {msg}", flush=True)


def _cell(source: Path | bytes, label: str) -> Image.Image:
    canvas = Image.new("RGB", (CELL, CELL + 22), (255, 255, 255))
    if isinstance(source, Path):
        if not source.exists():
            ImageDraw.Draw(canvas).text((8, CELL // 2), f"{label}: ausente", fill=(150, 20, 20))
            return canvas
        im = Image.open(source).convert("RGB")
    else:
        im = Image.open(BytesIO(source)).convert("RGB")
    im.thumbnail((CELL, CELL))
    canvas.paste(im, ((CELL - im.width) // 2, 22 + (CELL - im.height) // 2))
    ImageDraw.Draw(canvas).text((8, 6), label, fill=(20, 20, 20))
    return canvas


def contact_sheet(child: Child) -> Path:
    out = child.out_dir
    cells = [
        _cell(child.photo, "1. FOTO"),
        _cell(out / "face-crop.jpg", "2. RECORTE"),
        _cell(out / "character-raw.png", "3. CRU"),
        _cell(out / "character.png", "4. + FAL ROSTO"),
    ]
    sheet = Image.new("RGB", (CELL * len(cells), CELL + 22), (250, 248, 244))
    for col, cell in enumerate(cells):
        sheet.paste(cell, (CELL * col, 0))
    dest = out / "comparacao.png"
    sheet.save(dest, "PNG")
    return dest


def publish_avatar(child: Child, data: bytes) -> Path:
    dest = child.published
    Image.open(BytesIO(data)).convert("RGB").save(dest, "PNG")
    return dest


async def generate_one(child: Child, *, force: bool, budget_s: float) -> str:
    """Gera um avatar. Devolve 'ok' | 'skip' | 'fail' | 'outage'."""
    sys.path.insert(0, str(BACKEND))
    sys.path.insert(0, str(BACKEND / "scripts"))
    os.chdir(BACKEND)

    from _amazonia_common import Budget, write_atomic

    from app.ai_clients.book_prompts import AVATAR_PROMPT, AVATAR_STYLE
    from app.ai_clients.face_detect import face_reference, identity_images
    from app.ai_clients.factory import get_image_provider
    from app.ai_clients.resilience import OutageError, retry_until
    from app.config import settings
    from app.workers.handlers import _lock_avatar_identity

    if not child.photo.exists():
        log(f"{child.slug}: foto ausente ({child.photo})")
        return "fail"
    dest = child.out_dir / "character.png"
    child.out_dir.mkdir(parents=True, exist_ok=True)
    if is_ready(dest) and is_ready(child.published) and not force:
        log(f"{child.slug}: ja existe, pulando ({child.published})")
        contact_sheet(child)
        return "skip"

    settings.offline_fallback = False
    budget = Budget(budget_s)
    photo = child.photo.read_bytes()
    log(f"{child.slug}: localizando o rosto ({child.photo.name})...")
    crop = await face_reference(photo)
    write_atomic(child.out_dir / "face-crop.jpg", crop)

    provider = get_image_provider()
    log(f"{child.slug}: provider={type(provider).__name__} style=cgi-3d")

    async def gen():
        try:
            result = await provider.generate_character(
                prompt=AVATAR_PROMPT,
                reference_images=await identity_images(photo),
                style=AVATAR_STYLE,
            )
        except Exception:
            result = await provider.generate_realistic(
                photo=crop, prompt=AVATAR_PROMPT, style=AVATAR_STYLE
            )
        write_atomic(child.out_dir / "character-raw.png", result.image_bytes)
        return await _lock_avatar_identity(provider, crop, result, AVATAR_STYLE)

    try:
        result = await retry_until(
            f"avatar {child.slug}", gen, budget_s=budget.remaining(), log=log
        )
    except OutageError as exc:
        log(f"{child.slug}: gerador fora ({exc})")
        return "outage"
    except Exception as exc:  # noqa: BLE001
        log(f"{child.slug}: falhou ({type(exc).__name__}: {exc})")
        return "fail"

    write_atomic(dest, result.image_bytes)
    published = publish_avatar(child, result.image_bytes)
    log(f"{child.slug}: salvo {published} ({published.stat().st_size} bytes) meta={result.meta}")
    log(f"{child.slug}: comparacao {contact_sheet(child)}")
    log(f"livro Matteo em {BOOK_CHAR.parent.name}/ NAO foi tocado")
    return "ok"


async def main(only: list[str] | None, force: bool, budget_min: float) -> int:
    sys.path.insert(0, str(BACKEND))
    os.chdir(BACKEND)
    os.environ.setdefault("OFFLINE_FALLBACK", "false")

    from app.config import settings

    if not settings.openai_api_key:
        log("OPENAI_API_KEY ausente")
        return 1
    if not PHOTOS_DIR.is_dir():
        log(f"pasta nao encontrada: {PHOTOS_DIR}")
        return 1

    try:
        batch = children(only)
    except ValueError as exc:
        log(str(exc))
        return 1

    log(
        f"{len(batch)} criancas em {PHOTOS_DIR} | provider=openai "
        f"model={settings.openai_image_model} | "
        f"~{1 + 1} chamadas/crianca | offline={settings.offline_fallback}"
    )
    for child in batch:
        log(f"  - {child.slug}: {child.photo.name}")
    counts = {"ok": 0, "skip": 0, "fail": 0, "outage": 0}
    for child in batch:
        status = await generate_one(child, force=force, budget_s=max(0.0, budget_min) * 60)
        counts[status] = counts.get(status, 0) + 1
        if status == "outage":
            log("gerador fora — parando o lote")
            break
    log(
        f"resumo: gerados={counts['ok']} pulados={counts['skip']} "
        f"falha={counts['fail']} queda={counts['outage']}"
    )
    return 0 if counts["fail"] == 0 and counts["outage"] == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Avatares CGI 3D das criancas aprovadas")
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="ID",
        default=None,
        help="so estas criancas (slug do arquivo/pasta, ex.: emilia martin facundo)",
    )
    parser.add_argument("--force", action="store_true", help="regera mesmo se ja existir")
    parser.add_argument(
        "--budget-min",
        type=float,
        default=15.0,
        help="minutos de paciencia por crianca (default 15)",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.only, args.force, args.budget_min)))

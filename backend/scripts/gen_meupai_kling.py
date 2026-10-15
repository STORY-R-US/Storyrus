#!/usr/bin/env python3
"""Anima cada página do Meu Pai, Meu Herói via Kling (image2video) e concatena.

Requer KLING_API_KEY (console novo) — ou o par legado
KLING_ACCESS_KEY + KLING_SECRET_KEY — no ambiente (ou backend/.env).

Uso:
  cd backend
  export KLING_API_KEY=...
  .venv/bin/python scripts/gen_meupai_kling.py
  .venv/bin/python scripts/gen_meupai_kling.py --limit 1          # smoke test
  .venv/bin/python scripts/gen_meupai_kling.py --concurrency 2

Saídas:
  apps/web/public/exemplos/video-meupai-heroi-kling.mp4
  /opt/cursor/artifacts/Meu-Pai-Meu-Heroi-Kling.mp4
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Carrega backend/.env se existir (sem sobrescrever env já definido).
_env = ROOT / ".env"
if _env.is_file():
    for line in _env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = val

from app.ai_clients.video_kling import KlingVideoProvider  # noqa: E402
from app.config import settings  # noqa: E402

BOOK_DIR = ROOT.parent / "apps" / "web" / "public" / "exemplos" / "meupai-heroi"
OUT_MP4 = ROOT.parent / "apps" / "web" / "public" / "exemplos" / "video-meupai-heroi-kling.mp4"
ARTIFACT = Path("/opt/cursor/artifacts/Meu-Pai-Meu-Heroi-Kling.mp4")
CLIPS_DIR = ROOT.parent / "apps" / "web" / "public" / "exemplos" / "meupai-heroi" / "kling-clips"

# Página + prompt de movimento (Kling image2video: 5s ou 10s).
PAGES: list[tuple[str, str]] = [
    (
        "capa.png",
        "Gentle cinematic motion: father holding toddler smiles warmly, "
        "soft breeze in hair, helicopter blades idle slowly, sunny coastal light.",
    ),
    (
        "pagina-02.jpg",
        "Warm hug animation: father kisses toddler cheek, both smile, "
        "subtle hair movement, soft sunny outdoor light.",
    ),
    (
        "pagina-03.jpg",
        "Father and toddler walk hand in hand along wooden pier toward the sea, "
        "gentle camera push, sailboat drifts, sparkling water.",
    ),
    (
        "pagina-04.jpg",
        "Father hugs smiling toddler tightly, tender cheek kiss, "
        "soft indoor light, subtle natural motion.",
    ),
    (
        "pagina-05.jpg",
        "Father and toddler walk on sunny beach looking at each other smiling, "
        "waves roll gently, hair moves in breeze.",
    ),
    (
        "pagina-06.jpg",
        "Father and toddler run playfully on beach, joyful laughter, "
        "sand kicks lightly, ocean waves in background.",
    ),
    (
        "pagina-07.jpg",
        "Father helps toddler balance on blue bike, encouraging smile, "
        "slight forward motion, sunny park.",
    ),
    (
        "pagina-08.jpg",
        "Father and toddler on floor reading picture book, child points at page, "
        "warm indoor glow, subtle page turn motion.",
    ),
    (
        "pagina-09.jpg",
        "Father and toddler drawing together at table, crayon strokes, "
        "smiles and soft hand movement, sunny room.",
    ),
    (
        "pagina-10.jpg",
        "Toddler kicks soccer ball while father cheers proudly, "
        "ball rolls forward, sunny park trees sway lightly.",
    ),
    (
        "pagina-11.jpg",
        "Father kisses toddler forehead at bedtime, child hugs teddy bear, "
        "soft lamp glow, gentle breathing motion.",
    ),
    (
        "pagina-12.jpg",
        "Father and toddler sit on blanket at sunset looking at each other, "
        "golden light shifts, warm smiles.",
    ),
    (
        "pagina-13.jpg",
        "Father and toddler reading book on bed, child points at illustration, "
        "soft sunlight, cozy bedroom motion.",
    ),
    (
        "pagina-14.jpg",
        "Father holds toddler on balcony at sunset, child points to horizon, "
        "string lights twinkle, warm breeze.",
    ),
    (
        "pagina-15.jpg",
        "Father hugs and kisses toddler at sunset, emotional warm embrace, "
        "golden hour glow, soft camera drift.",
    ),
    (
        "pagina-16.jpg",
        "Father hugs smiling toddler at sunset on wooden deck, "
        "heartfelt kiss on cheek, glowing sky.",
    ),
    (
        "contracapa.jpg",
        "Father and child sit watching sunset with teddy bear, "
        "peaceful stillness, soft clouds drift, golden light.",
    ),
]

DURATION_S = 5  # Kling: 5 ou 10
POLL_INTERVAL = 4.0
POLL_TIMEOUT = 360.0


async def _animate_one(
    provider: KlingVideoProvider,
    image: bytes,
    prompt: str,
    out: Path,
    *,
    sem: asyncio.Semaphore,
    label: str,
) -> Path:
    import httpx

    async with sem:
        if out.is_file() and out.stat().st_size > 10_000:
            print(f"  reuse {out.name}", flush=True)
            return out

        print(f"  create {label}…", flush=True)
        task = await provider.create_video(image=image, prompt=prompt, duration_s=DURATION_S)
        print(f"  task {label} → {task.provider_task_id}", flush=True)
        deadline = time.monotonic() + POLL_TIMEOUT
        while task.status not in ("DONE", "FAILED"):
            if time.monotonic() > deadline:
                raise RuntimeError(f"Timeout Kling task {task.provider_task_id}")
            await asyncio.sleep(POLL_INTERVAL)
            task = await provider.poll_video(provider_task_id=task.provider_task_id)
            print(f"  status {label} {task.status}", flush=True)

        if task.status == "FAILED" or not task.video_url:
            raise RuntimeError(f"Kling falhou: {task.provider_task_id}")

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.get(task.video_url)
            resp.raise_for_status()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(resp.content)
        print(f"  saved {out.name} ({len(resp.content)} bytes)", flush=True)
        return out


def _concat(clips: list[Path], dest: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="kling_concat_") as tmp:
        root = Path(tmp)
        # Normaliza para 1080x1080 h264 antes do concat
        normalized: list[Path] = []
        for i, clip in enumerate(clips):
            norm = root / f"n_{i:03d}.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(clip),
                    "-vf",
                    "scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,fps=24,format=yuv420p",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "20",
                    "-an",
                    str(norm),
                ],
                check=True,
                capture_output=True,
            )
            normalized.append(norm)

        lst = root / "list.txt"
        lst.write_text("\n".join(f"file '{p.as_posix()}'" for p in normalized), encoding="utf-8")
        merged = root / "merged.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(lst),
                "-c",
                "copy",
                str(merged),
            ],
            check=True,
            capture_output=True,
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(merged.read_bytes())


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Gera vídeo Kling do livro Meu Pai, Meu Herói")
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Processa só as N primeiras páginas (0 = todas). Útil para smoke test.",
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Quantas tarefas Kling em paralelo (default 1; cuidado com rate limit).",
    )
    p.add_argument(
        "--skip-concat",
        action="store_true",
        help="Só gera clips; não monta o MP4 final.",
    )
    return p.parse_args()


async def main() -> None:
    args = _parse_args()
    has_api_key = bool(settings.kling_api_key)
    has_legacy = bool(settings.kling_access_key and settings.kling_secret_key)
    if not (has_api_key or has_legacy):
        raise SystemExit(
            "KLING_API_KEY ausente (ou par legado KLING_ACCESS_KEY/SECRET_KEY).\n"
            "Cole a API Key do console kling.ai/dev/api-key em backend/.env e rode de novo."
        )

    pages = PAGES[: args.limit] if args.limit and args.limit > 0 else PAGES
    concurrency = max(1, int(args.concurrency))
    provider = KlingVideoProvider()
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(concurrency)

    jobs: list[asyncio.Task[Path]] = []
    clip_paths: list[Path] = []
    for i, (fname, prompt) in enumerate(pages, start=1):
        src = BOOK_DIR / fname
        if not src.is_file():
            raise FileNotFoundError(src)
        out = CLIPS_DIR / f"clip-{i:02d}.mp4"
        clip_paths.append(out)
        label = f"[{i}/{len(pages)}] {fname}"
        print(label, flush=True)
        jobs.append(
            asyncio.create_task(
                _animate_one(
                    provider,
                    src.read_bytes(),
                    prompt,
                    out,
                    sem=sem,
                    label=label,
                )
            )
        )

    await asyncio.gather(*jobs)

    if args.skip_concat:
        print(f"OK: {len(clip_paths)} clips em {CLIPS_DIR}", flush=True)
        return

    print("Concatenando…", flush=True)
    _concat(clip_paths, OUT_MP4)
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_bytes(OUT_MP4.read_bytes())
    print(f"OK: {OUT_MP4} ({OUT_MP4.stat().st_size} bytes)", flush=True)
    print(f"OK: {ARTIFACT}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())

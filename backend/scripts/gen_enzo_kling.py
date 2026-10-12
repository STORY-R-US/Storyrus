#!/usr/bin/env python3
"""Anima cada página de Enzo, Meu Primo Predileto via Kling (image2video).

Requer KLING_API_KEY (ou par legado AK/SK) no ambiente / backend/.env.

Uso:
  cd backend
  export KLING_API_KEY=...
  .venv/bin/python scripts/gen_enzo_kling.py
  .venv/bin/python scripts/gen_enzo_kling.py --limit 1
  .venv/bin/python scripts/gen_enzo_kling.py --concurrency 2

Saídas:
  apps/web/public/exemplos/video-enzo-primo-kling.mp4
  /opt/cursor/artifacts/Enzo-Meu-Primo-Predileto-Kling.mp4
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

BOOK_DIR = ROOT.parent / "apps" / "web" / "public" / "exemplos" / "enzo-primo"
OUT_MP4 = ROOT.parent / "apps" / "web" / "public" / "exemplos" / "video-enzo-primo-kling.mp4"
ARTIFACT = Path("/opt/cursor/artifacts/Enzo-Meu-Primo-Predileto-Kling.mp4")
CLIPS_DIR = BOOK_DIR / "kling-clips"

# Página + prompt de movimento (Kling: 5s ou 10s).
PAGES: list[tuple[str, str]] = [
    (
        "capa.png",
        "Two boys hugging smile warmly on a sunny beach, soft breeze in hair, "
        "sailboat drifts gently, golden light, subtle natural motion, keep text still.",
    ),
    (
        "pagina-02.jpg",
        "Older boy and toddler sit on a couch reading a picture book together, "
        "gentle page turn, soft smiles, warm indoor light, subtle breathing motion.",
    ),
    (
        "pagina-03.jpg",
        "Older boy kisses toddler on the cheek affectionately, both smile, "
        "soft outdoor breeze, flowers sway lightly, warm sunlight.",
    ),
    (
        "pagina-04.jpg",
        "Two boys build a sandcastle on the beach, hands moving sand gently, "
        "blue bucket nearby, ocean waves roll softly in background.",
    ),
    (
        "pagina-05.jpg",
        "Older boy shows a large seashell to the toddler, toddler reaches curiously, "
        "soft sea breeze, sparkling coastal light, gentle smiles.",
    ),
    (
        "pagina-06.jpg",
        "Boys walk hand in hand along the sunny shoreline, slight forward motion, "
        "hair moves in breeze, bright summer day, joyful pace.",
    ),
    (
        "pagina-07.jpg",
        "Boys play with colorful wooden building blocks indoors, stacking gently, "
        "warm room light, soft hand movements, happy expressions.",
    ),
    (
        "pagina-08.jpg",
        "Boys play with toy trucks on the floor, trucks roll slightly forward, "
        "playful smiles, cozy indoor light, subtle natural motion.",
    ),
    (
        "pagina-09.jpg",
        "Both boys lie on a patterned pillow laughing joyfully, subtle head movement, "
        "warm intimate light, genuine laughter energy.",
    ),
    (
        "pagina-10.jpg",
        "Tender cheek-to-cheek hug between older boy and toddler, soft breathing, "
        "gentle smile, warm protective embrace, calm motion.",
    ),
    (
        "pagina-11.jpg",
        "Older boy helps toddler walk down stone garden steps, holding hands, "
        "careful slow steps, encouraging smile, sunny garden.",
    ),
    (
        "pagina-12.jpg",
        "Boys sit in a field of white flowers watching a monarch butterfly, "
        "butterfly flutters gently, soft breeze in flowers, golden light.",
    ),
    (
        "pagina-13.jpg",
        "Boys look through a physical photo album together, soft page turn, "
        "warm indoor glow, curious smiles, subtle natural motion.",
    ),
    (
        "pagina-14.jpg",
        "Toddler looks at a laptop video call while older boy waves on screen, "
        "screen glow, soft wave motion, warm connection, gentle smiles.",
    ),
    (
        "pagina-15.jpg",
        "Boys sit on a wooden pier watching sunset over the ocean, "
        "clouds drift slowly, sailboats idle, golden hour glow, peaceful stillness.",
    ),
    (
        "contracapa.png",
        "Final close-up of two boys smiling together, soft warm light, "
        "subtle natural motion, keep title text still, heartfelt ending.",
    ),
]

DURATION_S = 5
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
    with tempfile.TemporaryDirectory(prefix="enzo_kling_") as tmp:
        root = Path(tmp)
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
    p = argparse.ArgumentParser(description="Gera vídeo Kling de Enzo, Meu Primo Predileto")
    p.add_argument("--limit", type=int, default=0, help="Só as N primeiras páginas (0=todas)")
    p.add_argument("--concurrency", type=int, default=1, help="Tarefas Kling em paralelo")
    p.add_argument("--skip-concat", action="store_true", help="Só gera clips")
    return p.parse_args()


async def main() -> None:
    args = _parse_args()
    has_api_key = bool(settings.kling_api_key)
    has_legacy = bool(settings.kling_access_key and settings.kling_secret_key)
    if not (has_api_key or has_legacy):
        raise SystemExit(
            "KLING_API_KEY ausente (ou par legado KLING_ACCESS_KEY/SECRET_KEY).\n"
            "Defina em backend/.env e rode de novo."
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

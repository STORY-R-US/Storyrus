#!/usr/bin/env python3
"""Gera vídeo narrado HD de Enzo, Meu Primo Predileto.

Ken Burns 1080p (páginas landscape com letterbox) + TTS PT-BR + trilha suave.
Substitui o MP4 Kling mudo/distorcido na landing.

Uso:
  cd backend
  .venv/bin/python scripts/gen_enzo_video.py

Saídas:
  apps/web/public/exemplos/video-enzo-primo-kling.mp4
  /opt/cursor/artifacts/Enzo-Meu-Primo-Predileto-Narrado.mp4
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
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

from app.media.tts import EdgeTtsProvider, TtsError, get_tts_provider  # noqa: E402

BOOK_DIR = ROOT.parent / "apps" / "web" / "public" / "exemplos" / "enzo-primo"
OUT_MP4 = ROOT.parent / "apps" / "web" / "public" / "exemplos" / "video-enzo-primo-kling.mp4"
ARTIFACT = Path("/opt/cursor/artifacts/Enzo-Meu-Primo-Predileto-Narrado.mp4")
MUSIC_PATH = ROOT / "app" / "assets" / "audio" / "bed.mp3"

SIZE = 1080
FPS = 25

# Textos das páginas (transcritos das imagens do livro).
PAGES: list[tuple[str, str]] = [
    ("capa.png", "Enzo, meu primo predileto."),
    (
        "pagina-02.jpg",
        "Enzo é meu primo, meu amigo de coração, quando estamos juntos, é pura diversão!",
    ),
    (
        "pagina-03.jpg",
        "Quando Enzo chega, meu sorriso aparece, e cada momento feliz nunca se esquece.",
    ),
    (
        "pagina-04.jpg",
        "Na areia construímos castelos perto do mar. Com meu primo querido, é tão gostoso brincar!",
    ),
    (
        "pagina-05.jpg",
        "Enzo me mostra o mundo com carinho e atenção. Cada nova descoberta traz alegria ao coração.",
    ),
    (
        "pagina-06.jpg",
        "De mãos dadas caminhamos, com o sol a iluminar. Ao lado do meu primo, há tanto para explorar!",
    ),
    (
        "pagina-07.jpg",
        "Quando algo é difícil, Enzo vem me ajudar. Com paciência e carinho, me ensina a tentar.",
    ),
    (
        "pagina-08.jpg",
        "Dividimos os brinquedos, os sorrisos e a diversão. Compartilhar com carinho faz bem ao coração.",
    ),
    (
        "pagina-09.jpg",
        "Quando Enzo faz graça, começo logo a sorrir. Com tantas brincadeiras, não consigo parar de rir!",
    ),
    (
        "pagina-10.jpg",
        "O abraço do meu primo é cheio de proteção. Nele encontro carinho, amizade e união.",
    ),
    (
        "pagina-11.jpg",
        "Enzo cuida de mim com respeito e atenção. Aprendo que o carinho se demonstra em cada ação.",
    ),
    (
        "pagina-12.jpg",
        "Entre flores e borboletas, temos tanto a descobrir. Com Enzo ao meu lado, há mil razões para sorrir.",
    ),
    (
        "pagina-13.jpg",
        "Cada dia ao seu lado é uma linda recordação. São momentos especiais que guardo no coração.",
    ),
    (
        "pagina-14.jpg",
        "Mesmo quando estamos longe, o carinho vai ficar. Pois o amor entre primos nunca deixa de brilhar.",
    ),
    (
        "pagina-15.jpg",
        "Vamos crescer e aprender, novas histórias construir. Com meu primo predileto, há muitos sonhos por vir.",
    ),
    (
        "contracapa.png",
        "Enzo, meu primo predileto, meu amigo tão querido. Ter você na minha vida é um presente colorido! "
        "Histórias personalizadas para momentos inesquecíveis. Story R Us.",
    ),
]


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg falhou ({proc.returncode}): {(proc.stderr or proc.stdout)[-1200:]}"
        )


def _ffprobe_duration(path: Path) -> float:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return 5.0
    try:
        return max(1.2, float((proc.stdout or "5").strip()))
    except ValueError:
        return 5.0


def _ensure_music_bed(dest: Path) -> bytes:
    """Trilha suave procedural (sem dependência externa) se bed.mp3 ausente."""
    if dest.is_file() and dest.stat().st_size > 10_000:
        return dest.read_bytes()
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=196:duration=180,volume=0.08",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=246.94:duration=180,volume=0.06",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=293.66:duration=180,volume=0.05",
            "-f",
            "lavfi",
            "-i",
            "anoisesrc=color=pink:amplitude=0.015:duration=180",
            "-filter_complex",
            "[0][1][2][3]amix=inputs=4:duration=longest:dropout_transition=0,"
            "alimiter=limit=0.25,afade=t=in:st=0:d=2,afade=t=out:st=175:d=5",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            str(dest),
        ]
    )
    return dest.read_bytes()


def _scene_clip(image: Path, audio: Path, out: Path, *, idx: int) -> None:
    """Letterbox landscape → 1080² com fundo desfocado + Ken Burns suave."""
    duration = _ffprobe_duration(audio) + 0.45
    frames = max(FPS + 1, int(duration * FPS))
    # Alterna zoom-in / zoom-out leve para variar o ritmo.
    if idx % 2 == 0:
        z_expr = "min(zoom+0.00055,1.06)"
    else:
        z_expr = "if(eq(on,1),1.06,max(zoom-0.00055,1.0))"

    # Fundo: página escalada+blur; frente: página inteira com pad; zoompan no resultado.
    vf = (
        f"[0:v]scale={SIZE}:{SIZE}:force_original_aspect_ratio=increase,"
        f"crop={SIZE}:{SIZE},gblur=sigma=22,eq=brightness=-0.04:saturation=0.85[bg];"
        f"[0:v]scale={SIZE}:{SIZE}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,"
        f"zoompan=z='{z_expr}':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={SIZE}x{SIZE}:fps={FPS},"
        f"format=yuv420p[v]"
    )
    _run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(image),
            "-i",
            str(audio),
            "-filter_complex",
            vf,
            "-map",
            "[v]",
            "-map",
            "1:a",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-tune",
            "stillimage",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-t",
            f"{duration:.2f}",
            "-movflags",
            "+faststart",
            str(out),
        ]
    )


def _concat_and_mix(clips: list[Path], music: bytes, dest: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="enzo_narr_") as tmp:
        root = Path(tmp)
        lst = root / "list.txt"
        lst.write_text("\n".join(f"file '{p.as_posix()}'" for p in clips), encoding="utf-8")
        merged = root / "merged.mp4"
        _run(
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
            ]
        )
        bed = root / "bed.mp3"
        bed.write_bytes(music)
        final = root / "final.mp4"
        _run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(merged),
                "-stream_loop",
                "-1",
                "-i",
                str(bed),
                "-filter_complex",
                "[1:a]volume=0.14,afade=t=in:st=0:d=1.5[bed];"
                "[0:a]volume=1.0[vox];"
                "[vox][bed]amix=inputs=2:duration=first:dropout_transition=2[a]",
                "-map",
                "0:v",
                "-map",
                "[a]",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                "-movflags",
                "+faststart",
                str(final),
            ]
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(final, dest)


class GttsProvider:
    """Fallback PT-BR via Google gTTS (quando ElevenLabs/edge-tts falham)."""

    name = "gtts"

    async def synthesize(self, text: str, *, language: str = "pt-BR") -> bytes:
        from io import BytesIO

        try:
            from gtts import gTTS
        except ImportError as exc:
            raise TtsError("Pacote gTTS nao instalado", transient=False) from exc

        lang = "pt"
        if (language or "").lower().startswith("en"):
            lang = "en"
        elif (language or "").lower().startswith("es"):
            lang = "es"
        buf = BytesIO()
        gTTS((text or "").strip() or "...", lang=lang).write_to_fp(buf)
        data = buf.getvalue()
        if not data:
            raise TtsError("gTTS nao retornou audio", transient=True)
        return data


async def _pick_tts():
    for factory in (get_tts_provider, EdgeTtsProvider, GttsProvider):
        tts = factory()
        try:
            probe = await tts.synthesize("olá", language="pt-BR")
            if probe and len(probe) > 200:
                return tts
        except Exception as exc:
            print(
                f"TTS {getattr(tts, 'name', '?')} indisponível ({exc})",
                flush=True,
            )
    raise SystemExit("Nenhum provider TTS disponível (ElevenLabs/edge-tts/gTTS).")


async def _build() -> Path:
    tts = await _pick_tts()
    print(f"TTS provider: {getattr(tts, 'name', type(tts).__name__)}", flush=True)
    music = _ensure_music_bed(MUSIC_PATH)

    with tempfile.TemporaryDirectory(prefix="enzo_scenes_") as tmp:
        root = Path(tmp)
        clip_paths: list[Path] = []
        for i, (fname, text) in enumerate(PAGES):
            src = BOOK_DIR / fname
            if not src.is_file():
                raise FileNotFoundError(src)
            print(f"[{i + 1}/{len(PAGES)}] TTS {fname}", flush=True)
            audio_bytes = await tts.synthesize(text, language="pt-BR")
            aud = root / f"aud_{i:03d}.mp3"
            aud.write_bytes(audio_bytes)
            clip = root / f"clip_{i:03d}.mp4"
            print(f"[{i + 1}/{len(PAGES)}] scene {fname}", flush=True)
            _scene_clip(src, aud, clip, idx=i)
            clip_paths.append(clip)

        print(f"Montando {len(clip_paths)} cenas + trilha…", flush=True)
        _concat_and_mix(clip_paths, music, OUT_MP4)

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(OUT_MP4, ARTIFACT)
    print(f"OK: {OUT_MP4} ({OUT_MP4.stat().st_size} bytes)", flush=True)
    print(f"OK: {ARTIFACT}", flush=True)
    return OUT_MP4


if __name__ == "__main__":
    asyncio.run(_build())

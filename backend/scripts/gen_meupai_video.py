#!/usr/bin/env python3
"""Gera vídeo narrado do livro Meu Pai, Meu Herói a partir das páginas montadas.

Usa edge-tts (PT-BR) + Ken Burns (ffmpeg) via app.media.assemble.
Saída: apps/web/public/exemplos/video-meupai-heroi.mp4
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.media.assemble import SceneClip, assemble_narrated_video  # noqa: E402
from app.media.tts import EdgeTtsProvider  # noqa: E402

BOOK_DIR = ROOT.parent / "apps" / "web" / "public" / "exemplos" / "meupai-heroi"
OUT_MP4 = ROOT.parent / "apps" / "web" / "public" / "exemplos" / "video-meupai-heroi.mp4"
ARTIFACT = Path("/opt/cursor/artifacts/Meu-Pai-Meu-Heroi.mp4")

# Textos das páginas (transcritos das imagens do livro).
PAGES: list[tuple[str, str]] = [
    ("capa.png", "Meu pai, meu herói!"),
    (
        "pagina-02.jpg",
        "Para o papai que está sempre ao meu lado, com amor, carinho e um abraço apertado.",
    ),
    (
        "pagina-03.jpg",
        "Meu pai é meu herói, meu grande amigo, em cada aventura, está sempre comigo.",
    ),
    (
        "pagina-04.jpg",
        "No abraço do papai encontro proteção, um carinho gostoso que aquece o coração.",
    ),
    (
        "pagina-05.jpg",
        "Com papai, toda descoberta vira aprendizado, e cada momento se torna mais divertido.",
    ),
    (
        "pagina-06.jpg",
        "Com papai, toda brincadeira fica especial, corremos e sorrimos num dia sensacional.",
    ),
    (
        "pagina-07.jpg",
        "Se alguma coisa parece difícil para mim, papai me ajuda a tentar até o fim.",
    ),
    (
        "pagina-08.jpg",
        "Com muita paciência você me ensina, me explica com carinho e sempre me dá uma dica.",
    ),
    (
        "pagina-09.jpg",
        "Com papai, eu aprendo coisas novas, descubro meus talentos e ganho mais confiança.",
    ),
    (
        "pagina-10.jpg",
        "Você me incentiva a nunca desistir, e comemora comigo cada pequena conquista.",
    ),
    (
        "pagina-11.jpg",
        "Com seu amor, me sinto seguro, porque você sempre acredita em mim, hoje e no futuro.",
    ),
    (
        "pagina-12.jpg",
        "Eu te amo, papai! Obrigado por estar sempre ao meu lado. "
        "Você é o meu exemplo e o meu grande herói.",
    ),
    (
        "pagina-13.jpg",
        "Com você, eu aprendo, cresço e sou mais feliz. "
        "Você me ensina com carinho e sempre acredita em mim.",
    ),
    (
        "pagina-14.jpg",
        "Você me mostra um mundo incrível e sempre me guia para um futuro cheio de sonhos.",
    ),
    (
        "pagina-15.jpg",
        "Você me enche de alegria, papai, e eu sou muito grato por ter você sempre na minha vida.",
    ),
    (
        "pagina-16.jpg",
        "Eu te amo para sempre, papai! Você é o meu coração, a minha inspiração "
        "e a minha maior aventura.",
    ),
    (
        "contracapa.jpg",
        "Histórias personalizadas para momentos inesquecíveis. Story R Us.",
    ),
]


async def _build() -> Path:
    tts = EdgeTtsProvider()
    clips: list[SceneClip] = []
    for fname, text in PAGES:
        path = BOOK_DIR / fname
        if not path.is_file():
            raise FileNotFoundError(path)
        print(f"TTS: {fname}", flush=True)
        audio = await tts.synthesize(text, language="pt-BR")
        ext = path.suffix.lstrip(".") or "jpg"
        clips.append(
            SceneClip(image_bytes=path.read_bytes(), audio_bytes=audio, image_ext=ext)
        )

    print(f"Montando {len(clips)} cenas…", flush=True)
    # Formato quadrado do livro impresso (20×20).
    video = assemble_narrated_video(clips, music_bytes=None, width=1080, height=1080)
    OUT_MP4.parent.mkdir(parents=True, exist_ok=True)
    OUT_MP4.write_bytes(video)
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_bytes(video)
    print(f"OK: {OUT_MP4} ({len(video)} bytes)", flush=True)
    print(f"OK: {ARTIFACT}", flush=True)
    return OUT_MP4


if __name__ == "__main__":
    asyncio.run(_build())

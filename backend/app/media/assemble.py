"""Montagem de vídeo narrado com ffmpeg (Ken Burns + TTS + concat)."""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("media.assemble")


@dataclass
class SceneClip:
    image_bytes: bytes
    audio_bytes: bytes  # mp3
    image_ext: str = "png"


class AssembleError(Exception):
    pass


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssembleError(
            f"ffmpeg falhou ({proc.returncode}): {(proc.stderr or proc.stdout)[-800:]}"
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
        return max(1.0, float((proc.stdout or "5").strip()))
    except ValueError:
        return 5.0


def assemble_narrated_video(
    scenes: list[SceneClip],
    *,
    music_bytes: bytes | None = None,
    width: int = 1280,
    height: int = 720,
) -> bytes:
    """Gera MP4 a partir de cenas (imagem + áudio de narração)."""
    if not scenes:
        raise AssembleError("Nenhuma cena para montar")
    if not ffmpeg_available():
        raise AssembleError("ffmpeg nao encontrado no PATH")

    with tempfile.TemporaryDirectory(prefix="narrated_") as tmp:
        root = Path(tmp)
        clip_paths: list[Path] = []

        for i, scene in enumerate(scenes):
            img = root / f"img_{i:03d}.{scene.image_ext.lstrip('.')}"
            aud = root / f"aud_{i:03d}.mp3"
            clip = root / f"clip_{i:03d}.mp4"
            img.write_bytes(scene.image_bytes)
            aud.write_bytes(scene.audio_bytes)
            duration = _ffprobe_duration(aud) + 0.35
            # Ken Burns suave (zoom lento)
            vf = (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},"
                f"zoompan=z='min(zoom+0.0008,1.08)':d={max(25, int(duration * 25))}:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps=25,"
                f"format=yuv420p"
            )
            _run(
                [
                    "ffmpeg",
                    "-y",
                    "-loop",
                    "1",
                    "-i",
                    str(img),
                    "-i",
                    str(aud),
                    "-vf",
                    vf,
                    "-c:v",
                    "libx264",
                    "-tune",
                    "stillimage",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                    "-shortest",
                    "-t",
                    f"{duration:.2f}",
                    "-movflags",
                    "+faststart",
                    str(clip),
                ]
            )
            clip_paths.append(clip)

        concat_list = root / "concat.txt"
        concat_list.write_text(
            "\n".join(f"file '{p.as_posix()}'" for p in clip_paths), encoding="utf-8"
        )
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
                str(concat_list),
                "-c",
                "copy",
                str(merged),
            ]
        )

        final = root / "final.mp4"
        if music_bytes:
            music = root / "bed.mp3"
            music.write_bytes(music_bytes)
            # Mix: narração 100%, trilha ~18%
            _run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(merged),
                    "-stream_loop",
                    "-1",
                    "-i",
                    str(music),
                    "-filter_complex",
                    "[1:a]volume=0.18[bed];[0:a][bed]amix=inputs=2:duration=first:dropout_transition=2[a]",
                    "-map",
                    "0:v",
                    "-map",
                    "[a]",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(final),
                ]
            )
        else:
            shutil.copyfile(merged, final)

        return final.read_bytes()


def assemble_slideshow_gif(scenes: list[SceneClip], *, duration_per: float = 2.5) -> bytes:
    """Fallback sem ffmpeg: GIF a partir das imagens das cenas."""
    from io import BytesIO

    from PIL import Image

    if not scenes:
        raise AssembleError("Nenhuma cena para montar")
    frames: list[Image.Image] = []
    for scene in scenes:
        img = Image.open(BytesIO(scene.image_bytes)).convert("RGB")
        img = img.resize((960, 540), Image.Resampling.LANCZOS)
        frames.append(img)
    buf = BytesIO()
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=int(duration_per * 1000),
        loop=0,
        disposal=2,
    )
    return buf.getvalue()

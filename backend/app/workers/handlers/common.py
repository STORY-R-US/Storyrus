"""Shared helpers for worker job handlers."""

from __future__ import annotations

import logging
import re
from io import BytesIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import storage
from app.ai_clients.base import ProviderError
from app.ai_clients.face_detect import face_reference
from app.models import Asset, AssetKind, Job, Project, ProjectStatus
from app.services.usage_ledger import append_usage, image_provider_name, usage_line

logger = logging.getLogger("worker")


def _offline_png(
    label: str, *, palette: tuple[tuple[int, int, int], tuple[int, int, int]]
) -> bytes:
    """Gera uma imagem local simples para fallback offline/demonstração.

    O objetivo não é reproduzir a qualidade do provedor, apenas manter o fluxo
    funcional quando a IA externa estiver indisponivel.
    """
    from PIL import Image, ImageDraw, ImageFont

    width, height = 1024, 1024
    image = Image.new("RGB", (width, height), palette[0])
    draw = ImageDraw.Draw(image)

    # fundo com bloco suave e decoracoes simples
    draw.rounded_rectangle((64, 64, width - 64, height - 64), radius=48, fill=palette[1])
    draw.ellipse((120, 120, 420, 420), fill=(255, 255, 255))
    draw.ellipse((604, 120, 904, 420), fill=(255, 255, 255))
    draw.ellipse((260, 430, 764, 934), fill=(255, 255, 255))

    # personagem/ilustracao abstrata
    draw.ellipse((350, 260, 674, 584), fill=(246, 214, 170), outline=(80, 60, 50), width=6)
    draw.ellipse((410, 330, 470, 390), fill=(42, 42, 42))
    draw.ellipse((554, 330, 614, 390), fill=(42, 42, 42))
    draw.arc((460, 410, 564, 500), start=10, end=170, fill=(120, 60, 60), width=8)
    draw.rounded_rectangle((430, 600, 594, 820), radius=40, fill=(255, 232, 207))
    draw.line((430, 684, 360, 792), fill=(80, 60, 50), width=18)
    draw.line((594, 684, 664, 792), fill=(80, 60, 50), width=18)
    draw.line((470, 820, 430, 940), fill=(80, 60, 50), width=18)
    draw.line((554, 820, 594, 940), fill=(80, 60, 50), width=18)

    try:
        font = ImageFont.truetype("arial.ttf", 42)
    except Exception:
        font = ImageFont.load_default()
    draw.rounded_rectangle((168, 854, 856, 948), radius=28, fill=(255, 255, 255))
    draw.text((192, 874), label[:44], fill=(30, 30, 30), font=font)

    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _offline_gif(label: str) -> bytes:
    """Video fallback local em GIF animado para exibição no navegador."""
    from PIL import Image, ImageDraw, ImageFont

    frames = []
    colors = [
        ((221, 236, 255), (255, 250, 240)),
        ((255, 237, 222), (255, 248, 244)),
        ((234, 245, 228), (250, 250, 245)),
    ]
    try:
        font = ImageFont.truetype("arial.ttf", 38)
    except Exception:
        font = ImageFont.load_default()

    for idx, (bg, panel) in enumerate(colors):
        frame = Image.new("RGB", (960, 540), bg)
        draw = ImageDraw.Draw(frame)
        draw.rounded_rectangle((40, 40, 920, 500), radius=36, fill=panel)
        draw.ellipse((110 + idx * 30, 135, 350 + idx * 30, 375), fill=(246, 214, 170))
        draw.ellipse((210 + idx * 30, 230, 255 + idx * 30, 275), fill=(40, 40, 40))
        draw.ellipse((285 + idx * 30, 230, 330 + idx * 30, 275), fill=(40, 40, 40))
        draw.arc(
            (235 + idx * 30, 280, 305 + idx * 30, 345),
            start=15,
            end=165,
            fill=(120, 60, 60),
            width=6,
        )
        draw.rounded_rectangle(
            (530, 170, 840, 330), radius=28, fill=(255, 255, 255), outline=(170, 180, 190), width=4
        )
        draw.text((560, 205), label[:24], fill=(34, 42, 54), font=font)
        draw.text((560, 255), f"Cena {idx + 1}", fill=(84, 98, 112), font=font)
        frames.append(frame)

    buf = BytesIO()
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=700,
        loop=0,
        disposal=2,
    )
    return buf.getvalue()


def _offline_video_bytes(label: str) -> bytes:
    """Retorno de fallback para video offline.

    Mantem o fluxo funcionando sem depender de codificadores externos.
    O UI trata a URL assinada normal; aqui retornamos um pequeno placeholder
    textual em vez de um mp4 real quando o ambiente nao consegue gerar video.
    """
    return (
        f"Fallback offline do video indisponivel para: {label}\n"
        "Use o provedor configurado para gerar o mp4 real quando houver acesso.\n"
    ).encode()


def _project(db: Session, job: Job) -> Project:
    project = db.get(Project, job.project_id)
    if project is None:
        raise ProviderError("Projeto inexistente", transient=False)
    return project


def _set_status(db: Session, project: Project, status: ProjectStatus) -> None:
    project.status = status.value
    db.commit()


def _payload(job: Job) -> dict:
    return (job.result or {}).get("payload", {}) if job.result else {}


def _parse_title(story: str) -> str | None:
    """Extrai o título gerado pela IA (linha 'Título: ...' no começo da história)."""
    m = re.match(r"(?is)\s*t[íi]tulo\s*[:\-]\s*(.+?)\s*(?:\n|$)", story or "")
    if not m:
        return None
    title = m.group(1).strip().strip('"“”')
    return title[:120] or None


def _strip_title(story: str) -> str:
    """Remove a linha 'Título: ...' para que não vire página."""
    return re.sub(r"(?is)^\s*t[íi]tulo\s*[:\-].*?(?:\n+|$)", "", story or "", count=1)


def _parse_pages(story: str, limit: int = 200) -> list[str]:
    """Interpreta o texto enviado e divide em paginas para o e-book (sem limite fixo).

    Ordem:
      1) marcadores explicitos 'Pagina N:';
      2) paragrafos (linhas em branco) -> uma pagina por paragrafo;
      3) bloco unico -> agrupa ~2 frases por pagina.
    Usa TODA a historia (limite alto so como protecao). Cada item retornado e o
    TEXTO INTEGRAL daquele trecho (contexto completo para a ilustracao).
    """
    story = _strip_title((story or "").strip())
    # remove blocos de sugestao de imagem que a IA possa ter incluido,
    # ex.: "*(Imagem sugerida: ...)*" — nao devem virar pagina nem texto impresso
    story = re.sub(r"(?is)\*?\(\s*imagem[^)]*\)\*?", "", story).strip()
    if not story:
        return []

    # 1) marcadores "Pagina N:"
    parts = re.split(r"(?im)^\s*p[áa]gina\s*\d+\s*[:\-]", story)
    pages = [p.strip() for p in parts if p.strip()]

    # 2) paragrafos -> uma pagina por paragrafo
    if len(pages) <= 1:
        paras = [p.strip() for p in re.split(r"\n\s*\n", story) if p.strip()]
        if len(paras) > 1:
            pages = paras

    # 3) bloco unico -> agrupa ~2 frases por pagina (sem forcar numero fixo)
    if len(pages) <= 1 and len(story) > 220:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", story) if s.strip()]
        if len(sentences) > 1:
            group = 2
            pages = [" ".join(sentences[i : i + group]) for i in range(0, len(sentences), group)]

    return pages[:limit] or [story]


def _short_captions(pages: list[str]) -> list[str]:
    """Fallback local de resumo: 1a frase (ou trecho curto) de cada pagina."""
    out: list[str] = []
    for p in pages:
        p = (p or "").strip()
        first = re.split(r"(?<=[.!?])\s+", p)[0].strip() if p else ""
        if len(first) > 160:
            first = first[:157].rstrip() + "..."
        out.append(first or p[:120])
    return out


async def _project_photo_bytes(db: Session, project: Project) -> bytes | None:
    """Recorte do rosto da primeira foto do projeto, se existir.

    E a verdade do rosto em TODA pagina do livro, nao so no avatar: por isso usa
    a caixa detectada, e nao a janela geometrica que cortava a boca fora.
    """
    photos = db.scalars(
        select(Asset)
        .where(Asset.project_id == project.id, Asset.kind == AssetKind.PHOTO.value)
        .order_by(Asset.created_at.desc())
    ).all()
    if not photos:
        return None
    try:
        raw = storage.get_bytes(photos[0].storage_key)
    except Exception:  # noqa: BLE001
        return None
    return await face_reference(raw)


def _tag_image(result, *, action: str, label: str, fallback_provider: str | None = None):
    """Registra a chamada desta imagem em result.meta['usage_lines']."""
    if result is None:
        return result
    provider = image_provider_name(result, fallback_provider)
    append_usage(
        result,
        usage_line(
            action=action,
            label=label,
            cost_usd=result.cost_usd,
            provider=provider,
            meta={"model": (result.meta or {}).get("model")},
        ),
    )
    return result


def _ext(mime: str) -> str:
    return {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(mime, "png")

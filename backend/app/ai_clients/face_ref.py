"""Recorte de rosto para lock de identidade (foto inteira dilui a cara).

O recorte alimenta `REFINE_IDENTITY_PROMPT`, que manda o modelo copiar dali
"olhos, bochechas, boca e queixo". Se o recorte cortar a boca fora, o refino
recebe ordem de igualar features que nao existem na referencia e a identidade
DERIVA — foi o que acontecia com a janela geometrica fixa. Por isso a caixa vem
de deteccao (`face_detect`) e o heuristico aqui e so a rede de seguranca.

Este modulo e puro e offline: nao faz rede.
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw

# Folga em volta da caixa detectada: cabelo e queixo costumam encostar na borda.
BOX_PAD = 0.12
# Prompt do SAM: mais folga em cima para o cabelo fino entrar na silhueta.
SEGMENT_SIDE_PAD = 0.18
SEGMENT_TOP_PAD = 0.32
SEGMENT_BOTTOM_PAD = 0.16
# Mesmo cream do avatar: some com ombro/fundo que o retangulo ainda carrega.
CREAM = (245, 239, 229)


def _clamped_window(
    size: tuple[int, int], box: tuple[int, int, int, int], pad: float
) -> tuple[int, int, int, int]:
    w, h = size
    left, top, right, bottom = box
    left, top = max(0, min(left, w)), max(0, min(top, h))
    right, bottom = max(left + 1, min(right, w)), max(top + 1, min(bottom, h))
    dx, dy = int((right - left) * pad), int((bottom - top) * pad)
    return (max(0, left - dx), max(0, top - dy), min(w, right + dx), min(h, bottom + dy))


def crop_to_box(photo: bytes, box: tuple[int, int, int, int], *, pad: float = BOX_PAD) -> bytes:
    """Recorta a caixa (left, top, right, bottom) em pixels, com folga relativa.

    Nao forca formato quadrado: com o rosto na borda da foto, o quadrado sobra
    para o lado e traz de volta o cenario que o recorte deveria eliminar.
    """
    im = Image.open(BytesIO(photo)).convert("RGB")
    return _jpeg_bytes(im.crop(_clamped_window(im.size, box, pad)))


def isolate_on_cream(
    photo: bytes, box: tuple[int, int, int, int], *, pad: float = BOX_PAD
) -> bytes:
    """Recorte com oval do rosto sobre fundo creme.

    O retangulo ainda traz ombro, adulto e cenario; o oval + cream tira esse
    ruido do lock (PuLID e Gemini leem o fundo como se fosse a cara).
    """
    im = Image.open(BytesIO(photo)).convert("RGB")
    crop = im.crop(_clamped_window(im.size, box, pad))
    cw, ch = crop.size
    mask = Image.new("L", (cw, ch), 0)
    ix, iy = max(1, int(cw * 0.04)), max(1, int(ch * 0.04))
    ImageDraw.Draw(mask).ellipse((ix, iy, cw - 1 - ix, ch - 1 - iy), fill=255)
    cream = Image.new("RGB", (cw, ch), CREAM)
    cream.paste(crop, mask=mask)
    return _jpeg_bytes(cream)


def segment_prompt_box(
    size: tuple[int, int], box: tuple[int, int, int, int]
) -> tuple[int, int, int, int]:
    """Caixa do SAM: folga extra para cima (cabelo), laterais e queixo."""
    w, h = size
    left, top, right, bottom = box
    left, top = max(0, min(left, w)), max(0, min(top, h))
    right, bottom = max(left + 1, min(right, w)), max(top + 1, min(bottom, h))
    bw, bh = right - left, bottom - top
    return (
        max(0, left - int(bw * SEGMENT_SIDE_PAD)),
        max(0, top - int(bh * SEGMENT_TOP_PAD)),
        min(w, right + int(bw * SEGMENT_SIDE_PAD)),
        min(h, bottom + int(bh * SEGMENT_BOTTOM_PAD)),
    )


def composite_on_cream(
    photo: bytes,
    box: tuple[int, int, int, int],
    mask: bytes,
    *,
    pad: float = BOX_PAD,
) -> bytes:
    """Recorte no cream usando a mascara SAM (L ou alpha), alinhada a foto ou ao crop."""
    im = Image.open(BytesIO(photo)).convert("RGB")
    window = _clamped_window(im.size, box, pad)
    crop = im.crop(window)
    raw = Image.open(BytesIO(mask))
    if raw.mode in {"RGBA", "LA"}:
        alpha = raw.getchannel("A")
        if max(alpha.getextrema() or (0, 0)) > 0:
            mask_im = alpha
        else:
            mask_im = raw.convert("L")
    else:
        mask_im = raw.convert("L")
    if mask_im.size == im.size:
        mask_crop = mask_im.crop(window)
    elif mask_im.size == crop.size:
        mask_crop = mask_im
    else:
        mask_crop = mask_im.resize(crop.size, Image.Resampling.NEAREST)
    cream = Image.new("RGB", crop.size, CREAM)
    cream.paste(crop, mask=mask_crop)
    return _jpeg_bytes(cream)


def face_crop_bytes(photo: bytes) -> bytes:
    """Fallback geometrico: janela alta no terco superior-direito.

    NAO e um detector de face. A janela e generosa na vertical de proposito: a
    versao antiga usava 55% do menor lado e cortava a boca de fotos de crianca
    no colo. Preferir sempre `face_detect.face_reference`.
    """
    im = Image.open(BytesIO(photo)).convert("RGB")
    w, h = im.size
    if w < 32 or h < 32:
        return _jpeg_bytes(im)

    side = max(32, int(min(w, h) * 0.75))
    left = max(0, w - side - int(w * 0.04))
    top = max(0, int(h * 0.04))
    if left + side > w:
        left = max(0, w - side)
    if top + side > h:
        top = max(0, h - side)
    return _jpeg_bytes(im.crop((left, top, min(w, left + side), min(h, top + side))))


def try_face_crop(photo: bytes) -> bytes:
    """Recorte do rosto; se a imagem for invalida, devolve a foto original."""
    try:
        return face_crop_bytes(photo)
    except Exception:
        return photo


def identity_images(photo: bytes) -> list[bytes]:
    """[recorte do rosto, foto inteira] para generate_character."""
    crop = try_face_crop(photo)
    if crop is photo:
        return [photo]
    return [crop, photo]


def _jpeg_bytes(im: Image.Image) -> bytes:
    buf = BytesIO()
    im.save(buf, format="JPEG", quality=90)
    return buf.getvalue()

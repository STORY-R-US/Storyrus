"""Deterministic product views built from the book's actual finished artwork."""

import hashlib
import io

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _gradient(width, height, top, bottom):
    top = np.asarray(top, dtype=np.float32)
    bottom = np.asarray(bottom, dtype=np.float32)
    y = np.linspace(0, 1, height, dtype=np.float32)[:, None, None]
    pixels = top[None, None, :] * (1 - y) + bottom[None, None, :] * y
    x = np.linspace(-1, 1, width, dtype=np.float32)[None, :, None]
    center_light = np.clip(1 - (x * x + (y - 0.42) ** 2) * 0.06, 0.91, 1.0)
    pixels = pixels * center_light
    return Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))


def _shadow(size, polygon, *, blur, offset=(0, 0), opacity=90):
    width, height = size
    layer = Image.new("RGBA", size)
    shifted = [(round(x + offset[0]), round(y + offset[1])) for x, y in polygon]
    ImageDraw.Draw(layer).polygon(shifted, fill=(38, 31, 24, opacity))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def _warp(image, points, canvas_size, *, shade=1.0):
    source = np.asarray(Image.open(io.BytesIO(image)).convert("RGB"))
    height, width = source.shape[:2]
    target = np.asarray(points, dtype=np.float32)
    transform = cv2.getPerspectiveTransform(
        np.asarray(
            [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype=np.float32
        ),
        target,
    )
    warped = cv2.warpPerspective(
        source, transform, canvas_size, flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    mask = np.zeros((canvas_size[1], canvas_size[0]), dtype=np.uint8)
    cv2.fillConvexPoly(mask, np.round(target).astype(np.int32), 255, lineType=cv2.LINE_AA)
    if isinstance(shade, np.ndarray):
        warped = np.clip(warped.astype(np.float32) * shade[..., None], 0, 255).astype(np.uint8)
    elif shade != 1.0:
        warped = np.clip(warped.astype(np.float32) * shade, 0, 255).astype(np.uint8)
    return Image.fromarray(warped), Image.fromarray(mask)


def _shade_map(size, *, direction, strength=0.13):
    width, height = size
    x = np.linspace(0, 1, width, dtype=np.float32)[None, :]
    y = np.linspace(0, 1, height, dtype=np.float32)[:, None]
    if direction == "left":
        gutter = np.exp(-x * 24)
        outer = np.exp(-(1 - x) * 13)
    else:
        gutter = np.exp(-(1 - x) * 24)
        outer = np.exp(-x * 13)
    vertical = 0.99 + 0.015 * np.cos((y - 0.5) * np.pi)
    return np.clip((1 - strength * gutter + 0.025 * outer) * vertical, 0.78, 1.04)


def _reference_open_book(left, right, cover):
    """Use approved catalog geometry, replacing both example pages completely."""
    from pathlib import Path

    template = (
        Path(__file__).resolve().parents[1]
        / "assets/composition_examples/catalog/adventure-page.png"
    ).read_bytes()
    canvas = Image.open(io.BytesIO(template)).convert("RGB")
    if canvas.size != (1024, 1024):
        raise ValueError("Dimensões do modelo de livro aberto alteradas")
    # Keep the neutral outdoor product setting without the example's airplane.
    scenery = canvas.crop((512, 0, 1024, 248)).resize((1024, 248), Image.Resampling.LANCZOS)
    canvas.paste(scenery, (0, 0))
    edge_scenery = canvas.crop((1000, 248, 1024, 740)).resize((30, 492))
    canvas.paste(edge_scenery, (0, 248))
    binding = "catalog_hardback"
    if cover:
        with Image.open(io.BytesIO(cover)) as image:
            sample = np.asarray(image.convert("RGB").resize((64, 64)))
        edges = np.concatenate((sample[0], sample[-1], sample[:, 0], sample[:, -1]))
        binding = tuple(int(v) for v in np.median(edges, axis=0))
        band = np.zeros((1024, 1024), dtype=np.uint8)
        cv2.fillConvexPoly(band, np.asarray([(33, 252), (990, 250), (994, 736), (30, 737)]), 255)
        cv2.fillConvexPoly(band, np.asarray([(39, 255), (984, 254), (987, 730), (36, 731)]), 0)
        pixels = np.asarray(canvas).copy()
        pixels[band > 0] = binding
        canvas = Image.fromarray(pixels)
    surfaces = [
        [(49, 254), (511, 257), (511, 730), (49, 730)],
        [(512, 257), (978, 254), (979, 731), (512, 730)],
    ]
    # Shade the actual printed art only near the real central gutter.
    x = np.arange(1024, dtype=np.float32)[None, :]
    shade = np.broadcast_to(1 - 0.13 * np.exp(-abs(x - 511.5) / 8), (1024, 1024))
    for art, surface in zip((left, right), surfaces, strict=True):
        warped, mask = _warp(art, surface, (1024, 1024), shade=shade)
        canvas.paste(warped, (0, 0), mask)
    output = io.BytesIO()
    canvas.resize((2048, 2048), Image.Resampling.LANCZOS).save(output, format="PNG", optimize=True)
    return output.getvalue(), {
        "method": "deterministic_open_book_v2",
        "sources": [_digest(left), _digest(right)],
        "template_sha256": _digest(template),
        "dimensions": [2048, 2048],
        "surfaces": surfaces,
        "binding_color": binding,
    }


def open_book_spread(left, right, *, presentation=None, cover=None):
    """Render two exact square pages in the same fixed physical hardback shell."""
    for data in (left, right):
        with Image.open(io.BytesIO(data)) as image:
            if image.width != image.height:
                raise ValueError("As duas páginas precisam ser quadradas")

    if presentation == "meu_pai_heroi_v2":
        return _reference_open_book(left, right, cover)

    width, height = 1600, 800
    background = _gradient(width, height, (244, 240, 232), (220, 214, 202)).convert("RGBA")
    outer = [(91, 99), (1509, 99), (1525, 724), (75, 724)]
    background = Image.alpha_composite(
        background,
        _shadow((width, height), outer, blur=28, offset=(0, 20), opacity=95),
    )
    draw = ImageDraw.Draw(background)
    draw.polygon(outer, fill="#6b5846")
    page_stack = [(108, 108), (1492, 108), (1504, 704), (96, 704)]
    draw.polygon(page_stack, fill="#e5d9c4")
    left_page = [(118, 111), (790, 130), (790, 700), (118, 681)]
    right_page = [(810, 130), (1482, 111), (1482, 681), (810, 700)]
    draw.polygon(left_page, fill="#fffdf8")
    draw.polygon(right_page, fill="#fffdf8")
    draw.line([(118, 681), (790, 700)], fill="#cfc2aa", width=3)
    draw.line([(810, 700), (1482, 681)], fill="#cfc2aa", width=3)

    left_art = [(132, 124), (786, 143), (786, 686), (132, 667)]
    right_art = [(814, 143), (1468, 124), (1468, 667), (814, 686)]
    canvas = background.convert("RGB")
    for art, quad_points, direction in (
        (left, left_art, "left"),
        (right, right_art, "right"),
    ):
        warped, mask = _warp(
            art,
            quad_points,
            (width, height),
            shade=_shade_map((width, height), direction=direction),
        )
        canvas.paste(warped, (0, 0), mask)

    seam = Image.new("RGBA", (width, height))
    seam_draw = ImageDraw.Draw(seam)
    seam_draw.line([(800, 128), (800, 700)], fill=(54, 43, 33, 125), width=19)
    seam_draw.line([(789, 140), (789, 693)], fill=(255, 255, 255, 55), width=3)
    canvas = Image.alpha_composite(canvas.convert("RGBA"), seam.filter(ImageFilter.GaussianBlur(7)))
    canvas = canvas.convert("RGB").resize((2048, 1024), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    canvas.save(output, format="PNG", optimize=True)
    return output.getvalue(), {
        "method": "deterministic_open_book_v1",
        "sources": [_digest(left), _digest(right)],
        "dimensions": [2048, 1024],
        "surfaces": [left_art, right_art],
        "binding_color": "warm_neutral",
    }


def book_only(cover):
    """Render a hardback product view when the optional person-held image fails."""
    with Image.open(io.BytesIO(cover)) as image:
        if image.width != image.height:
            raise ValueError("A capa precisa ser quadrada")

    width = height = 1024
    canvas = _gradient(width, height, (248, 245, 238), (224, 218, 207)).convert("RGBA")
    board = [(232, 199), (744, 151), (792, 704), (280, 752)]
    canvas = Image.alpha_composite(
        canvas,
        _shadow((width, height), board, blur=26, offset=(0, 22), opacity=100),
    )
    draw = ImageDraw.Draw(canvas)
    draw.polygon([(248, 199), (744, 153), (784, 692), (284, 741)], fill="#695542")
    draw.polygon([(270, 199), (744, 155), (773, 675), (292, 724)], fill="#e7dac4")
    draw.polygon([(744, 155), (773, 175), (802, 695), (773, 675)], fill="#816d55")
    draw.polygon([(292, 724), (773, 675), (802, 695), (316, 748)], fill="#f4ebda")
    for offset in range(5):
        y0 = 727 + offset * 3
        draw.line([(300, y0), (790, y0 - 49)], fill="#d3c4aa", width=1)

    face = [(276, 185), (738, 142), (766, 658), (304, 701)]
    warped, mask = _warp(cover, face, (width, height), shade=0.96)
    canvas.paste(warped, (0, 0), mask)
    finish = Image.new("RGBA", (width, height))
    finish_draw = ImageDraw.Draw(finish)
    finish_draw.line([face[0], face[1], face[2]], fill=(255, 255, 255, 62), width=3)
    finish_draw.line([face[0], face[3]], fill=(38, 30, 23, 90), width=4)
    canvas = Image.alpha_composite(canvas, finish.filter(ImageFilter.GaussianBlur(1)))
    canvas = canvas.convert("RGB")
    output = io.BytesIO()
    canvas.save(output, format="PNG", optimize=True)
    return output.getvalue(), {
        "method": "deterministic_book_only_v1",
        "source": _digest(cover),
        "dimensions": [width, height],
        "surface": face,
        "presentation": "book_only_fallback",
    }

"""Flat editorial art, literal text and perspective mockups; no generative lettering."""

import hashlib
import io
import json
import math
import unicodedata
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.services import editorial_profile

TEXT_LAYOUT_REVISION = "2026-11-07.local-fit.1"


class TextLayoutError(ValueError):
    """An actionable local text issue; retrying an image provider cannot fix it."""


def _fit_copy(draw, value, font_path, preferred, minimum, width, height, line_height, stroke):
    for size in range(preferred, minimum - 1, -1):
        font = ImageFont.truetype(str(font_path), size)
        lines = []
        fits = True
        for paragraph in value.splitlines():
            line = ""
            for word in paragraph.split():
                if draw.textlength(word, font=font) + 2 * stroke > width:
                    fits = False
                    break
                candidate = f"{line} {word}".strip()
                if draw.textlength(candidate, font=font) + 2 * stroke > width:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
            if not fits:
                break
        step = max(1, round(size * line_height))
        ink_height = max(
            (font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines), default=0
        )
        if fits and (len(lines) - 1) * step + ink_height + 2 * stroke <= height:
            return font, lines, step
    raise TextLayoutError(
        "O texto não cabe mantendo uma leitura confortável. Encurte o título ou o trecho "
        "antes de tentar novamente; nenhuma nova imagem resolve esse limite."
    )


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(image):
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def square(data):
    image = Image.open(io.BytesIO(data)).convert("RGB")
    if image.width != image.height:
        raise ValueError("Arte plana deve ser quadrada; não recorte um mockup")
    return image


def validate_preview_copy(profile, locale):
    policy = editorial_profile.policy(profile)
    composition = policy.get("referenceComposition", {})
    design = profile.get("book_design")
    items = [("título", locale["title"], True)]
    if design and design["interior"]["mode"] != "two_scenes":
        items.append(("texto do livro aberto", locale["left"] + "\n\n" + locale["right"], False))
    else:
        items.extend(
            (label, locale[key], False)
            for key, label in (
                ("left", "texto da página esquerda"),
                ("right", "texto da página direita"),
            )
        )
    blank = encode(Image.new("RGB", (1024, 1024), "white"))
    for label, literal, title in items:
        try:
            text(
                blank,
                literal,
                profile,
                title=title,
                region=composition.get("coverRegion" if title else "bodyRegion"),
                measure_only=True,
                readable=not title,
            )
        except TextLayoutError as exc:
            raise TextLayoutError(f"Revise o {label}: {exc}") from exc


def text(
    data,
    value,
    profile,
    *,
    title=False,
    region=None,
    alignment=None,
    readable=False,
    measure_only=False,
):
    """Preserve literal copy and catalog position, fitting locally above readable limits."""
    image = square(data)
    if not isinstance(value, str) or not value.strip():
        raise TextLayoutError("Preencha o título ou o trecho antes de gerar a imagem.")
    policy = editorial_profile.policy(profile)
    typography = policy["typography"]
    filename = typography.get("titleFontFile" if title else "bodyFontFile", "Nunito-Medium.ttf")
    font_path = editorial_profile._root(profile["editorial"]["version"]) / "fonts" / filename
    manifest = json.loads((font_path.parent / "manifest.json").read_text(encoding="utf-8"))
    face = manifest.get("faces", {}).get(filename, manifest)
    if digest(font_path.read_bytes()) != face["sha256"]:
        raise ValueError("Fonte editorial alterada")
    normalized = unicodedata.normalize("NFC", value)
    if any(ord(char) not in face["codepoints"] for char in normalized if not char.isspace()):
        raise TextLayoutError("Retire do texto os símbolos que a fonte do livro não suporta.")
    width_ratio = typography.get(
        "titleWidthRatio" if title else "bodyWidthRatio", 0.055 if title else 0.032
    )
    if title and len(value) >= typography.get("longTitleMinCharacters", 100000):
        width_ratio = typography["longTitleWidthRatio"]
    preferred_size = max(1, round(image.width * width_ratio))
    bounds = region or policy.get("referenceComposition", {}).get(
        "coverRegion" if title else "bodyRegion",
        [0.09, 0.06, 0.91, 0.29] if title else [0.07, 0.07, 0.93, 0.29],
    )
    x0, y0, x1, y1 = validate_region(bounds)
    box = [round(v * image.width) for v in (x0, y0, x1, y1)]
    draw = ImageDraw.Draw(image)
    line_height = (
        typography.get("titleLineHeight", typography["lineHeight"])
        if title
        else typography["lineHeight"]
    )
    color = typography.get("titleColor", typography["color"]) if title else typography["color"]
    minimum_size = (
        min(preferred_size, max(1, round(image.width * (0.035 if title else 0.028))))
        if policy.get("referenceComposition")
        else preferred_size
    )
    stroke = max(1, round(image.width * 0.0012)) if readable else 0
    font, lines, step = _fit_copy(
        draw,
        normalized,
        font_path,
        preferred_size,
        minimum_size,
        box[2] - box[0],
        box[3] - box[1],
        line_height,
        stroke,
    )
    alignment = alignment or typography["coverAlignment" if title else "bodyAlignment"]
    if alignment not in {"left", "center"}:
        raise ValueError("Alinhamento editorial inválido")
    ink_boxes = []
    for i, line in enumerate(lines):
        offset = (
            (box[2] - box[0] - 2 * stroke - draw.textlength(line, font=font)) / 2
            if alignment == "center"
            else 0
        )
        position = (box[0] + stroke + offset, box[1] + stroke + i * step)
        if line:
            ink_boxes.append(
                draw.textbbox(position, line, font=font, anchor="lt", stroke_width=stroke)
            )
        draw.text(
            position,
            line,
            font=font,
            fill=color,
            anchor="lt",
            stroke_width=stroke,
            stroke_fill="#fff9ed" if readable else None,
        )
    padding = image.width * 0.012
    ink_region = [
        max(0, min(b[0] for b in ink_boxes) - padding) / image.width,
        max(0, min(b[1] for b in ink_boxes) - padding) / image.height,
        min(image.width, max(b[2] for b in ink_boxes) + padding) / image.width,
        min(image.height, max(b[3] for b in ink_boxes) + padding) / image.height,
    ]
    return (data if measure_only else encode(image)), {
        "text": value,
        "lines": lines,
        "region": bounds,
        "ink_region_with_margin": ink_region,
        "alignment": alignment,
        "font_sha256": digest(font_path.read_bytes()),
        "weight": face["weight"],
        "font_size": font.size,
        "preferred_font_size": preferred_size,
        "minimum_font_size": minimum_size,
        "fit_adjusted": font.size != preferred_size,
        "text_layout_revision": TEXT_LAYOUT_REVISION,
        "line_height": line_height,
        "color": color,
        "layout_version": profile["editorial"]["version"],
        "readability_outline": readable,
    }


@lru_cache(maxsize=1)
def _face_cascade():
    from pathlib import Path

    # OpenCV's filename loader mishandles accented Windows paths. Read the
    # packaged XML through Python and pass it in memory on every platform.
    xml = (Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml").read_text(
        encoding="utf-8"
    )
    document = cv2.FileStorage(xml, cv2.FILE_STORAGE_READ | cv2.FILE_STORAGE_MEMORY)
    detector = cv2.CascadeClassifier()
    detector.read(document.getFirstTopLevelNode())
    document.release()
    if detector.empty():
        raise ValueError("Detector local de áreas protegidas indisponível")
    return detector


def protected_heads(data):
    """Local face locations with generous room for hair/hats; no identity judgement."""
    image = square(data)
    side = min(768, image.width)
    small = np.array(image.resize((side, side)))
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    faces = _face_cascade().detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(max(24, side // 14),) * 2
    )
    return [
        [
            max(0, x - 0.25 * w) / side,
            max(0, y - 0.8 * h) / side,
            min(side, x + 1.25 * w) / side,
            min(side, y + 1.2 * h) / side,
        ]
        for x, y, w, h in faces
    ]


def choose_reading_region(data, value, profile, preferred, *, alignment="center"):
    """Move literal, fixed-size copy around detected heads instead of buying new art."""
    heads = protected_heads(data)
    if not heads:
        return preferred, {
            "method": "local_head_aware_layout",
            "protected_heads": [],
            "relocated": False,
            "unresolved_head_overlap": False,
        }
    image = square(data)
    gray = np.array(image.resize((256, 256)).convert("L"))
    candidates = [preferred, [0.06, 0.04, 0.94, 0.32]]
    for top in (0.05, 0.16, 0.35, 0.52):
        for left, right in (
            (0.05, 0.45),
            (0.55, 0.95),
            (0.05, 0.51),
            (0.49, 0.95),
            (0.05, 0.65),
            (0.35, 0.95),
        ):
            candidates.append([left, top, right, min(0.95, top + 0.62)])
    choices = []
    for index, region in enumerate(candidates):
        try:
            _, layout = text(
                data,
                value,
                profile,
                region=region,
                alignment=alignment,
                readable=True,
                measure_only=True,
            )
        except ValueError:
            continue
        x0, y0, x1, y1 = layout["ink_region_with_margin"]
        overlap = sum(
            max(0, min(x1, b[2]) - max(x0, b[0])) * max(0, min(y1, b[3]) - max(y0, b[1]))
            for b in heads
        )
        crop = gray[
            max(0, int(y0 * 256)) : max(1, int(y1 * 256)),
            max(0, int(x0 * 256)) : max(1, int(x1 * 256)),
        ]
        busy = float(crop.std()) / 255 if crop.size else 1
        score = overlap * 1000 + busy * 0.05 + y0 * 0.03 + (0 if index == 0 else 0.015)
        choices.append((score, overlap, region))
    if not choices:
        raise ValueError("Texto não cabe nas áreas de leitura disponíveis")
    _, overlap, region = min(choices, key=lambda item: item[0])
    return region, {
        "method": "local_head_aware_layout",
        "protected_heads": heads,
        "relocated": region != preferred,
        "unresolved_head_overlap": bool(overlap),
    }


def bound_cover(data):
    """Presentation-only hinge and board finish, derived from the actual cover colors."""
    art = np.array(square(data)).astype(np.float32)
    side = art.shape[1]
    spine = max(2, round(side * 0.026))
    x = np.linspace(0, 1, spine)
    curve = 0.70 + 0.34 * np.sin(x * math.pi)
    art[:, :spine] *= curve[None, :, None]
    groove = max(1, round(side * 0.002))
    art[:, spine : spine + groove] *= 0.64
    art[:, spine + groove : spine + 2 * groove] = np.minimum(
        255, art[:, spine + groove : spine + 2 * groove] * 1.08 + 6
    )
    # A fine board edge, rather than a large ivory band, leaves the art prominent.
    edge = max(1, round(side * 0.003))
    art[-edge:] *= 0.78
    return encode(Image.fromarray(np.clip(art, 0, 255).astype(np.uint8)))


def validate_region(region):
    if not isinstance(region, list) or len(region) != 4:
        raise ValueError("Região de texto ausente")
    if any(not isinstance(n, (float, int)) or not math.isfinite(n) for n in region):
        raise ValueError("Região de texto inválida")
    x0, y0, x1, y1 = region
    if not (0.04 <= x0 < x1 <= 0.96 and 0.04 <= y0 < y1 <= 0.96):
        raise ValueError("Região fora das margens seguras")
    return region


def front(data, *, profile=None):
    """Front-facing physical presentation; retain the separate flat cover for the PDF."""
    art = square(data)
    side = art.width
    if profile and editorial_profile.policy(profile).get("referenceComposition"):
        # A square printed face stays square; the separate spine sits beside it.
        face_size = side - round(side * 0.032)
        spine = max(8, round(side * 0.022))
        x, y = (side - face_size - spine) // 2, (side - face_size) // 2
        image = Image.new("RGB", (side, side), "#fff9ed")
        shadow = Image.new("RGBA", image.size)
        ImageDraw.Draw(shadow).rounded_rectangle(
            (x + 2, y + 4, x + spine + face_size + 2, y + face_size + 4),
            radius=side // 45,
            fill=(48, 35, 18, 65),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(max(2, side // 170)))
        image.paste(shadow, (0, 0), shadow)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(
            (x, y, x + spine + face_size, y + face_size), radius=side // 45, fill="#dfd1b8"
        )
        spine_art = art.crop((0, 0, max(2, round(side * 0.035)), side)).resize(
            (spine, face_size), Image.Resampling.LANCZOS
        )
        pixels = np.array(spine_art).astype(np.float32)
        roll = 0.62 + 0.40 * np.sin(np.linspace(0, math.pi, spine))
        pixels *= roll[None, :, None]
        image.paste(Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8)), (x, y))
        mask = Image.new("L", (face_size, face_size))
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, face_size - 1, face_size - 1), radius=side // 55, fill=255
        )
        image.paste(
            art.resize((face_size, face_size), Image.Resampling.LANCZOS), (x + spine, y), mask
        )
        groove = max(1, side // 500)
        crease = Image.new("RGBA", image.size)
        ImageDraw.Draw(crease).line(
            (x + spine, y + side // 55, x + spine, y + face_size - side // 55),
            fill=(15, 20, 25, 90),
            width=groove,
        )
        image = Image.alpha_composite(image.convert("RGBA"), crease).convert("RGB")
        return encode(image)
    image = Image.new("RGB", (side, side), "#fff7ec")
    inset = max(6, side // 35)
    art = art.resize((side - inset * 2, side - inset * 2), Image.Resampling.LANCZOS)
    mask = Image.new("L", art.size)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, art.width - 1, art.height - 1), radius=side // 40, fill=255
    )
    image.paste(art, (inset, inset), mask)
    return encode(image)


def quad(points):
    if not isinstance(points, list) or len(points) != 4:
        raise ValueError("Superfície do livro não identificada")
    result = np.asarray(points, dtype=np.float32)
    if (
        result.shape != (4, 2)
        or not np.isfinite(result).all()
        or (result < 0).any()
        or (result > 1).any()
    ):
        raise ValueError("Coordenadas de superfície inválidas")
    contour = result.reshape(-1, 1, 2)
    if not cv2.isContourConvex(contour) or cv2.contourArea(contour) < 0.035:
        raise ValueError("Superfície ilegível, pequena ou não convexa")
    # TL, TR, BR, BL: reject upside-down or mirrored placement.
    if (
        result[0, 0] >= result[1, 0]
        or result[3, 0] >= result[2, 0]
        or result[:2, 1].mean() >= result[2:, 1].mean()
    ):
        raise ValueError("Ordem dos cantos inválida")
    return result


def keyed_surfaces(data, count):
    """Measure marked print planes from pixels, rather than guessing vision coordinates."""
    original = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
    hsv = cv2.cvtColor(original, cv2.COLOR_RGB2HSV)
    h, w = hsv.shape[:2]
    ranges = [(135, 175), (75, 105)]  # magenta cover/left page, cyan right page
    surfaces, masks = [], []
    for low, high in ranges[:count]:
        # Near hands, low-saturation reflected color must not become print area.
        saturation_floor = 65 if count == 1 else 15
        mask = cv2.inRange(hsv, (low, saturation_floor, 35), (high, 255, 255))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            raise ValueError("Superfície de impressão não identificada pelos pixels")
        contour = max(contours, key=cv2.contourArea)
        hull = cv2.convexHull(contour)
        perimeter = cv2.arcLength(hull, True)
        corners = None
        for epsilon in (0.01, 0.015, 0.02, 0.03):
            polygon = cv2.approxPolyDP(hull, perimeter * epsilon, True).reshape(-1, 2)
            if len(polygon) == 4:
                corners = polygon.astype(np.float32)
                break
        if corners is None:
            raise ValueError("Página curva ou contorno de impressão não retangular")
        center = corners.mean(axis=0)
        corners = corners[
            np.argsort(np.arctan2(corners[:, 1] - center[1], corners[:, 0] - center[0]))
        ]
        corners = np.roll(corners, -np.argmin(corners.sum(axis=1)), axis=0)
        normalized = (corners / [w - 1, h - 1]).tolist()
        quad(normalized)
        plane = np.zeros((h, w), np.uint8)
        cv2.fillConvexPoly(plane, corners.astype(np.int32), 255)
        component = np.zeros((h, w), np.uint8)
        cv2.drawContours(component, [contour], -1, 255, cv2.FILLED)
        visible = cv2.bitwise_and(mask, component)
        radius = max(3, round(w * 0.004))
        near_plane = cv2.dilate(plane, np.ones((radius * 2 + 1, radius * 2 + 1), np.uint8))
        fringe = cv2.inRange(hsv, (low, 15, 35), (high, 255, 255))
        fringe = cv2.bitwise_and(fringe, near_plane)
        visible = cv2.bitwise_or(cv2.bitwise_and(visible, near_plane), fringe)
        coverage = np.count_nonzero(cv2.bitwise_and(visible, plane)) / max(
            1, np.count_nonzero(plane)
        )
        if coverage < 0.80:
            raise ValueError("Superfície excessivamente oculta ou marcação incompleta")
        surfaces.append(normalized)
        masks.append(visible)
    if count == 2 and np.mean(surfaces[0], axis=0)[0] >= np.mean(surfaces[1], axis=0)[0]:
        raise ValueError("Páginas marcadas em ordem incorreta")
    return {"valid": True, "issues": [], "surfaces": surfaces, "occlusions": []}, masks


def mockup(template, artworks, geometry, *, visible_masks=None, physical_book=False):
    """Project the actual finished art; restore explicit foreground occlusions unchanged."""
    if geometry.get("valid") is not True or geometry.get("issues") != []:
        raise ValueError("Geometria do mockup não foi aprovada")
    surfaces = geometry.get("surfaces")
    if not isinstance(surfaces, list) or len(surfaces) != len(artworks):
        raise ValueError("Quantidade de superfícies incorreta")
    if not isinstance(geometry.get("occlusions"), list):
        raise ValueError("Oclusões não avaliadas")
    original = np.array(Image.open(io.BytesIO(template)).convert("RGB"))
    output = original.copy()
    h, w = output.shape[:2]
    cover_masks = np.zeros((h, w), dtype=np.uint8)
    provenance = []
    for index, (raw, surface) in enumerate(zip(artworks, surfaces, strict=True)):
        art = np.array(square(bound_cover(raw) if physical_book and len(artworks) == 1 else raw))
        ah, aw = art.shape[:2]
        target = quad(surface) * np.array([w - 1, h - 1], dtype=np.float32)
        source = np.array([[0, 0], [aw - 1, 0], [aw - 1, ah - 1], [0, ah - 1]], dtype=np.float32)
        matrix = cv2.getPerspectiveTransform(source, target.astype(np.float32))
        warped = cv2.warpPerspective(
            art, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillConvexPoly(mask, np.round(target).astype(np.int32), 255)
        if visible_masks is not None:
            # Foreground hands and real page edges never carried the marking color.
            # Preserve those pixels without relying on generated occlusion polygons.
            # Include the measured curved paper edge outside the four-corner fit.
            # Replicate the artwork edge there; never leave registration-color strips.
            mask = visible_masks[index]
        # Neutral generated surface supplies only smooth illumination, never new cover content.
        light = cv2.GaussianBlur(
            cv2.cvtColor(original, cv2.COLOR_RGB2GRAY), (0, 0), max(2, w / 90)
        ).astype(np.float32)
        baseline = max(1, float(np.median(light[mask > 0])))
        shaded = np.clip(
            warped.astype(np.float32) * np.clip(light / baseline, 0.85, 1.1)[..., None], 0, 255
        ).astype(np.uint8)
        output[mask > 0] = shaded[mask > 0]
        cover_masks |= mask
        provenance.append(
            {"source_sha256": digest(raw), "quad": surface, "matrix": matrix.tolist()}
        )
    foreground = np.zeros((h, w), dtype=np.uint8)
    for polygon in geometry["occlusions"]:
        pts = np.asarray(polygon, dtype=np.float32)
        if (
            pts.ndim != 2
            or pts.shape[1] != 2
            or len(pts) < 3
            or not np.isfinite(pts).all()
            or (pts < 0).any()
            or (pts > 1).any()
        ):
            raise ValueError("Máscara de mãos inválida")
        cv2.fillPoly(foreground, [np.round(pts * [w - 1, h - 1]).astype(np.int32)], 255)
    if np.count_nonzero((foreground > 0) & (cover_masks > 0)) > np.count_nonzero(cover_masks) * 0.4:
        raise ValueError("Livro excessivamente oculto para conferir a capa")
    output[foreground > 0] = original[foreground > 0]
    return encode(Image.fromarray(output)), {
        "method": "keyed_perspective_composition"
        if visible_masks is not None
        else "perspective_composition",
        "surfaces": provenance,
        "occlusions": geometry["occlusions"],
        "binding_finish": "cover_derived_hinge" if physical_book and len(artworks) == 1 else None,
    }

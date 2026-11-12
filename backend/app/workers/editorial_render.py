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

TEXT_LAYOUT_REVISION = "2026-11-11.protected-lines.1"


class TextLayoutError(ValueError):
    """An actionable local text issue; retrying an image provider cannot fix it."""


@lru_cache(maxsize=32)
def _font(path, size):
    return ImageFont.truetype(str(path), size)


def _fit_copy(
    draw, value, font_path, preferred, minimum, width, height, line_height, stroke, balanced=False
):
    for size in range(preferred, minimum - 1, -1):
        font = _font(font_path, size)
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
        if balanced and len(value.splitlines()) == 1 and len(value.split()) > 1:
            words = value.split()
            pairs = [(" ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))]
            candidates = [
                pair
                for pair in pairs
                if all(draw.textlength(line, font=font) + 2 * stroke <= width for line in pair)
            ]
            if candidates:
                lines = list(
                    min(
                        candidates,
                        key=lambda pair: abs(
                            draw.textlength(pair[0], font=font)
                            - draw.textlength(pair[1], font=font)
                        ),
                    )
                )
        ink_height = max(
            (font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines), default=0
        )
        if fits and (len(lines) - 1) * step + ink_height + 2 * stroke <= height:
            return font, lines, step
    raise TextLayoutError(
        "BOOK_TEXT_INVALID: O texto não cabe mantendo uma leitura confortável. Encurte o título ou o trecho "
        "antes de tentar novamente; nenhuma nova imagem resolve esse limite."
    )


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(image):
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def square(data):
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.width != image.height:
                raise ValueError("Arte plana deve ser quadrada; não recorte um mockup")
            if image.width * image.height > 40_000_000 or image.format not in {
                "PNG",
                "JPEG",
                "WEBP",
            }:
                raise ValueError("Formato ou dimensões da arte inválidos")
            return image.convert("RGB")
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ValueError(f"BOOK_ART_INVALID: {exc}") from exc


def normalize_art(data):
    image = square(data)
    return data if data.startswith(b"\x89PNG\r\n\x1a\n") else encode(image)


def _luminance(rgb):
    values = np.asarray(rgb, dtype=np.float32) / 255
    linear = np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4)
    return linear @ np.array([0.2126, 0.7152, 0.0722])


def _readable_color(image, mask, preferred):
    from PIL import ImageColor

    pixels = np.asarray(image)[np.asarray(mask) > 0]
    if not pixels.size:
        return preferred, None
    background = _luminance(pixels)

    def contrast(color):
        ink = float(_luminance(ImageColor.getrgb(color)))
        ratios = (np.maximum(background, ink) + 0.05) / (np.minimum(background, ink) + 0.05)
        return float(np.quantile(ratios, 0.15))

    score = contrast(preferred)
    if score >= 3:
        return preferred, score
    alternatives = [(contrast(color), color) for color in (preferred, "#071337", "#fff9ed")]
    best, color = max(alternatives)
    return color, best


def validate_preview_copy(profile, locale):
    if not isinstance(locale, dict) or any(
        not isinstance(locale.get(key), str) or not locale[key].strip()
        for key in ("title", "left", "right")
    ):
        raise TextLayoutError("BOOK_TEXT_INVALID: preencha o título e os dois trechos da prévia.")
    policy = editorial_profile.policy(profile)
    composition = policy.get("referenceComposition", {})
    design = profile.get("book_design")
    if design and design["id"] == "family":
        from app.services import book_design

        design = {**design, "interior": book_design.preview_interior(design)}
        composition = {**composition, "bodyRegion": design["interior"]["region"]}
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
    if measure_only:
        # Font metrics need neither decoded full-page pixels nor a full-size canvas.
        with Image.open(io.BytesIO(data)) as image:
            if image.width != image.height:
                raise ValueError("Arte plana deve ser quadrada; não recorte um mockup")
    else:
        image = square(data)
    if not isinstance(value, str) or not value.strip():
        raise TextLayoutError(
            "BOOK_TEXT_INVALID: Preencha o título ou o trecho antes de gerar a imagem."
        )
    policy = editorial_profile.policy(profile)
    typography = policy["typography"]
    filename = typography.get("titleFontFile" if title else "bodyFontFile", "Nunito-Medium.ttf")
    font_path = editorial_profile._root(profile["editorial"]["version"]) / "fonts" / filename
    if typography.get("titleFontPackage" if title else "bodyFontPackage") == "catalog-v1":
        from app.services import book_design

        font_path = book_design.ROOT / "fonts/catalog-v1" / filename
    try:
        manifest = json.loads((font_path.parent / "manifest.json").read_text(encoding="utf-8"))
        font_bytes = font_path.read_bytes()
    except (OSError, ValueError) as exc:
        raise ValueError("BOOK_ART_UNAVAILABLE: fonte editorial indisponível") from exc
    face = manifest.get("faces", {}).get(filename, manifest)
    if digest(font_bytes) != face["sha256"]:
        raise ValueError("BOOK_ART_INVALID: Fonte editorial alterada")
    normalized = unicodedata.normalize("NFC", value)
    if any(ord(char) not in face["codepoints"] for char in normalized if not char.isspace()):
        raise TextLayoutError(
            "BOOK_TEXT_INVALID: Retire do texto os símbolos que a fonte do livro não suporta."
        )
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
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)) if measure_only else image)
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
    gold = title and typography.get("titleGoldOrnaments", False)
    font, lines, step = _fit_copy(
        draw,
        normalized,
        font_path,
        preferred_size,
        minimum_size,
        box[2] - box[0],
        box[3] - box[1] - (round(image.width * 0.03) if gold else 0),
        line_height,
        stroke,
        balanced=title and typography.get("titleBalancedLines") == 2,
    )
    alignment = alignment or typography["coverAlignment" if title else "bodyAlignment"]
    if alignment not in {"left", "center"}:
        raise ValueError("Alinhamento editorial inválido")
    ink_boxes = []
    positions = []
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
        positions.append((position, line))
    decorations = []
    if gold:
        radius = image.width * 0.013
        gap = image.width * 0.012
        for ink in list(ink_boxes):
            cy = (ink[1] + ink[3]) / 2
            for cx in (ink[0] - gap - radius, ink[2] + gap + radius):
                ornament_bounds = [cx - radius, cy - radius, cx + radius, cy + radius]
                if ornament_bounds[0] >= box[0] and ornament_bounds[2] <= box[2]:
                    points = [
                        (
                            cx
                            + math.cos(-math.pi / 2 + i * math.pi / 5)
                            * radius
                            * (1 if i % 2 == 0 else 0.45),
                            cy
                            + math.sin(-math.pi / 2 + i * math.pi / 5)
                            * radius
                            * (1 if i % 2 == 0 else 0.45),
                        )
                        for i in range(10)
                    ]
                    decorations.append(("star", points))
                    ink_boxes.append(ornament_bounds)
        bottom = max(b[3] for b in ink_boxes)
        cx = (box[0] + box[2]) / 2
        ornament_bounds = [
            cx - image.width * 0.14,
            bottom + gap,
            cx + image.width * 0.14,
            bottom + gap + image.width * 0.012,
        ]
        if ornament_bounds[3] <= box[3]:
            decorations.append(("arc", ornament_bounds))
            ink_boxes.append(ornament_bounds)
    preferred_color = color
    contrast = None
    if not measure_only:
        mask = Image.new("L", image.size)
        ink_draw = ImageDraw.Draw(mask)
        for position, line in positions:
            ink_draw.text(position, line, font=font, fill=255, anchor="lt", stroke_width=stroke)
        color, contrast = _readable_color(image, mask, color)
    for position, line in positions:
        draw.text(
            position,
            line,
            font=font,
            fill=color,
            anchor="lt",
            stroke_width=stroke,
            stroke_fill=("#071337" if color == "#fff9ed" else "#fff9ed") if readable else None,
        )
    for kind, points in decorations:
        if kind == "star":
            draw.polygon(points, fill="#F6BC43")
        else:
            draw.arc(points, 190, 350, fill="#F6BC43", width=max(1, round(image.width * 0.003)))
    padding = image.width * 0.012
    ink_region = [
        max(0, min(b[0] for b in ink_boxes) - padding) / image.width,
        max(0, min(b[1] for b in ink_boxes) - padding) / image.height,
        min(image.width, max(b[2] for b in ink_boxes) + padding) / image.width,
        min(image.height, max(b[3] for b in ink_boxes) + padding) / image.height,
    ]
    line_regions = [
        [
            max(0, b[0] - padding) / image.width,
            max(0, b[1] - padding) / image.height,
            min(image.width, b[2] + padding) / image.width,
            min(image.height, b[3] + padding) / image.height,
        ]
        for b in ink_boxes
    ]
    return (data if measure_only else encode(image)), {
        "text": value,
        "lines": lines,
        "gold_ornaments": len(decorations),
        "region": bounds,
        "ink_region_with_margin": ink_region,
        "ink_regions_with_margin": line_regions,
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
        "preferred_color": preferred_color,
        "contrast_adjusted": color != preferred_color,
        "ink_contrast_p15": contrast,
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


def title_area_evidence(data, layout):
    """Advisory face-box estimate; actual title clearance needs visual inspection."""
    x0, y0, x1, y1 = layout["ink_region_with_margin"]
    heads = protected_heads(data)
    possible_overlap = any(
        min(x1, box[2]) > max(x0, box[0]) and min(y1, box[3]) > max(y0, box[1]) for box in heads
    )
    return {
        "method": "approximate_local_head_boxes",
        "protected_heads": heads,
        "possible_overlap": possible_overlap,
        "authoritative": False,
    }


def protected_kind(value):
    """Canonicalize explicit equivalent labels, never infer an unknown region."""
    if not isinstance(value, str):
        return None
    return {
        "heads": "head",
        "faces": "face",
        "hairs": "hair",
        "hats": "hat",
        "accessories": "accessory",
        "hands": "hand",
        "bodies": "body",
        "actions": "action",
        "objects": "object",
    }.get(value, value)


def normalize_protected_regions(value):
    protected_regions(value)
    return [{**item, "kind": protected_kind(item["kind"])} for item in value]


def protected_regions(value):
    """Validate observed full-scene obstacles before using their geometry."""
    if not isinstance(value, list) or not 1 <= len(value) <= 64:
        raise TextLayoutError("Mapa de áreas protegidas ausente ou inválido.")
    boxes = []
    for item in value:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("kind"), str)
            or protected_kind(item.get("kind"))
            not in {
                "head",
                "face",
                "hair",
                "hat",
                "accessory",
                "hand",
                "body",
                "action",
                "object",
            }
        ):
            raise TextLayoutError("Área protegida sem identificação válida.")
        box = item.get("region")
        if (
            not isinstance(box, list)
            or len(box) != 4
            or any(type(n) not in (int, float) or not math.isfinite(n) for n in box)
            or not (0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1)
        ):
            raise TextLayoutError("Coordenadas de área protegida inválidas.")
        # Vision coordinates are approximate. Keep a conservative breathing margin.
        boxes.append(
            [
                max(0, box[0] - 0.02),
                max(0, box[1] - 0.02),
                min(1, box[2] + 0.02),
                min(1, box[3] + 0.02),
            ]
        )
    return boxes


def _intersection(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def layout_overlaps(layout, boxes):
    lines = layout.get("ink_regions_with_margin")
    if lines is None:
        lines = [layout.get("ink_region_with_margin")]
    if not isinstance(lines, list) or not lines:
        raise TextLayoutError("Regiões de texto ausentes ou inválidas.")
    for line in lines:
        validate_inspection_region(line)
    return any(_intersection(line, box) > 0 for line in lines for box in boxes)


def reading_region_candidates(
    data,
    value,
    profile,
    preferred,
    *,
    title=False,
    alignment="center",
    obstacles=None,
    suggested=None,
):
    """Bounded text-only repairs, ranked on the purchased scene without changing its pixels.

    Face boxes and texture only rank proposals. Mandatory crop/whole-image reviews
    still decide whether the text avoids hair, hands, objects and important action.
    """
    heads = protected_heads(data)
    gray = np.array(square(data).resize((256, 256)).convert("L"))
    regions = [preferred]
    if suggested is not None:
        regions.append(validate_region(suggested))
    # Keep covers in the upper part of the scene; interiors can use quiet scenery
    # beside the activity, as in the approved book references.
    # Search locally first; only the best safe candidates need a paid visual check.
    tops = (
        (0.055, 0.10, 0.16, 0.24, 0.34, 0.48, 0.62)
        if obstacles is not None
        else ((0.055, 0.10) if title else (0.055, 0.16, 0.35, 0.52))
    )
    for top in tops:
        for left, right in (
            (0.06, 0.94),
            (0.06, 0.44),
            (0.56, 0.94),
            (0.06, 0.51),
            (0.49, 0.94),
            (0.06, 0.65),
            (0.35, 0.94),
        ):
            regions.append([left, top, right, min(0.94, top + (0.34 if title else 0.40))])
    if obstacles is not None:
        # Derive actual free rectangles from obstacle edges. Fixed thirds alone
        # miss a narrow clear side of a face/hat, especially for longer titles.
        lanes = {(0.06, 0.94)}
        anchors = {0.055, *tops}
        for box in obstacles:
            if box[0] - 0.02 - 0.06 >= 0.18:
                lanes.add((0.06, box[0] - 0.02))
            if 0.94 - (box[2] + 0.02) >= 0.18:
                lanes.add((box[2] + 0.02, 0.94))
            if 0.055 <= box[3] + 0.02 < 0.85:
                anchors.add(box[3] + 0.02)
        for left, right in sorted(lanes)[:40]:
            for top in sorted(anchors)[:24]:
                relevant = [box for box in obstacles if min(right, box[2]) > max(left, box[0])]
                if any(box[1] <= top < box[3] for box in relevant):
                    continue
                bottom = min(
                    [0.94, top + 0.65, *[box[1] - 0.02 for box in relevant if box[1] > top]]
                )
                if bottom - top >= 0.10:
                    regions.append([left, top, right, bottom])
    choices = []
    top_cover = title and editorial_profile.policy(profile)["typography"].get("titleGoldOrnaments")
    if top_cover:
        regions.extend([[0.06, 0.045, 0.94, 0.29], [0.06, 0.075, 0.94, 0.32]])
    for index, region in enumerate(regions):
        if top_cover and (
            region[0] > 0.12 or region[2] < 0.88 or region[1] > 0.10 or region[3] > 0.36
        ):
            continue
        try:
            _, layout = text(
                data,
                value,
                profile,
                title=title,
                region=region,
                alignment=alignment,
                readable=not title,
                measure_only=True,
            )
        except TextLayoutError:
            continue
        ink = layout["ink_region_with_margin"]
        if obstacles is not None and layout_overlaps(layout, obstacles):
            continue
        x0, y0, x1, y1 = ink
        overlap = sum(
            max(0, min(x1, b[2]) - max(x0, b[0])) * max(0, min(y1, b[3]) - max(y0, b[1]))
            for b in heads
        )
        crop = gray[
            max(0, int(y0 * 256)) : max(1, int(y1 * 256)),
            max(0, int(x0 * 256)) : max(1, int(x1 * 256)),
        ]
        busy = float(crop.std()) / 255 if crop.size else 1
        # Larger readable titles and the catalog's upper placement take priority.
        score = (
            overlap * 1000
            + busy * 0.1
            + y0 * 0.3
            + (1 - layout["font_size"] / layout["preferred_font_size"]) * 0.15
        )
        choices.append((index, score, region, ink))
    if not choices:
        raise TextLayoutError("O texto não cabe nas áreas de leitura disponíveis.")
    # The catalog layout always gets its mandatory visual check, even when the
    # approximate face detector disagrees. Avoid spending reviews on near copies.
    ordered = (
        sorted(choices, key=lambda item: item[1])
        if obstacles is not None
        else [choices[0], *sorted(choices[1:], key=lambda item: item[1])]
    )
    selected = [ordered[0]]
    for choice in ordered[1:]:
        ink = choice[3]
        if any(_region_iou(ink, previous[3]) > 0.65 for previous in selected):
            continue
        selected.append(choice)
        if len(selected) == 3:
            break
    return [item[2] for item in selected]


def _region_iou(a, b):
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(
        0, min(a[3], b[3]) - max(a[1], b[1])
    )
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - intersection
    return intersection / union if union else 0


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


def validate_inspection_region(region):
    """Ink breathing margins can extend beyond the text container's safe margin."""
    if (
        not isinstance(region, list)
        or len(region) != 4
        or any(type(n) not in (int, float) or not math.isfinite(n) for n in region)
        or not (0 <= region[0] < region[2] <= 1 and 0 <= region[1] < region[3] <= 1)
    ):
        raise TextLayoutError("BOOK_LAYOUT_UNSAFE: região de inspeção inválida")
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


def keyed_folded_cover(data):
    """Separate two marked boards at an observed hinge, without any provider call.

    The upper concave corner and lower hinge tip identify a book opened toward
    its reader. Only the right board receives the front cover. The reverse and
    spine receive a neutral navy binding; unmarked hands remain pixel-identical.
    Return None for a single plane, never approximate a folded book by its hull.
    """
    original = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
    h, w = original.shape[:2]
    hsv = cv2.cvtColor(original, cv2.COLOR_RGB2HSV)
    marker = cv2.inRange(hsv, (135, 65, 35), (175, 255, 255))
    contours, _ = cv2.findContours(marker, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(contour) < h * w * 0.035:
        return None
    polygon = cv2.approxPolyDP(contour, cv2.arcLength(contour, True) * 0.01, True)
    points = polygon.reshape(-1, 2).astype(np.float32)
    lo, hi = points.min(axis=0), points.max(axis=0)
    span = hi - lo
    hinges = []
    for i, point in enumerate(points):
        before, after = points[i - 1], points[(i + 1) % len(points)]
        if (
            lo[0] + span[0] * 0.25 < point[0] < hi[0] - span[0] * 0.25
            and point[1] < lo[1] + span[1] * 0.4
            and min(point[1] - before[1], point[1] - after[1]) > span[1] * 0.07
            and min(before[0], after[0]) < point[0] < max(before[0], after[0])
        ):
            hinges.append((i, point))
    if not hinges:
        return None
    if len(hinges) != 1:
        raise ValueError("Lombada ambígua: montagem preservada para ajuste sem regeneração")
    i, top = hinges[0]
    direction = 1 if points[(i + 1) % len(points), 0] > top[0] else -1
    right = points[(i + direction) % len(points)]
    outer = points[(i + 2 * direction) % len(points)]
    bottom_index = int(np.argmax(points[:, 1]))
    bottom = points[bottom_index]
    lower = points[(bottom_index - direction) % len(points)]
    # Extrapolate only rigid board edges hidden behind the fingers. Their
    # observed segments must be long enough to constrain the missing corner.
    if (
        np.linalg.norm(outer - right) < span[1] * 0.2
        or lower[0] - bottom[0] < span[0] * 0.12
        or not lo[0] + span[0] * 0.25 < bottom[0] < hi[0] - span[0] * 0.25
    ):
        raise ValueError("Bordas da capa insuficientes para montar sem deformação")
    edge, base = outer - right, lower - bottom
    matrix = np.column_stack((edge, -base))
    if abs(np.linalg.det(matrix)) < 1:
        raise ValueError("Bordas da capa incompatíveis")
    distance = np.linalg.solve(matrix, bottom - right)[0]
    corner = right + distance * edge
    surface = np.array([top, right, corner, bottom]) / [w - 1, h - 1]
    quad(surface.tolist())
    if not 0.5 < distance < 4:
        raise ValueError("Perspectiva da capa não confirmada")
    component = np.zeros((h, w), np.uint8)
    cv2.drawContours(component, [contour], -1, 255, cv2.FILLED)
    neighborhood = cv2.dilate(component, np.ones((3, 3), np.uint8))
    visible = cv2.inRange(hsv, (135, 15, 35), (175, 255, 255)) & neighborhood
    yy, xx = np.indices((h, w))
    hinge_x = top[0] + (yy - top[1]) * (bottom[0] - top[0]) / (bottom[1] - top[1])
    front = visible.copy()
    front[xx < hinge_x] = 0
    back = (visible > 0) & (front == 0)
    # Retain the original illumination and hinge shadows, remove registration
    # hue on the reverse instead of duplicating/distorting the cover artwork.
    light = hsv[:, :, 2].astype(np.float32) / 255
    neutral = np.clip(light[..., None] * np.array([25, 48, 76]), 0, 255).astype(np.uint8)
    original[back] = neutral[back]
    return (
        encode(Image.fromarray(original)),
        {"valid": True, "issues": [], "surfaces": [surface.tolist()], "occlusions": []},
        [front],
    )


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


def validate_geometry(geometry, count):
    """Validate vision-proposed geometry before it can place customer artwork."""
    if count not in (1, 2):
        raise ValueError("Quantidade de superfícies inválida")
    if (
        not isinstance(geometry, dict)
        or geometry.get("valid") is not True
        or geometry.get("issues") != []
    ):
        raise ValueError("Superfícies do livro não foram identificadas com confiança")
    surfaces = geometry.get("surfaces")
    occlusions = geometry.get("occlusions")
    if not isinstance(surfaces, list) or len(surfaces) != count:
        raise ValueError("Quantidade de superfícies identificadas incorreta")
    if not isinstance(occlusions, list):
        raise ValueError("Oclusões do livro não foram avaliadas")

    normalized_surfaces = [quad(points).tolist() for points in surfaces]
    if (
        count == 2
        and np.mean(normalized_surfaces[0], axis=0)[0] >= np.mean(normalized_surfaces[1], axis=0)[0]
    ):
        raise ValueError("Páginas identificadas em ordem incorreta")

    normalized_occlusions = []
    for polygon in occlusions:
        points = np.asarray(polygon, dtype=np.float32)
        if (
            points.ndim != 2
            or points.shape[1] != 2
            or not 3 <= len(points) <= 128
            or not np.isfinite(points).all()
            or (points < 0).any()
            or (points > 1).any()
            or cv2.contourArea(points.reshape(-1, 1, 2)) < 0.00005
        ):
            raise ValueError("Máscara de oclusão inválida")
        normalized_occlusions.append(points.tolist())

    return {
        "valid": True,
        "issues": [],
        "surfaces": normalized_surfaces,
        "occlusions": normalized_occlusions,
    }


def mockup(
    template,
    artworks,
    geometry,
    *,
    visible_masks=None,
    physical_book=False,
    geometry_source=None,
):
    """Project the actual finished art; restore explicit foreground occlusions unchanged."""
    geometry = validate_geometry(geometry, len(artworks))
    surfaces = geometry["surfaces"]
    original = np.array(Image.open(io.BytesIO(template)).convert("RGB"))
    output = original.copy()
    h, w = output.shape[:2]
    cover_masks = np.zeros((h, w), dtype=np.uint8)
    provenance = []
    for index, (raw, surface) in enumerate(zip(artworks, surfaces, strict=True)):
        art = np.array(square(bound_cover(raw) if physical_book and len(artworks) == 1 else raw))
        ah, aw = art.shape[:2]
        target = quad(surface) * np.array([w - 1, h - 1], dtype=np.float32)
        if len(artworks) == 1:
            horizontal = np.linalg.norm(target[1] - target[0]) + np.linalg.norm(
                target[2] - target[3]
            )
            vertical = np.linalg.norm(target[3] - target[0]) + np.linalg.norm(target[2] - target[1])
            if horizontal / max(1, vertical) > 1.65:
                raise ValueError("Capa quadrada deformada: superfície atravessa as duas capas")
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
    # Check the original registration pixels, not arbitrary pink in the artwork.
    # A vision rectangle can be convex yet cover only a strip of the real book.
    if len(artworks) == 1:
        hsv = cv2.cvtColor(original, cv2.COLOR_RGB2HSV)
        marker = cv2.inRange(hsv, (135, 65, 35), (175, 255, 255))
        contours, _ = cv2.findContours(marker, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            component = np.zeros((h, w), np.uint8)
            cv2.drawContours(component, [max(contours, key=cv2.contourArea)], -1, 255, cv2.FILLED)
            marked = (marker > 0) & (component > 0)
            uncovered = marked & ((cover_masks == 0) | (foreground > 0))
            if np.count_nonzero(uncovered) > max(8, np.count_nonzero(marked) * 0.005):
                raise ValueError(
                    "Marcação rosa exposta: montagem não cobre toda a superfície do livro"
                )
    geometry_source = geometry_source or ("keyed_pixels" if visible_masks is not None else "manual")
    method = {
        "keyed_pixels": "keyed_perspective_composition",
        "vision": "vision_geometry_composition",
        "manual": "perspective_composition",
    }.get(geometry_source)
    if method is None:
        raise ValueError("Origem da geometria do mockup inválida")
    return encode(Image.fromarray(output)), {
        "method": method,
        "geometry_source": geometry_source,
        "surfaces": provenance,
        "occlusions": geometry["occlusions"],
        "binding_finish": "cover_derived_hinge" if physical_book and len(artworks) == 1 else None,
    }

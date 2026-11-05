"""Flat editorial art, literal text and perspective mockups; no generative lettering."""

import hashlib
import io
import json
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.services import editorial_profile


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


def text(data, value, profile, *, title=False, region=None, alignment=None):
    """Fixed, versioned sizes. Overflow fails rather than shrinking or changing words."""
    image = square(data)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Texto aprovado ausente")
    policy = editorial_profile.policy(profile)
    font_path = editorial_profile._root(profile["editorial"]["version"]) / "fonts/Nunito-Medium.ttf"
    manifest = json.loads((font_path.parent / "manifest.json").read_text(encoding="utf-8"))
    if digest(font_path.read_bytes()) != manifest["sha256"]:
        raise ValueError("Fonte editorial alterada")
    if any(ord(char) not in manifest["codepoints"] for char in value if not char.isspace()):
        raise ValueError("Fonte não contém todos os caracteres do texto aprovado")
    font = ImageFont.truetype(
        str(font_path), max(1, round(image.width * (0.055 if title else 0.032)))
    )
    bounds = region or ([0.09, 0.06, 0.91, 0.29] if title else [0.07, 0.07, 0.93, 0.29])
    x0, y0, x1, y1 = validate_region(bounds)
    box = [round(v * image.width) for v in (x0, y0, x1, y1)]
    draw = ImageDraw.Draw(image)
    lines = []
    for paragraph in value.splitlines():
        line = ""
        for word in paragraph.split():
            candidate = f"{line} {word}".strip()
            if draw.textlength(candidate, font=font) > box[2] - box[0]:
                if not line or draw.textlength(word, font=font) > box[2] - box[0]:
                    raise ValueError("Palavra não cabe; recomponha a área de leitura")
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    step = round(font.size * policy["typography"]["lineHeight"])
    ink_height = font.getbbox("ÁgjÇ")[3] - font.getbbox("ÁgjÇ")[1]
    if (len(lines) - 1) * step + ink_height > box[3] - box[1]:
        raise ValueError("Texto não cabe; recomponha a cena sem reduzir a fonte")
    alignment = alignment or ("center" if title else "left")
    if alignment not in {"left", "center"}:
        raise ValueError("Alinhamento editorial inválido")
    ink_boxes = []
    for i, line in enumerate(lines):
        offset = (
            (box[2] - box[0] - draw.textlength(line, font=font)) / 2 if alignment == "center" else 0
        )
        position = (box[0] + offset, box[1] + i * step)
        if line:
            ink_boxes.append(draw.textbbox(position, line, font=font, anchor="lt"))
        draw.text(
            position,
            line,
            font=font,
            fill=policy["typography"]["color"],
            anchor="lt",
        )
    padding = image.width * 0.012
    ink_region = [
        max(0, min(b[0] for b in ink_boxes) - padding) / image.width,
        max(0, min(b[1] for b in ink_boxes) - padding) / image.height,
        min(image.width, max(b[2] for b in ink_boxes) + padding) / image.width,
        min(image.height, max(b[3] for b in ink_boxes) + padding) / image.height,
    ]
    return encode(image), {
        "text": value,
        "lines": lines,
        "region": bounds,
        "ink_region_with_margin": ink_region,
        "alignment": alignment,
        "font_sha256": digest(font_path.read_bytes()),
        "weight": 500,
        "font_size": font.size,
        "line_height": 1.2,
        "color": "#172A3A",
        "layout_version": "2026-11-05.1",
    }


def validate_region(region):
    if not isinstance(region, list) or len(region) != 4:
        raise ValueError("Região de texto ausente")
    if any(not isinstance(n, (float, int)) or not math.isfinite(n) for n in region):
        raise ValueError("Região de texto inválida")
    x0, y0, x1, y1 = region
    if not (0.04 <= x0 < x1 <= 0.96 and 0.04 <= y0 < y1 <= 0.96):
        raise ValueError("Região fora das margens seguras")
    return region


def front(data):
    """Front-facing physical presentation; retain the separate flat cover for the PDF."""
    art = square(data)
    side = art.width
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


def mockup(template, artworks, geometry, *, visible_masks=None):
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
        art = np.array(square(raw))
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
    }

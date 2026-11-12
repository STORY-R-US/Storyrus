"""Optional, deterministic scenery accents. No providers, resizing or face edits."""

import hashlib
import io
import re
import unicodedata

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFilter

VERSION = "local-football-1"


def football_theme(value):
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return bool(re.search(r"\b(futebol|football|soccer|goleiro|goalkeeper)\b", value))


def _regions(values):
    result = []
    for value in values:
        box = np.asarray(value, dtype=float)
        if (
            box.shape != (4,)
            or not np.isfinite(box).all()
            or not (0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1)
        ):
            raise ValueError("Invalid protected scenery region")
        result.append(box.tolist())
    return result


def _clear(box, protected, margin=0.012):
    return all(
        box[2] + margin <= p[0]
        or box[0] - margin >= p[2]
        or box[3] + margin <= p[1]
        or box[1] - margin >= p[3]
        for p in protected
    )


def _encode(image):
    stream = io.BytesIO()
    image.save(stream, "PNG")
    return stream.getvalue()


def enrich(data, *, theme, protected, text_regions=(), horizon=None, accent=None):
    """Add whole props only in clear background, never clip them around a face.

    A complete observed protection map is required by the caller. Unknown themes
    or missing maps remain untouched. A horizon may be supplied for reviewed
    saved art; otherwise estimate the distant green field from image pixels.
    """
    report = {
        "version": VERSION,
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "added": [],
        "provider_calls": 0,
    }
    if not football_theme(theme) or not protected:
        return data, {**report, "reason": "unsupported_theme_or_missing_protection"}
    try:
        flag_color = ImageColor.getrgb(
            "#186742" if "palmeiras" in str(theme).lower() else accent or "#284e77"
        )[:3]
    except (ValueError, TypeError):
        flag_color = (40, 78, 119)
    boxes = _regions([*protected, *text_regions])
    image = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = image.size
    rgb = np.array(image).astype(float)
    if horizon is None:
        green = (rgb[:, :, 1] > rgb[:, :, 0] * 1.04) & (rgb[:, :, 1] > rgb[:, :, 2] * 1.05)
        rows = np.flatnonzero((green.mean(axis=1) > 0.60) & (np.arange(h) > h * 0.45))
        if not len(rows):
            return data, {**report, "reason": "field_not_identified"}
        horizon = float(rows[0] / h)
    if not 0.40 <= horizon <= 0.80:
        return data, {**report, "reason": "unsupported_horizon"}
    layer = Image.new("RGBA", image.size)
    draw = ImageDraw.Draw(layer)

    def xy(x, y):
        return (round(x * w), round(y * h))

    def line(points, fill, width=1):
        draw.line([xy(*p) for p in points], fill=fill, width=max(1, round(width * w / 1024)))

    def accept(kind, box):
        if min(box) < 0 or max(box) > 1:
            return False
        if not _clear(box, boxes):
            return False
        # Do not put stadium towers in a roof, person or field: require blue sky
        # at the top. The protection map alone cannot identify a background type.
        if kind == "floodlight":
            x0, y0, x1, y1 = box
            patch = rgb[round(y0 * h) : round((y0 + 0.04) * h), round(x0 * w) : round(x1 * w)]
            if not patch.size or np.mean(patch[:, :, 2] > patch[:, :, 0] * 1.04) < 0.65:
                return False
        report["added"].append({"kind": kind, "region": box})
        return True

    for x in (0.10, 0.89):
        top, bottom = horizon - 0.26, horizon - 0.015
        box = [x - 0.055, top - 0.008, x + 0.055, bottom + 0.008]
        if not accept("floodlight", box):
            top = horizon - 0.16
            box = [x - 0.055, top - 0.008, x + 0.055, bottom + 0.008]
            if not accept("floodlight", box):
                continue
        line([(x - 0.006, top + 0.025), (x - 0.009, bottom)], (87, 107, 111, 230), 4)
        line([(x + 0.006, top + 0.025), (x + 0.009, bottom)], (186, 196, 186, 235), 3)
        for y in np.linspace(top + 0.04, bottom - 0.02, 7):
            line([(x - 0.007, y), (x + 0.007, y + 0.025)], (125, 145, 142, 210), 1)
        draw.rounded_rectangle(
            (*xy(x - 0.05, top), *xy(x + 0.05, top + 0.029)),
            radius=max(1, w // 700),
            fill=(102, 119, 124, 240),
        )
        for dx in (-0.038, -0.019, 0, 0.019, 0.038):
            for dy in (0.009, 0.021):
                draw.ellipse(
                    (*xy(x + dx - 0.006, top + dy - 0.005), *xy(x + dx + 0.006, top + dy + 0.005)),
                    fill=(51, 66, 70, 245),
                )
                draw.ellipse(
                    (*xy(x + dx - 0.004, top + dy - 0.003), *xy(x + dx + 0.004, top + dy + 0.003)),
                    fill=(205, 216, 204, 245),
                )
                draw.ellipse(
                    (*xy(x + dx - 0.003, top + dy - 0.003), *xy(x + dx, top + dy)),
                    fill=(248, 245, 224, 220),
                )

    for x, lift in ((0.17, 0.10), (0.76, 0.09), (0.94, 0.105)):
        top, bottom = horizon - lift, horizon + 0.015
        box = [x - 0.005, top - 0.005, min(0.99, x + 0.05), bottom + 0.005]
        if not accept("supporter_flag", box):
            continue
        line([(x, top), (x, bottom)], (208, 210, 193, 235), 2)
        shape = [
            (x, top),
            (x + 0.018, top + 0.003),
            (x + 0.045, top - 0.002),
            (x + 0.041, top + 0.029),
            (x + 0.018, top + 0.035),
            (x, top + 0.030),
        ]
        draw.polygon([xy(*p) for p in shape], fill=(*flag_color, 235))
        line(
            [(x + 0.003, top + 0.013), (x + 0.020, top + 0.018), (x + 0.041, top + 0.013)],
            (238, 231, 192, 230),
            3,
        )

    for x, y, scale in ((0.86, 0.88, 0.017), (0.93, 0.95, 0.023)):
        box = [x - scale * 1.6, y - scale * 2.2, x + scale * 2.5, min(0.995, y + scale * 0.55)]
        if not accept("training_cone", box):
            continue
        draw.ellipse(
            (*xy(x - scale, y - scale * 0.15), *xy(x + scale * 2.4, y + scale * 0.45)),
            fill=(30, 48, 29, 65),
        )
        # A shaded cone surface, not a flat triangular icon. Cross-sections
        # follow perspective and preserve the scene's upper-left illumination.
        px, py = xy(x, y)
        radius = max(3, round(scale * w))
        height = max(6, round(scale * 2 * h))
        for row in range(height):
            t = (row + 1) / height
            half = max(1, round(radius * t))
            for column in range(-half, half + 1):
                normal = column / half
                light = 0.66 + 0.26 * (1 - normal * normal) ** 0.5 - 0.10 * normal
                color = (
                    np.array([226, 129, 47]) if not 0.45 < t < 0.56 else np.array([241, 229, 201])
                )
                draw.point(
                    (px + column, py - height + row),
                    fill=(*np.clip(color * light, 0, 255).astype(int).tolist(), 245),
                )
        draw.ellipse(
            (*xy(x - scale * 1.2, y - scale * 0.13), *xy(x + scale * 1.2, y + scale * 0.20)),
            fill=(193, 94, 27, 240),
        )
    if not report["added"]:
        return data, {**report, "reason": "no_safe_background_space"}
    # No resampling of the source. Entire protected boxes must be bit-identical.
    layer = layer.filter(ImageFilter.GaussianBlur(max(0.45, w / 1800)))
    result = Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")
    for box in boxes:
        crop = tuple(round(v * (w if i % 2 == 0 else h)) for i, v in enumerate(box))
        if result.crop(crop).tobytes() != image.crop(crop).tobytes():
            raise ValueError("Scenery overlay touched a protected region")
    return _encode(result), {**report, "protected_pixels_identical": True, "horizon": horizon}


def framed_scene(data, artwork, *, region, protected):
    """Place saved scenery in a deliberately selected, clear indoor wall area."""
    region = _regions([region])[0]
    if not _clear(region, _regions(protected), margin=0.025):
        raise ValueError("Wall decoration overlaps protected content")
    image = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = image.size
    x0, y0, x1, y1 = [round(v * (w if i % 2 == 0 else h)) for i, v in enumerate(region)]
    panel = Image.open(io.BytesIO(artwork)).convert("RGB")
    # Contain, never stretch or crop a saved picture.
    from PIL import ImageOps

    mat = Image.new("RGB", (x1 - x0, y1 - y0), "#c4baa0")
    fit = ImageOps.contain(panel, (mat.width - 16, mat.height - 16))
    mat.paste(fit, ((mat.width - fit.width) // 2, (mat.height - fit.height) // 2))
    draw = ImageDraw.Draw(mat)
    draw.rectangle((0, 0, mat.width - 1, mat.height - 1), outline="#514638", width=5)
    draw.line((2, 2, mat.width - 3, 2), fill="#a09172", width=2)
    draw.line((2, 2, 2, mat.height - 3), fill="#897b61", width=2)
    # The frame is in the existing softly focused background, not on the
    # subject's focal plane. Match that depth rather than pasting a sharp tile.
    mat = mat.filter(ImageFilter.GaussianBlur(max(1.2, w / 650)))
    image.paste(mat, (x0, y0))
    return _encode(image)

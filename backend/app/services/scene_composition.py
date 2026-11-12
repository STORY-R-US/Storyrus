"""Local composition diagrams: camera/layout references, never finished artwork."""

import io
import json

from PIL import Image, ImageDraw


def cover_guide(region, *, alignment):
    """Reserve actual lettering and show a smaller subject without editing the photo."""
    left, top, right, bottom = region
    if alignment not in {"left", "center", "right"} or not (
        0 <= left < right <= 1 and 0 <= top < bottom <= 0.5
    ):
        raise ValueError("Invalid upper cover title reserve")
    # A side title belongs beside the cast; a full-width title belongs above it.
    side = left >= 0.4
    diameter = min(0.22, max(0.12, left - 0.12)) if side else 0.22
    head_left = 0.08 if side else 0.5 - diameter / 2
    head_top = max(0.12, top) if side else max(0.40, bottom + 0.08)
    head = [head_left, head_top, head_left + diameter, head_top + diameter]
    image = Image.new("RGB", (1024, 1024), "#dce7eb")
    draw = ImageDraw.Draw(image)

    def pixels(box):
        return tuple(round(v * 1024) for v in box)

    draw.rectangle(pixels(region), fill="#f6d96b")
    # Deliberately abstract: no identity, example scenery, clothing or text to copy.
    draw.ellipse(pixels(head), fill="#627483")
    draw.rounded_rectangle(
        pixels([max(0.04, head_left - 0.04), head[3] + 0.02, min(0.96, head[2] + 0.04), 0.96]),
        radius=36,
        fill="#627483",
    )
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue(), {
        "title_region": list(region),
        "head_envelope": head,
        "reference_role": "composition_diagram_only",
    }


def direction(geometry, *, reference_number):
    return (
        f"\nCOMPOSITION DIAGRAM: attached image {reference_number} is an abstract camera "
        "and spacing guide, NOT artwork, a character, a palette or a background to reproduce. "
        "The yellow area means continuous natural scenery reserved for the server's large "
        "title and ornaments; the grey silhouette shows the maximum head scale and placement. "
        "Include ALL hair, hats and accessories inside that head envelope. Original photos "
        "define facial identity, age and natural anatomy ONLY: never copy their portrait crop, "
        "pose, background or clothing unless explicitly requested in the story wardrobe. "
        "Create the entire scene anew around the requested theme, with a coherent foreground, "
        "middle ground and distant background, detailed relevant materials, light and objects. "
        "Show the protagonist participating in the story's activity, not posing for a portrait. "
        "The diagram does not define cast count: include all and only the explicitly requested "
        "companions, with their complete heads outside the title reserve too. "
        "Keep the selected catalog finish. The title reserve must be the SAME continuous "
        "environment as the rest of the scene: no yellow patch, grey silhouette, border, "
        "separate header, blank band, blur, repeated edge strips or lettering in the output. "
        "Move the camera and stage the action to fit; do not enlarge the head. "
        + json.dumps(geometry)
    )


def expansion_canvas(data, title_bottom, head_height, protected=()):
    """Uniformly reduce saved art; transparent surroundings are the ONLY new scene."""
    source = Image.open(io.BytesIO(data)).convert("RGBA")
    if source.width != source.height or not 0 < head_height <= 1:
        raise ValueError("Invalid source geometry")
    size = source.width
    scale = min(0.64, 1 - title_bottom - 0.08, 0.24 / head_height)
    if not 0.20 <= scale <= 0.64:
        raise ValueError("Insufficient room for natural scene expansion")
    side = round(size * scale)
    left, top = (size - side) // 2, size - side
    seed = Image.new("RGBA", source.size)
    seed.paste(source.resize((side, side), Image.Resampling.LANCZOS), (left, top))
    # A narrow transition at the scenery edges; the face/body core stays exact.
    alpha = Image.new("L", source.size)
    draw = ImageDraw.Draw(alpha)
    feather = max(1, round(size * 0.012))
    for offset in range(feather + 1):
        draw.rectangle(
            (left + offset, top + offset, left + side - 1 - offset, size - 1),
            fill=round(255 * offset / feather),
        )
    for box in protected:
        draw.rectangle(
            (
                left + round(box[0] * side),
                top + round(box[1] * side),
                min(size - 1, left + round(box[2] * side)),
                min(size - 1, top + round(box[3] * side)),
            ),
            fill=255,
        )
    mask = Image.new("RGBA", source.size, (0, 0, 0, 0))
    mask.putalpha(alpha)

    def encode(image):
        buffer = io.BytesIO()
        image.save(buffer, "PNG")
        return buffer.getvalue()

    return (
        encode(seed),
        encode(mask),
        {"scale": side / size, "left": left, "top": top, "side": side},
    )


def validate_expansion_output(output, seed, mask):
    """Keep the continuous provider output for mandatory identity/scene review.

    A mask is guidance, not a guarantee of fixed pixel coordinates. Pasting the
    seed rectangle back can duplicate a person or break scenery that moved.
    """
    result = Image.open(io.BytesIO(output)).convert("RGB")
    original = Image.open(io.BytesIO(seed)).convert("RGB")
    alpha = Image.open(io.BytesIO(mask)).getchannel("A")
    if result.size != original.size or alpha.size != result.size:
        raise ValueError("Expanded scene dimensions changed")
    buffer = io.BytesIO()
    result.save(buffer, "PNG")
    return buffer.getvalue()

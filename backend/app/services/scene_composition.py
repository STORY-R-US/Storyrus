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

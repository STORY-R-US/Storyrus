"""Rebuild display bounds without changing source artwork (requires Pillow)."""
import json
from pathlib import Path

from PIL import Image

web = Path(__file__).resolve().parents[1]
root = web / "public" / "exemplos"
bounds = {}
for path in sorted(root.rglob("*")):
    if not path.is_file() or "capa-" not in path.name or path.suffix.lower() not in {".png", ".webp", ".jpg", ".jpeg"}:
        continue
    with Image.open(path) as image:
        if "A" not in image.getbands():
            continue
        width, height = image.size
        alpha = image.getchannel("A")
        # Ignore isolated shadow pixels; retain the rectangular cover face.
        columns = [x for x in range(width) if sum(alpha.crop((x, 0, x + 1, height)).histogram()[129:]) > height / 2]
        rows = [y for y in range(height) if sum(alpha.crop((0, y, width, y + 1)).histogram()[129:]) > width / 2]
        if not columns or not rows:
            continue
        x, y = columns[0], rows[0]
        visible_width, visible_height = columns[-1] + 1 - x, rows[-1] + 1 - y
        if (x, y, visible_width, visible_height) != (0, 0, width, height):
            bounds[path.relative_to(root).as_posix()] = [width, height, x, y, visible_width, visible_height]
(web / "src" / "coverBounds.json").write_text(json.dumps(bounds, indent=2) + "\n", encoding="utf-8")
print(f"{len(bounds)} covers with transparent margins")

"""Cut prop reference crops out of the reference screenshot.

Reads props/crops.json, writes props/crops/<name>.png for every prop with
gen=true. Trellis.2 wants a single centered object, so each crop gets a
margin of padding around the box.
"""

import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PAD = 0.08  # fraction of box size added on each side


def main() -> None:
    spec = json.loads((ROOT / "props" / "crops.json").read_text())
    img = Image.open(ROOT / spec["image"]).convert("RGB")
    out_dir = ROOT / "props" / "crops"
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, prop in spec["props"].items():
        if not prop.get("gen"):
            continue
        x, y, w, h = prop["box"]
        px, py = int(w * PAD), int(h * PAD)
        box = (max(0, x - px), max(0, y - py),
               min(img.width, x + w + px), min(img.height, y + h + py))
        crop = img.crop(box)
        path = out_dir / f"{name}.png"
        crop.save(path)
        print(f"{name}: {crop.size[0]}x{crop.size[1]} -> {path.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())

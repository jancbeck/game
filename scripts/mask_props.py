"""Add alpha mattes to the prop crops with rembg (u2net).

Writes props/crops/<name>_rgba.png for every crop. Trellis.2 skips its own
background remover when the input already has a useful alpha channel.

Usage: U2NET_HOME=weights/u2net .venv/bin/python scripts/mask_props.py [name ...]
"""

import sys
from pathlib import Path

from PIL import Image
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parent.parent
CROPS = ROOT / "props" / "crops"


def main() -> None:
    names = sys.argv[1:] or [p.stem for p in CROPS.glob("*.png") if not p.stem.endswith("_rgba")]
    session = new_session("u2net")
    for name in names:
        src = CROPS / f"{name}.png"
        out = CROPS / f"{name}_rgba.png"
        img = Image.open(src).convert("RGB")
        result = remove(img, session=session)
        result.save(out)
        alpha = result.getchannel("A")
        coverage = sum(1 for p in alpha.getdata() if p > 128) / (alpha.width * alpha.height)
        print(f"{name}: foreground {coverage:.0%} -> {out.name}")


if __name__ == "__main__":
    main()

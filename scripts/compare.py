"""Compare a render against the reference screenshot.

Writes, next to the render:
  compare_<name>.png  reference | render | abs-difference
  blend_<name>.png    50/50 overlay, the quickest way to judge alignment

Prints scores:
  edges  correlation of blurred edge maps (geometry: 1 = same outlines)
  MAE    mean absolute color error (look: 0 = identical), with per-third luma
  style  framing-independent look statistics, render vs reference:
         luma and saturation means, palette distance (0 = same color
         distribution) and detail (fine-scale contrast; ratio 1 = as busy as
         the reference). The scene camera frames more than the reference, so
         style is the score to watch for look work.

Usage: .venv/bin/python scripts/compare.py renders/iter_002.png
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "ref" / "courtyard.webp"


def edge_map(img):
    g = np.asarray(img.convert("L").filter(ImageFilter.GaussianBlur(2)), dtype=np.float32)
    gx = np.abs(np.diff(g, axis=1))[:-1, :]
    gy = np.abs(np.diff(g, axis=0))[:, :-1]
    mag = np.hypot(gx, gy)
    e = Image.fromarray(np.clip(mag * (255 / max(mag.max(), 1e-6)), 0, 255).astype(np.uint8))
    # widen edges so a few pixels of misalignment still overlap
    e = np.asarray(e.filter(ImageFilter.GaussianBlur(4)), dtype=np.float32)
    return (e - e.mean()) / (e.std() + 1e-6)


def _stats(x):
    luma = x @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    sat = x.max(axis=2) - x.min(axis=2)
    q = np.clip((x * 8).astype(int), 0, 7)
    hist = np.bincount((q[..., 0] * 64 + q[..., 1] * 8 + q[..., 2]).ravel(), minlength=512).astype(np.float64)
    lap = np.abs(luma[1:-1, 1:-1] * 4 - luma[:-2, 1:-1] - luma[2:, 1:-1] - luma[1:-1, :-2] - luma[1:-1, 2:])
    return luma.mean(), sat.mean(), hist / hist.sum(), lap.mean()


def style(a, b):
    la, sa, ha, da = _stats(a)
    lb, sb, hb, db = _stats(b)
    palette = 0.5 * np.abs(ha - hb).sum()
    print(f"style: luma {lb:.3f} (ref {la:.3f})  saturation {sb:.3f} (ref {sa:.3f})  "
          f"palette {palette:.3f}  detail {db / da:.2f}")


def main() -> None:
    render_path = Path(sys.argv[1])
    ref = Image.open(REF).convert("RGB")
    ren = Image.open(render_path).convert("RGB").resize(ref.size)

    edges = float((edge_map(ref) * edge_map(ren)).mean())
    a = np.asarray(ref, dtype=np.float32) / 255
    b = np.asarray(ren, dtype=np.float32) / 255
    diff = np.abs(a - b)
    print(f"edges: {edges:.3f}  (geometry, 1 = same outlines)")
    print(f"MAE:   {diff.mean():.4f}  (look, 0 = identical)")
    h = a.shape[0]
    for name, sl in [("top", slice(0, h // 3)), ("middle", slice(h // 3, 2 * h // 3)), ("bottom", slice(2 * h // 3, h))]:
        print(f"{name:>7}: ref luma {a[sl].mean():.3f}  render luma {b[sl].mean():.3f}  mae {diff[sl].mean():.3f}")

    style(a, b)

    out_dir = render_path.resolve().parent
    strip = Image.new("RGB", (ref.width * 3, ref.height))
    strip.paste(ref, (0, 0))
    strip.paste(ren, (ref.width, 0))
    strip.paste(Image.fromarray((diff * 255).astype(np.uint8)), (ref.width * 2, 0))
    strip.save(out_dir / f"compare_{render_path.stem}.png")
    Image.blend(ref, ren, 0.5).save(out_dir / f"blend_{render_path.stem}.png")
    print(f"composite -> {out_dir / f'compare_{render_path.stem}.png'}")
    print(f"overlay   -> {out_dir / f'blend_{render_path.stem}.png'}")


if __name__ == "__main__":
    main()

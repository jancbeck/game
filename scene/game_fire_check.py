"""Check frames for the fire flipbooks: each flipbook composited over the game frame, through the view transform.

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scene/game_fire_check.py -- \
        --flipbooks game/build/fire_flipbooks.json [--root game] [--compare game/data/scene.json] --out <dir> [--ids a,b]

For every flipbook in the list it composites the atlas frames over base + all light groups (the
group at intensity 1, as `reference.png`), premultiplied, as the runtime does; applies AgX with the
scene's look; and writes <out>/<id>/f####.png crops (the flipbook rect with a margin, at the
flipbook's own density: a 2x flipbook goes over the frame upscaled 2x), plus a seam strip
(the last 3 and the first 3 frames). With --compare, the same is written for the flipbooks of that
scene.json with the same id, under <out>/<id>_compare/.
"""

import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "game"
MARGIN = 40


def read(path):
    """Pixels as stored: PNG colour is not multiplied by alpha on read (the atlases are already premultiplied)."""
    import OpenImageIO as oiio
    cfg = oiio.ImageSpec()
    cfg.attribute("oiio:UnassociatedAlpha", 1)
    buf = oiio.ImageBuf(str(path), 0, 0, cfg)
    s = buf.spec()
    return np.asarray(buf.get_pixels(oiio.FLOAT)).reshape(s.height, s.width, s.nchannels)


def srgb_decode(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def frames_of(fb, root):
    a = read(root / fb["atlas"])            # PNG: OIIO gives straight values as stored (premultiplied)
    cw, ch = fb.get("cell") or (a.shape[1] // fb["cols"], a.shape[0] // fb["rows"])
    out = []
    for i in range(fb["frames"]):
        r, c = divmod(i, fb["cols"])
        cell = a[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw]
        rgb = srgb_decode(cell[:, :, :3]) * fb.get("scale", 1.0) if fb.get("encoding", "srgb") == "srgb" else cell[:, :, :3]
        out.append(np.concatenate([rgb, cell[:, :, 3:4]], axis=2))
    return out


def display(lin, path, sc):
    h, w = lin.shape[:2]
    img = bpy.data.images.new("chk", w, h, alpha=False, float_buffer=True)
    img.colorspace_settings.name = "Linear Rec.709"
    px = np.ones((h, w, 4), np.float32)
    px[:, :, :3] = lin[::-1]
    img.pixels.foreach_set(px.ravel())
    img.save_render(str(path), scene=sc)
    bpy.data.images.remove(img)


def resize(img, w, h):
    import OpenImageIO as oiio
    src = oiio.ImageBuf(np.ascontiguousarray(img.astype(np.float32)))
    dst = oiio.ImageBufAlgo.resize(src, roi=oiio.ROI(0, w, 0, h, 0, 1, 0, img.shape[2]))
    return np.asarray(dst.get_pixels(oiio.FLOAT)).reshape(h, w, img.shape[2])


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--flipbooks", default=str(GAME / "build" / "fire_flipbooks.json"))
    ap.add_argument("--root", default=str(GAME), help="game dir the flipbooks' atlases are under")
    ap.add_argument("--compare", default=None)
    ap.add_argument("--compare-root", default=str(GAME), help="game dir the compared atlases are under")
    ap.add_argument("--ids", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out)
    scene = json.loads((GAME / "data" / "scene.json").read_text())
    sc = bpy.context.scene
    sc.view_settings.view_transform = scene["layers"].get("view_transform", "AgX")
    sc.view_settings.look = scene["layers"].get("look") or "None"
    sc.view_settings.exposure = 0.0
    sc.render.image_settings.file_format = "PNG"
    frame = read(GAME / scene["layers"]["base"])[:, :, :3]
    for g in scene["layers"]["groups"]:
        frame = frame + read(GAME / g["image"])[:, :, :3]
    books = json.loads(Path(args.flipbooks).read_text())
    books = list(books.values()) if isinstance(books, dict) else books
    compare = {}
    if args.compare:
        compare = {fb["id"]: fb for fb in json.loads(Path(args.compare).read_text())["flipbooks"]}
    jobs = []
    for fb in books:
        if args.ids and fb["id"] not in args.ids.split(","):
            continue
        jobs.append((fb["id"], fb, Path(args.root)))
        if fb["id"] in compare:
            jobs.append((fb["id"] + "_compare", compare[fb["id"]], Path(args.compare_root)))
    for name, fb, root in jobs:
        d = fb.get("density", 1)
        x, y, w, h = fb["rect"]
        x0, y0 = max(0, x - MARGIN), max(0, y - MARGIN)
        x1, y1 = min(frame.shape[1], x + w + MARGIN), min(frame.shape[0], y + h + MARGIN)
        bg = frame[y0:y1, x0:x1]
        if d != 1:
            bg = resize(bg, (x1 - x0) * d, (y1 - y0) * d)
        frs = frames_of(fb, root)
        cw, ch = frs[0].shape[1], frs[0].shape[0]
        ox, oy = (x - x0) * d, (y - y0) * d
        if (cw, ch) != (w * d, h * d):
            frs = [resize(f, w * d, h * d) for f in frs]
        o = out / name
        o.mkdir(parents=True, exist_ok=True)
        for i, f in enumerate(frs):
            img = bg.copy()
            sub = img[oy:oy + f.shape[0], ox:ox + f.shape[1]]
            sub[:] = f[:, :, :3] + sub * (1 - f[:, :, 3:4])
            display(img, o / f"f{i:04d}.png", sc)
        print("CHECK", name, len(frs), "frames ->", o)


if __name__ == "__main__":
    main()

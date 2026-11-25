#!/usr/bin/env python3
"""Can the player walk to every stand point of a room? The check Godot's navmesh answers at run time, without Godot.

    .venv/bin/python scripts/walkcheck.py [--location cookhouse] [--png walk.png]

Builds the room in Blender (CPU, no render, about 15 s, no GPU queue), writes its proxy.glb and walk.glb to a temporary
folder, and rasterises the floor of plan.json `platform.walk` minus the footprint hulls of the props (the same hulls
export_game.py cuts and game/scripts/navigation.gd carves). The floor is eroded by the agent radius 0.3 m, as the
navmesh bake does. Reports, for every hotspot stand, exit and person of location.json, the clearance to the nearest
obstacle and whether the point is in the largest walkable region; a point counts as reachable when that region lies
within 0.35 m of it (`navigation.gd` reachable()). Needs numpy, scipy and Pillow (the project .venv has them).
A lane is walkable when it is 0.7 m wide or more; keep stand points 0.35 m clear of every hull.
"""

import argparse
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
RADIUS, TOLERANCE, STEP = 0.3, 0.35, 0.025

BUILD = """
import sys
from pathlib import Path
sys.path.insert(0, "%(root)s/scene")
import export_game as eg, game_frame as gf, location
location.use("%(loc)s")
plan, trace, layout, cam = gf.build(None)
out = Path("%(out)s")
(out / "assets").mkdir(parents=True, exist_ok=True)
counts, hulls = eg.export_proxies(plan, out)
eg.export_walk(plan, hulls, out)
"""


def glb_meshes(path):
    """{node name: (n, 3) triangle vertices in the file's axes} of a .glb."""
    b = Path(path).read_bytes()
    size, = struct.unpack("<I", b[12:16])
    doc = json.loads(b[20:20 + size])
    blob = b[20 + size + 8:]

    def accessor(i):
        a = doc["accessors"][i]
        view = doc["bufferViews"][a["bufferView"]]
        n = {"SCALAR": 1, "VEC3": 3}[a["type"]]
        dtype = {5126: "<f4", 5123: "<u2", 5125: "<u4"}[a["componentType"]]
        arr = np.frombuffer(blob, dtype=dtype, count=a["count"] * n, offset=view.get("byteOffset", 0) + a.get("byteOffset", 0))
        return arr.reshape(-1, n) if n > 1 else arr
    out = {}
    for node in doc["nodes"]:
        if "mesh" in node:
            tris = []
            for p in doc["meshes"][node["mesh"]]["primitives"]:
                pos = accessor(p["attributes"]["POSITION"])
                tris.append(pos[accessor(p["indices"])] if "indices" in p else pos)
            out[node.get("name", "?")] = np.concatenate(tris)
    return out


def hull(pts):
    pts = sorted(set(map(tuple, np.round(pts, 4))))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def points(loc):
    """(label, (x, y)) of the stands, exits and people of a location, plan metres."""
    table = json.loads((ROOT / "locations" / loc / "location.json").read_text())
    out = [(f"stand {h['id']}", tuple(h["stand"])) for h in table.get("hotspots", [])]
    out += [(f"exit {e['id']}", tuple(e["pos"])) for e in table.get("exits", {}).get("list", [])]
    for pid, p in table.get("people", {}).items():
        if not pid.startswith("_"):
            out.append((f"{pid} stand", tuple(p["stand"])))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--location", default="cookhouse")
    ap.add_argument("--png", default=None, help="write a picture: grey floor, green eroded floor, blue the largest region")
    args = ap.parse_args()
    loc = args.location
    plan = json.loads((ROOT / "locations" / loc / "plan.json").read_text())
    if plan.get("kind") != "room":
        sys.exit(f"{loc} is not a room")
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "build.py"
        script.write_text(BUILD % dict(root=ROOT, loc=loc, out=tmp))
        r = subprocess.run([BLENDER, "--background", "--python-exit-code", "1", "--python", str(script)],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(r.stdout[-2000:] + r.stderr[-2000:])
        proxy = glb_meshes(Path(tmp) / "assets" / "proxy.glb")
    poly = plan["platform"]["walk"]
    hulls = []
    for name, v in proxy.items():
        if name.startswith("prop"):
            h = hull(np.stack([v[:, 0], -v[:, 2]], 1))         # godot (x, y, z) -> plan (x, -z)
            if len(h) >= 3:
                hulls.append((name, h))
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    x0, y0 = min(xs) - 0.3, min(ys) - 0.3
    nx, ny = int((max(xs) + 0.3 - x0) / STEP) + 1, int((max(ys) + 0.3 - y0) / STEP) + 1

    def raster(polys):
        img = Image.new("L", (nx, ny), 0)
        d = ImageDraw.Draw(img)
        for p in polys:
            d.polygon([((a - x0) / STEP, (b - y0) / STEP) for a, b in p], fill=1)
        return np.array(img, bool)
    free = raster([poly]) & ~raster([h for _, h in hulls])
    clearance = ndimage.distance_transform_edt(free) * STEP
    eroded = clearance >= RADIUS
    labels, n = ndimage.label(eroded)
    if not n:
        sys.exit("nothing is walkable")
    sizes = ndimage.sum(eroded, labels, range(1, n + 1)) * STEP * STEP
    main = labels == int(np.argmax(sizes)) + 1
    to_main = ndimage.distance_transform_edt(~main) * STEP
    print(f"{loc}: walkable region {sizes.max():.1f} m2 of {sum(sizes):.1f} m2 eroded floor in {n} piece(s)")
    bad = 0
    pts = points(loc)
    for label, (x, y) in pts:
        i, j = int(round((y - y0) / STEP)), int(round((x - x0) / STEP))
        ok = to_main[i, j] <= TOLERANCE
        bad += not ok
        print(f"  {'ok ' if ok else 'BAD'} {label:28s} ({x:+.2f}, {y:+.2f})  clear {clearance[i, j]:.2f} m  to region {to_main[i, j]:.2f} m")
    if args.png:
        img = np.zeros((ny, nx, 3), np.uint8)
        img[free] = (90, 90, 90)
        img[eroded] = (40, 160, 70)
        img[main] = (90, 200, 255)
        out = Image.fromarray(img[::-1]).resize((nx * 2, ny * 2), Image.NEAREST)
        d = ImageDraw.Draw(out)
        for _, (x, y) in pts:
            cx, cy = (x - x0) / STEP * 2, (ny - (y - y0) / STEP) * 2
            d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), outline=(255, 255, 0), width=2)
        out.save(args.png)
        print(f"picture: {args.png}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

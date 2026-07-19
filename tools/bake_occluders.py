#!/usr/bin/env python3
"""Offline baker for painted-scene occluder cards.

Occluder cards are the "depth map" of the painted-scene pipeline: each
occluder polygon in data/scenes/<id>.json is a foreground prop painted into
the backdrop. At runtime the card is mounted as an alpha-scissor quad at the
anchor's true 3D depth, so characters walking behind the anchor line are
genuinely occluded by the depth buffer. This tool cuts those cards out of
the backdrop PNGs at build time; the runtime only loads the results
(scripts/systems/painted_scene.gd).

RE-RUN THIS after changing a backdrop PNG or any occluder polygon/anchor.
Outputs are COMMITTED artifacts under art/occluders/<scene>/ — they are not
generated in CI; CI only checks they are fresh (tools/bake_occluders.py
--check, the drift guard against "backdrop regenerated, cards not rebaked").

Outputs per scene manifest with a non-empty "occluders" array:
  art/occluders/<scene>/occluder_<i>.png  trimmed RGBA card, manifest order
  art/occluders/<scene>/cards.json        {"scene", "cards": [{card, anchor,
                                          bounds: [x, y, w, h]}]}

The cut reproduces the original GDScript semantics EXACTLY (they are the
spec the runtime loader is coded against):
  * bounds = Rect2i(p0.x, p0.y, 1, 1).expand(every point): origin is the
    componentwise min, end the componentwise max but at least p0 + 1 — the
    max point itself is EXCLUDED (a Rect2i covers [position, position+size)).
  * inside test = Geometry2D.is_point_in_polygon (pnpoly, even-odd) on the
    INTEGER pixel coordinate, not the pixel center.
  * outside pixels keep their RGB from the backdrop; only alpha is cleared.

Usage:
  tools/bake_occluders.py          bake and write all cards
  tools/bake_occluders.py --check  re-bake in memory, exit 1 on any drift
"""
import io
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SCENES_DIR = ROOT / "data" / "scenes"
OUT_ROOT = ROOT / "art" / "occluders"


def _rect2i_bounds(points):
    """Rect2i(p0, 1, 1).expand(...) bounds as [x, y, w, h] (max excluded)."""
    ipoints = [(int(p[0]), int(p[1])) for p in points]  # Vector2i(): truncates
    ox = min(p[0] for p in ipoints)
    oy = min(p[1] for p in ipoints)
    ex = max(max(p[0] for p in ipoints), ipoints[0][0] + 1)
    ey = max(max(p[1] for p in ipoints), ipoints[0][1] + 1)
    return [ox, oy, ex - ox, ey - oy]


def _is_point_in_polygon(px, py, polygon):
    """Godot 4 Geometry2D.is_point_in_polygon verbatim (pnpoly, even-odd)."""
    inside = False
    x0, y0 = polygon[-1]
    for x1, y1 in polygon:
        if (y1 > py) != (y0 > py) and px < (x0 - x1) * (py - y1) / (y0 - y1) + x1:
            inside = not inside
        x0, y0 = x1, y1
    return inside


def _bake_card(backdrop, polygon, bounds):
    """Trimmed RGBA card for one occluder: backdrop region, outside alpha=0."""
    bx, by, w, h = bounds
    card = backdrop.crop((bx, by, bx + w, by + h))
    mask = Image.new("L", (w, h), 0)
    pixel = mask.load()
    for y in range(h):
        for x in range(w):
            if _is_point_in_polygon(bx + x, by + y, polygon):
                pixel[x, y] = 255
    # Composite rather than putalpha: inside pixels keep the backdrop's
    # original alpha verbatim, exactly like the GDScript path did.
    r, g, b, a = card.split()
    a = Image.composite(a, Image.new("L", (w, h), 0), mask)
    return Image.merge("RGBA", (r, g, b, a))


def _png_bytes(image):
    """Deterministic encoding (explicit compress_level) so --check can
    compare committed PNG bytes against an in-memory re-bake."""
    buf = io.BytesIO()
    image.save(buf, format="PNG", compress_level=6)
    return buf.getvalue()


def _bake_scene(scene_id, manifest):
    """All files one scene implies, as {repo-relative path: bytes}."""
    backdrop_rel = str(manifest["backdrop"]).removeprefix("res://")
    backdrop_path = ROOT / backdrop_rel
    if not backdrop_path.is_file():
        sys.exit(f"error: {scene_id}: backdrop not found: {backdrop_rel}")
    backdrop = Image.open(backdrop_path).convert("RGBA")
    files = {}
    cards = []
    for i, occluder in enumerate(manifest["occluders"]):
        bounds = _rect2i_bounds(occluder["polygon"])
        bx, by, w, h = bounds
        if bx < 0 or by < 0 or bx + w > backdrop.width or by + h > backdrop.height:
            sys.exit(
                f"error: {scene_id}: occluder {i} bounds {bounds} exceed "
                f"backdrop {backdrop.width}x{backdrop.height}"
            )
        polygon = [(float(p[0]), float(p[1])) for p in occluder["polygon"]]
        card = _bake_card(backdrop, polygon, bounds)
        rel = f"art/occluders/{scene_id}/occluder_{i}.png"
        files[rel] = _png_bytes(card)
        cards.append(
            {
                "card": f"res://{rel}",
                "anchor": occluder["anchor"],
                "bounds": bounds,
            }
        )
    payload = json.dumps({"scene": scene_id, "cards": cards}, indent=2) + "\n"
    files[f"art/occluders/{scene_id}/cards.json"] = payload.encode("utf-8")
    return files


def _expected_files():
    """Everything the current scene manifests imply, {repo-rel path: bytes}."""
    files = {}
    for manifest_path in sorted(SCENES_DIR.glob("*.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not manifest.get("occluders"):
            continue
        scene_id = str(manifest.get("id", manifest_path.stem))
        files.update(_bake_scene(scene_id, manifest))
    return files


def _is_managed(path):
    """Files the baker owns inside art/occluders/ (never .DS_Store et al.)."""
    return path.name == "cards.json" or (
        path.name.startswith("occluder_") and path.suffix == ".png"
    )


def _check(expected):
    problems = []
    for rel in sorted(expected):
        path = ROOT / rel
        if not path.is_file():
            problems.append(f"missing: {rel}")
        elif path.read_bytes() != expected[rel]:
            problems.append(f"differs: {rel}")
    if OUT_ROOT.is_dir():
        for path in sorted(OUT_ROOT.rglob("*")):
            rel = path.relative_to(ROOT).as_posix()
            if path.is_file() and _is_managed(path) and rel not in expected:
                problems.append(f"stale: {rel}")
    if problems:
        print("Occluder cards are out of date — re-run tools/bake_occluders.py:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(f"Occluder cards up to date ({len(expected)} files)")
    return 0


def _bake(expected):
    expected_dirs = {}
    for rel in expected:
        expected_dirs.setdefault(str(Path(rel).parent), []).append(rel)
    if OUT_ROOT.is_dir():
        for stale in sorted(OUT_ROOT.iterdir()):
            rel_dir = f"art/occluders/{stale.name}"
            if stale.is_dir() and rel_dir not in expected_dirs:
                shutil.rmtree(stale)
                print(f"removed stale {rel_dir}/")
    for rel_dir in sorted(expected_dirs):
        directory = ROOT / rel_dir
        directory.mkdir(parents=True, exist_ok=True)
        # Drop previously baked managed files first, so a shrunken occluder
        # array never leaves a stale occluder_<i>.png behind.
        for old in directory.iterdir():
            if old.is_file() and _is_managed(old):
                old.unlink()
        for rel in sorted(expected_dirs[rel_dir]):
            (ROOT / rel).write_bytes(expected[rel])
            print(f"wrote {rel}")
    return 0


def main():
    args = sys.argv[1:]
    unknown = [a for a in args if a != "--check"]
    if unknown:
        sys.exit(f"usage: bake_occluders.py [--check] (unknown: {' '.join(unknown)})")
    expected = _expected_files()
    if "--check" in args:
        return _check(expected)
    return _bake(expected)


if __name__ == "__main__":
    sys.exit(main())

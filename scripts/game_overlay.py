"""Check images for the game export, drawn over game/assets/layers/reference.png.

    Blender --background --python scripts/game_overlay.py      # writes game/build/overlay.json
    .venv/bin/python scripts/game_overlay.py draw              # walk mesh, exits, perches: game/build/overlay_walk.png
    .venv/bin/python scripts/game_overlay.py flip              # each flipbook's frame 0 composited at its rect:
                                                               # game/build/flip_<id>.png (reference | composite)
    .venv/bin/python scripts/game_overlay.py views             # zoom views and id masks (scene/game_views.py):
                                                               # game/build/check_ids_main.png, check_wide.png,
                                                               # check_tile_<id>.png
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "game"

if "flip" in sys.argv:
    import numpy as np
    from PIL import Image
    s = json.loads((GAME / "data" / "scene.json").read_text())
    ref = np.asarray(Image.open(GAME / "assets" / "layers" / "reference.png").convert("RGB")) / 255.0
    lin = lambda c: np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)  # noqa: E731
    enc = lambda c: np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - 0.055)  # noqa: E731
    for f in s["flipbooks"]:
        at = np.asarray(Image.open(GAME / f["atlas"]).convert("RGBA")) / 255.0
        cw, ch = f["cell"]
        x, y, w, h = f["rect"]
        cell = Image.fromarray((at[:ch, :cw] * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
        cell = np.asarray(cell) / 255.0
        rgb, a = lin(cell[:, :, :3]) * f["scale"], cell[:, :, 3:4]
        m = 40
        X0, Y0, X1, Y1 = max(0, x - m), max(0, y - m), min(ref.shape[1], x + w + m), min(ref.shape[0], y + h + m)
        under = ref[Y0:Y1, X0:X1].copy()
        comp = under.copy()
        sub = lin(comp[y - Y0:y - Y0 + h, x - X0:x - X0 + w])
        # display-referred approximation: the reference is AgX, the flipbook linear; enough to judge registration
        comp[y - Y0:y - Y0 + h, x - X0:x - X0 + w] = np.clip(enc(rgb * 0.6 + (1 - a) * sub), 0, 1)
        side = np.concatenate([under, comp], axis=1)
        img = Image.fromarray((side * 255).astype(np.uint8))
        if img.width < 600:
            img = img.resize((img.width * 2, img.height * 2), Image.NEAREST)
        img.save(GAME / "build" / f"flip_{f['id']}.png")
    sys.exit(0)

if "draw" in sys.argv:
    from PIL import Image, ImageDraw
    d = json.loads((GAME / "build" / "overlay.json").read_text())
    base = Image.open(GAME / "assets" / "layers" / "reference.png").convert("RGB")
    sx = base.width / 2560
    over = Image.new("RGBA", base.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(over)
    for tri, z, _ in d["tris"]:
        col = (0, 255, 80, 70) if z < 0.1 else (255, 200, 0, 110)
        dr.polygon([(x * sx, y * sx) for x, y in tri], fill=col, outline=(0, 255, 80, 160) if z < 0.1 else (255, 200, 0, 220))
    for name, (x, y) in d["exits"]:
        dr.ellipse([x * sx - 7, y * sx - 7, x * sx + 7, y * sx + 7], fill=(255, 40, 40, 255))
        dr.text((x * sx + 9, y * sx - 6), name, fill=(255, 255, 255, 255))
    for x, y in d["perches"]:
        dr.ellipse([x * sx - 3, y * sx - 3, x * sx + 3, y * sx + 3], fill=(80, 160, 255, 255))
    Image.alpha_composite(base.convert("RGBA"), over).convert("RGB").save(GAME / "build" / "overlay_walk.png")

    # surface types: one colour per walk.glb material, portals as linked pairs
    colors = {"cobble": (150, 160, 175), "mud": (150, 95, 30), "straw": (240, 205, 60), "stone_stair": (230, 60, 200),
              "stone_walk": (60, 150, 255), "wood": (255, 90, 30)}
    over = Image.new("RGBA", base.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(over)
    for tri, z, mat in d["tris"]:
        c = colors.get(mat, (255, 0, 0))
        dr.polygon([(x * sx, y * sx) for x, y in tri], fill=(*c, 120))
    for p in d.get("portals", []):
        (ax, ay), (bx, by) = p["a"], p["b"]
        dr.line([(ax * sx, ay * sx), (bx * sx, by * sx)], fill=(255, 255, 255, 140), width=2)
        for (x, y), label in (((ax, ay), p["label"]), ((bx, by), p["label_b"])):
            dr.ellipse([x * sx - 8, y * sx - 8, x * sx + 8, y * sx + 8], fill=(255, 255, 255, 255))
            dr.text((x * sx + 10, y * sx - 18), label, fill=(255, 255, 255, 255))
    for i, (name, c) in enumerate(colors.items()):
        dr.rectangle([20, 20 + i * 26, 40, 40 + i * 26], fill=(*c, 255))
        dr.text((48, 24 + i * 26), name, fill=(255, 255, 255, 255))
    Image.alpha_composite(base.convert("RGBA"), over).convert("RGB").save(GAME / "build" / "overlay_surfaces.png")
    sys.exit(0)

if "views" in sys.argv:
    import numpy as np
    from PIL import Image, ImageDraw
    s = json.loads((GAME / "data" / "scene.json").read_text())
    hot = json.loads((GAME / "data" / "hotspots.json").read_text())
    pal = np.array([(0, 0, 0)] + [tuple(int(255 * c) for c in __import__("colorsys").hsv_to_rgb(k / 12, 0.9, 1.0))
                                  for k in range(12)], np.uint8)

    def ids_overlay(ref, ids):
        """Reference with each hotspot tinted in its colour and outlined (the runtime's outline input)."""
        ref = np.asarray(ref.convert("RGB")).astype(np.float32)
        tint = pal[ids].astype(np.float32)
        on = (ids > 0)[:, :, None]
        out = np.where(on, ref * 0.55 + tint * 0.45, ref)
        edge = np.zeros(ids.shape, bool)
        edge[1:] |= ids[1:] != ids[:-1]
        edge[:, 1:] |= ids[:, 1:] != ids[:, :-1]
        edge &= ids > 0
        out[edge] = 255
        return Image.fromarray(out.clip(0, 255).astype(np.uint8))

    def label(img, entries):
        dr = ImageDraw.Draw(img)
        for text, (x, y) in entries:
            dr.text((x + 1, y + 1), text, fill=(0, 0, 0))
            dr.text((x, y), text, fill=(255, 255, 255))
        return img

    ref = Image.open(GAME / s["layers"]["reference"])
    if "ids" in s["masks"]:
        ids = np.asarray(Image.open(GAME / s["masks"]["ids"]))
        img = ids_overlay(ref, ids)
        label(img, [(h["name"], h["screen_px"]) for h in hot]).save(GAME / "build" / "check_ids_main.png")
    v = s.get("views", {})
    if "wide" in v:
        w = v["wide"]
        wref = Image.open(GAME / w["reference"])
        wids = np.asarray(Image.open(GAME / w["ids"]))
        top = ids_overlay(wref, wids)
        dr = ImageDraw.Draw(top)
        dr.rectangle([640, 360, 1920, 1080], outline=(255, 255, 255), width=2)
        # the wide view's centre against the main frame at half size, and their difference x4
        centre = np.asarray(wref.convert("RGB"))[360:1080, 640:1920].astype(np.int16)
        main_half = np.asarray(ref.convert("RGB").resize((1280, 720), Image.LANCZOS)).astype(np.int16)
        diff = np.clip(np.abs(centre - main_half) * 4, 0, 255).astype(np.uint8)
        row = np.concatenate([main_half.astype(np.uint8), centre.astype(np.uint8), diff], axis=1)
        row = Image.fromarray(row).resize((2560, 480), Image.LANCZOS)
        sheet = Image.new("RGB", (2560, 1440 + 480))
        sheet.paste(top, (0, 0))
        sheet.paste(row, (0, 1440))
        label(sheet, [("wide view, ids tinted; white box = main frame", (20, 20)),
                      ("main frame / 2", (20, 1450)), ("wide centre", (873, 1450)), ("difference x4", (1726, 1450))])
        sheet.save(GAME / "build" / "check_wide.png")
        print("wide centre vs main/2: mean abs", float(np.abs(centre - main_half).mean()))
    for t in v.get("tiles", []):
        x0, y0, w_, h_ = t["rect"]
        k = t["scale"]
        tref = Image.open(GAME / t["reference"]).convert("RGB")
        up = ref.convert("RGB").crop((x0, y0, x0 + w_, y0 + h_)).resize(tref.size, Image.BICUBIC)
        tids = np.asarray(Image.open(GAME / t["ids"]))
        down = np.asarray(tref.resize((w_, h_), Image.LANCZOS)).astype(np.int16)
        main = np.asarray(ref.convert("RGB").crop((x0, y0, x0 + w_, y0 + h_))).astype(np.int16)
        diff = np.clip(np.abs(down - main) * 4, 0, 255).astype(np.uint8)
        half = lambda im: im.resize((tref.width // 2, tref.height // 2), Image.LANCZOS)  # noqa: E731
        sheet = Image.new("RGB", (tref.width, tref.height))
        sheet.paste(half(up), (0, 0))
        sheet.paste(half(tref), (tref.width // 2, 0))
        sheet.paste(half(ids_overlay(tref, tids)), (0, tref.height // 2))
        sheet.paste(Image.fromarray(diff).resize((tref.width // 2, tref.height // 2)), (tref.width // 2, tref.height // 2))
        label(sheet, [("main frame upscaled x2 (bicubic)", (20, 20)), (f"tile {t['id']} groups "
                      + ",".join(g["id"] for g in t["groups"]), (tref.width // 2 + 20, 20)),
                      ("tile ids", (20, tref.height // 2 + 20)), ("|tile/2 - main| x4", (tref.width // 2 + 20, tref.height // 2 + 20))])
        sheet.save(GAME / "build" / f"check_tile_{t['id']}.png")
        print(t["id"], "tile/2 vs main: mean abs", float(np.abs(down - main).mean()))
    sys.exit(0)

import bpy  # noqa: E402
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from mathutils import Vector  # noqa: E402

sys.path.insert(0, str(ROOT / "scene"))
import game_frame as gf  # noqa: E402
import location  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)
trace = location.load("trace.json")
cam = gf.camera_game(trace["camera"])
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam
r = bpy.context.scene.render
r.resolution_x, r.resolution_y = gf.RES
bpy.ops.import_scene.gltf(filepath=str(GAME / "assets" / "walk.glb"))
bpy.context.view_layer.update()
sc = bpy.context.scene


def px(p):
    v = world_to_camera_view(sc, cam, Vector(p))
    return [v.x * gf.RES[0], (1 - v.y) * gf.RES[1]]


tris = []
for ob in sc.objects:
    if ob.type != "MESH":
        continue
    me = ob.data
    me.calc_loop_triangles()
    for t in me.loop_triangles:
        ps = [ob.matrix_world @ me.vertices[i].co for i in t.vertices]
        slot = ob.material_slots[t.material_index] if len(ob.material_slots) > t.material_index else None
        tris.append([[px(p) for p in ps], max(p.z for p in ps), slot.material.name if slot and slot.material else ""])
s = json.loads((GAME / "data" / "scene.json").read_text())
g2b = lambda p: (p[0], -p[2], p[1])  # noqa: E731
exits = [[e["id"], px(g2b(e["pos"]))] for e in s["walk"]["exits"]]
perches = [px(g2b(p["pos"])) for p in s["crows"]["perches"]]
portals = [dict(p, a=px(g2b(p["a"])), b=px(g2b(p["b"]))) for p in s["walk"].get("portals", [])]
area = {}
for ob in sc.objects:
    if ob.type == "MESH":
        for f in ob.data.polygons:
            m = ob.material_slots[f.material_index].material.name if ob.material_slots else ""
            area[m] = area.get(m, 0.0) + f.area
print("OVERLAY walk area by material", {k: round(v, 1) for k, v in area.items()})
(GAME / "build" / "overlay.json").write_text(json.dumps({"tris": tris, "exits": exits, "perches": perches,
                                                         "portals": portals}))

"""Render the moving parts of the game frame as looping flipbooks, in EEVEE.

    /Applications/Blender.app/Contents/MacOS/Blender --background --python scene/game_flipbooks.py -- \
        [--location courtyard] [--only fire_basket_flame,...] [--out game]

Builds the static scene of game_frame.py once, at the game camera, and renders the flames, smoke
and embers of every open fire and the chimney and forge smoke in EEVEE. Every static object is a
holdout, so whatever stands in front of an element is already cut out. Poses come from anim.py, so
the motion is the motion of the videos; the shader clocks of the fire and smoke materials follow
the frame.

Passes. Elements of one kind share a time base, so each time step is one render of a region that
covers all elements of that kind, cropped into the elements' rects afterwards: one pass for the
flames (24 fps), one for the smoke (8 fps) and one for the embers, where each ember cloud is posed
at its own phase of its own period. Rects come from one full-frame probe render per kind.

Loops. Embers move on an exact loop (anim.Sparks), so one period is rendered. Flames and smoke are
not periodic: `frames + fade` frames are rendered and the last `fade` frames are cross-faded into
the first ones, so frame frames-1 runs on into frame 0.

Light. Flames and embers only emit: they are rendered without lights and the Cycles exposure of
layout.json is multiplied in, so they sit in the base layer's units. Smoke is lit, and EEVEE lights
a volume differently from Cycles (no occlusion of the sky, no light from emissive flames), so the
smoke pass uses the EEVEE balance of layout_preview.json, the look of the videos: its sky strength
and its exposure. Flipbooks
are rendered at rest (flame glow and light energy at 1): the runtime multiplies an element by its
light group's intensity(t). The haze box is left out; its veil is in the base layer. EEVEE's
volume slices are fitted to the smoke's depth around the camera.

Output, under <out>/:

  assets/flipbooks/<id>.png   atlas, cols x rows cells, frames row-major from the top left,
                              premultiplied RGBA; rgb = srgb_encode(linear / scale)
  build/flipbooks.json        the flipbook list, read by export_game.py
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scene"))

import anim  # noqa: E402
import game_frame as gf  # noqa: E402
import game_layers as gl  # noqa: E402
import location  # noqa: E402

FPS = 24.0
MAX_ATLAS = 4096
PAD_PX = 8
TAA = {"flame": 16, "embers": 8, "smoke": 16}


# ---------- elements ----------

def elements(srcs):
    """The flipbook elements: dicts with id, objects, kind, frames, fps, fade, samples, group."""
    out = []
    taken = set()
    for d in srcs:
        if d["kind"] not in gf.FLIPBOOK_KINDS:
            continue
        if d["flames"]:
            out.append(dict(id=f"{d['id']}_flame", objects=d["flames"], kind="flame", frames=48, fps=24.0,
                            fade=12, group=d["id"]))
        for ob in d["smoke"]:
            name = "chimney_smoke" if "chimney" in ob.name else "smoke"
            out.append(dict(id=f"{d['id']}_{name}", objects=[ob], kind="smoke", frames=32, fps=8.0,
                            fade=10, group=None))
            taken.add(ob.name)
    # smoke plumes of props that are not open fires (the forge), and embers by nearest fire
    fires = [d for d in srcs if d["kind"] in gf.FLIPBOOK_KINDS]
    for ob in bpy.data.objects:
        if ob.type != "MESH" or ob.name in taken:
            continue
        mats = gf._mats(ob)
        key = gf.prop_key(ob)
        if "smoke" in mats and "density" in ob:
            sid = next((d["id"] for d in srcs if ob in d["smoke"]), (key or "prop").replace("#", "_"))
            out.append(dict(id=f"{sid}_{'chimney_smoke' if 'chimney' in ob.name else 'smoke'}", objects=[ob],
                            kind="smoke", frames=32, fps=8.0, fade=10, group=None))
        elif "embers" in mats and "spark" in ob.data.attributes:
            p = ob.matrix_world.translation
            d = min(fires, key=lambda d: (gf.anchor(d) - p).length)
            sp = next(s for s in anim._STATE["sparks"] if s.ob == ob)
            n = max(12, int(round(sp.life * FPS)))
            out.append(dict(id=f"{d['id']}_embers", objects=[ob], kind="embers", frames=n, fps=n / sp.life,
                            fade=0, group=d["id"]))
    # unique ids
    seen = {}
    for e in out:
        if e["id"] in seen:
            seen[e["id"]] += 1
            e["id"] = f"{e['id']}_{seen[e['id']]}"
        else:
            seen[e["id"]] = 0
    return out


# ---------- scene state ----------

def setup_eevee(sc):
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.film_transparent = True
    sc.render.use_compositing = False
    sc.render.resolution_x, sc.render.resolution_y = gf.RES
    sc.render.resolution_percentage = 100
    ee = sc.eevee
    ee.taa_render_samples = 16
    if hasattr(ee, "use_raytracing"):
        ee.use_raytracing = False
    ee.use_volumetric_shadows = True
    ee.volumetric_tile_size = "2"
    ee.volumetric_samples = 64
    ee.shadow_pool_size = "1024"
    # the ground mist's handler refits the volume range before every render; the mist is not drawn here
    for fn in [f for f in bpy.app.handlers.render_pre if f.__name__ == "_fit_volume_range"]:
        bpy.app.handlers.render_pre.remove(fn)
    st = sc.render.image_settings
    if hasattr(st, "media_type"):
        st.media_type = "IMAGE"
    st.file_format = "OPEN_EXR"
    st.color_mode = "RGBA"
    st.color_depth = "32"


def holdout_static(keep, name="flip_holdout"):
    """Every visible static mesh except `keep` gets a plain Holdout material: static geometry only
    cuts the moving parts out, and that shader is far cheaper to draw than the scene's materials
    (is_holdout still shades them)."""
    hold = bpy.data.materials.new(name)
    hold.use_nodes = True
    nt = hold.node_tree
    nt.nodes.clear()
    h = nt.nodes.new("ShaderNodeHoldout")
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(h.outputs[0], o.inputs["Surface"])
    for ob in bpy.data.objects:
        if ob.type in ("MESH", "CURVE") and not ob.hide_render and ob.visible_camera and ob not in keep:
            if not ob.material_slots:
                ob.data.materials.append(hold)
            for slot in ob.material_slots:
                slot.link = "OBJECT"
                slot.material = hold


class Stage:
    """Holdouts, visibility and pose of the moving parts."""

    def __init__(self, srcs, cam, els):
        self.cam = cam
        holdout_static({ob for e in els for ob in e["objects"]})
        self.lights = [ob for ob in bpy.data.objects if ob.type == "LIGHT"]
        haze = bpy.data.objects.get("haze")
        if haze:
            haze.hide_render = True
        # lights stay at rest and the crows stay hidden: anim.py must not touch them, or every frame
        # would invalidate EEVEE's shadow maps. The trees are holdouts, the embers have their own pass.
        for src in anim._STATE["sources"]:
            src.lights = []
        anim._STATE["sways"] = []
        self.sparks = anim._STATE["sparks"]
        anim._STATE["sparks"] = []
        anim._STATE["crows"] = type("NoCrows", (), {"apply": lambda self, t: None})()
        self.glow = [ob for ob in bpy.data.objects if anim.GLOW_ATTR in ob]
        self.els = els
        self.show([])

    def lighting(self, kind):
        """Flames and embers only emit: no lights. Smoke is lit by the sky, the moon and the fires,
        without shadow maps (the plumes stand in the open, beside their own fire)."""
        for li in self.lights:
            li.hide_render = kind != "smoke"
            li.data.use_shadow = False

    def show(self, objs):
        on = set(objs)
        for e in self.els:
            for ob in e["objects"]:
                ob.hide_render = ob not in on
                ob.visible_camera = True
                ob.is_holdout = False

    def pose(self, t):
        """Flames and smoke at time t (the shader clocks follow the scene frame, set by the caller)."""
        anim.apply(t)
        for ob in self.glow:
            ob[anim.GLOW_ATTR] = 1.0


def project_rect(objs, cam, res):
    """Pixel rect [x0, y0, x1, y1] of the objects' bounding boxes in the full frame."""
    sc = bpy.context.scene
    xs, ys = [], []
    for ob in objs:
        for c in ob.bound_box:
            v = world_to_camera_view(sc, cam, ob.matrix_world @ Vector(c))
            xs.append(v.x * res[0])
            ys.append((1 - v.y) * res[1])
    return [max(0, int(min(xs))), max(0, int(min(ys))), min(res[0], int(math.ceil(max(xs)))),
            min(res[1], int(math.ceil(max(ys))))]


def plume_points(ob):
    """World points around a smoke plume (assets/_fire.smoke): the box itself is far bigger."""
    yaw = math.radians(ob["ang0"])
    wind = Vector((math.cos(yaw), math.sin(yaw), 0.0))
    side = Vector((-wind.y, wind.x, 0.0))
    base = ob.matrix_world.translation
    r1, rise, drift = ob["r1"], ob["rise"], ob["drift"]
    pts = []
    for u in (-ob["r0"] - 0.3, 2.7 * drift + r1):
        for v in (-1.3 * r1, 1.3 * r1):
            for z in (-0.6 * r1, rise + 1.6 * r1):
                pts.append(base + wind * u + side * v + Vector((0, 0, z)))
    return pts


def render_region(rect, path):
    """Render the pixel rect [x0, y0, x1, y1] of the game frame; returns RGBA float (row 0 at the top)."""
    import OpenImageIO as oiio
    sc = bpy.context.scene
    r = sc.render
    res = gf.RES
    x0, y0, x1, y1 = rect
    full = (x0, y0, x1, y1) == (0, 0, res[0], res[1])
    r.use_border = not full
    r.use_crop_to_border = not full
    r.border_min_x, r.border_max_x = x0 / res[0], x1 / res[0]
    r.border_min_y, r.border_max_y = 1 - y1 / res[1], 1 - y0 / res[1]
    r.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    buf = oiio.ImageBuf(str(path))
    a = np.asarray(buf.get_pixels(oiio.FLOAT)).reshape(buf.spec().height, buf.spec().width, -1)
    return a


def element_box(e, cam):
    """Generous pixel rect from geometry: plume shape for smoke, grown boxes for flames and embers."""
    res = gf.RES
    if e["kind"] == "smoke":
        sc = bpy.context.scene
        uv = [world_to_camera_view(sc, cam, p) for p in plume_points(e["objects"][0])]
        return [max(0, int(min(v.x for v in uv) * res[0])), max(0, int(min(1 - v.y for v in uv) * res[1])),
                min(res[0], int(max(v.x for v in uv) * res[0]) + 1), min(res[1], int(max(1 - v.y for v in uv) * res[1]) + 1)]
    box = project_rect(e["objects"], cam, res)
    w, h = box[2] - box[0], box[3] - box[1]
    g = 0.6
    return [max(0, int(box[0] - g * w)), max(0, int(box[1] - g * h * 1.5)),
            min(res[0], int(box[2] + g * w)), min(res[1], int(box[3] + g * h * 0.3))]


def union(rects):
    return [min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects)]


def crop(img, region, rect):
    x0, y0 = rect[0] - region[0], rect[1] - region[1]
    return img[y0:y0 + rect[3] - rect[1], x0:x0 + rect[2] - rect[0]]


def fit_volumes(els, cam):
    """EEVEE volume slices only over the depth the smoke plumes occupy."""
    view = -Vector(cam.matrix_world.to_3x3().col[2]).normalized()
    ds = [(p - cam.matrix_world.translation).dot(view) for e in els for p in plume_points(e["objects"][0])]
    ee = bpy.context.scene.eevee
    ee.volumetric_start = max(0.1, min(ds) - 1.0)
    ee.volumetric_end = max(ds) + 1.0
    return ee.volumetric_start, ee.volumetric_end


def poser(kind, els, stage):
    """(frame step, function i -> pose the pass's elements for its i-th frame)."""
    if kind == "embers":
        sparks = {sp.ob: sp for sp in stage.sparks}

        def pose(i):
            for e in els:
                ob = e["objects"][0]
                ob.hide_render = i >= e["n"]
                if not ob.hide_render:
                    sparks[ob].apply(i * sparks[ob].life / e["n"])
        return 1, pose
    step = int(round(FPS / els[0]["fps"]))       # flames every frame, smoke every third (8 fps)
    return step, lambda i: stage.pose(i * step / FPS)


def render_sequence(region, kind, steps, step, pose, tmp):
    """Render `steps` frames as one EEVEE animation render (the engine stays up between frames);
    a frame-change handler poses the elements. Returns the frames as RGBA float arrays."""
    import OpenImageIO as oiio
    sc = bpy.context.scene
    r = sc.render
    res = gf.RES
    x0, y0, x1, y1 = region
    r.use_border = r.use_crop_to_border = True
    r.border_min_x, r.border_max_x = x0 / res[0], x1 / res[0]
    r.border_min_y, r.border_max_y = 1 - y1 / res[1], 1 - y0 / res[1]
    for f in tmp.glob(f"{kind}_seq_*.exr"):
        f.unlink()
    r.filepath = str(tmp / f"{kind}_seq_####")
    sc.frame_start, sc.frame_end, sc.frame_step = 0, (steps - 1) * step, step

    def handler(scene, *_):
        pose(scene.frame_current // step)
    bpy.app.handlers.frame_change_pre.append(handler)
    try:
        bpy.ops.render.render(animation=True)
    finally:
        bpy.app.handlers.frame_change_pre.remove(handler)
    out = []
    for i in range(steps):
        buf = oiio.ImageBuf(str(tmp / f"{kind}_seq_{i * step:04d}.exr"))
        out.append(np.asarray(buf.get_pixels(oiio.FLOAT)).reshape(buf.spec().height, buf.spec().width, -1))
    return out


# ---------- atlas ----------

def srgb_encode(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def write_atlas(path, img):
    """Premultiplied RGBA atlas to an 8-bit PNG, colour sRGB-encoded after dividing by `scale`, the
    99.9th percentile of the lit pixels rounded up to a quarter (at least 1). Returns scale."""
    lit = img[:, :, 3] > 0.01
    peak = float(np.percentile(img[:, :, :3][lit], 99.9)) if lit.any() else 1.0
    scale = max(1.0, math.ceil(peak * 4) / 4)
    png = np.concatenate([srgb_encode(img[:, :, :3] / scale), np.clip(img[:, :, 3:4], 0, 1)], axis=2)
    gl.write_png(path, (png * 255 + 0.5).astype(np.uint8))
    return scale


def atlas(frames, cell_scale=1.0):
    """Grid of frames; returns (rgba float atlas, cols, rows, cell w, cell h)."""
    n = len(frames)
    h, w = frames[0].shape[:2]
    best = None
    for cols in range(1, n + 1):
        rows = math.ceil(n / cols)
        aspect = (cols * w) / (rows * h)
        score = abs(math.log(aspect)) + (cols * rows - n) * 0.05
        if best is None or score < best[0]:
            best = (score, cols, rows)
    _, cols, rows = best
    scale = min(cell_scale, MAX_ATLAS / (cols * w), MAX_ATLAS / (rows * h))
    cw, ch = max(1, int(w * scale)), max(1, int(h * scale))
    if (cw, ch) != (w, h):
        import OpenImageIO as oiio
        res = []
        for f in frames:
            src = oiio.ImageBuf(np.ascontiguousarray(f.astype(np.float32)))
            dst = oiio.ImageBufAlgo.resize(src, roi=oiio.ROI(0, cw, 0, ch, 0, 1, 0, 4))
            res.append(np.asarray(dst.get_pixels(oiio.FLOAT)).reshape(ch, cw, 4))
        frames = res
    out = np.zeros((rows * ch, cols * cw, 4), np.float32)
    for i, f in enumerate(frames):
        r, c = divmod(i, cols)
        out[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw] = f
    return out, cols, rows, cw, ch


def loop(frames, n, fade):
    """Cross-fade the `fade` frames after frame n-1 into the first `fade` frames."""
    out = [f.copy() for f in frames[:n]]
    for i in range(fade):
        wgt = i / fade
        out[i] = wgt * frames[i] + (1 - wgt) * frames[i + n]
    return out


# ---------- main ----------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    location.add_argument(ap)
    ap.add_argument("--layout", default=None, help="default: the location's layout.json")
    ap.add_argument("--only", default=None, help="comma-separated element ids")
    ap.add_argument("--frames", type=int, default=None, help="override the frame count (tests)")
    ap.add_argument("--out", default=None, help="game folder to write (default: location.game_dir())")
    args = ap.parse_args(argv)
    location.use(args.location)
    out = Path(args.out) if args.out else location.game_dir()
    tmp = out / "build" / "flipbooks"
    for d in ("assets/flipbooks", "build/flipbooks"):
        (out / d).mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    plan, trace, layout, cam = gf.build(args.layout)
    srcs, _ = gf.sources()
    gf.hide_moving(srcs)
    els = elements(srcs)
    if args.only:
        keep = set(args.only.split(","))
        els = [e for e in els if e["id"] in keep]
    sc = bpy.context.scene
    setup_eevee(sc)
    stage = Stage(srcs, cam, els)
    preview = location.load("layout_preview.json")
    gains = {"flame": 2.0 ** layout["render"].get("exposure", 0.0),
             "embers": 2.0 ** layout["render"].get("exposure", 0.0),
             "smoke": 2.0 ** preview["render"].get("exposure", 0.0)}
    sky = sc.world.node_tree.nodes["Background"].inputs[1]
    view = -Vector(cam.matrix_world.to_3x3().col[2]).normalized()
    meta_path = out / "build" / "flipbooks.json"
    meta = {}
    t_build = time.time() - t0
    print(f"FLIP built in {t_build:.0f}s: {[(e['id'], e['frames']) for e in els]}")
    timing = {"build_s": round(t_build)}

    for kind in ("flame", "embers", "smoke"):
        group = [e for e in els if e["kind"] == kind]
        if not group:
            continue
        tk = time.time()
        sc.eevee.taa_render_samples = TAA[kind]
        if kind == "smoke":
            print("FLIP smoke volume range", fit_volumes(group, cam))
        stage.show([ob for e in group for ob in e["objects"]])
        stage.lighting(kind)
        sky.default_value = (preview if kind == "smoke" else layout)["environment"].get("ambient_strength", 1.0)
        gain = gains[kind]
        for e in group:
            e["n"] = args.frames or e["frames"]
            e["fade_n"] = min(e["fade"], e["n"] // 3)
        step, pose = poser(kind, group, stage)
        # probe: full frame at a few times, alpha inside each element's generous box
        boxes = {e["id"]: element_box(e, cam) for e in group}
        for i in [i for i, b in boxes.items() if b[2] <= b[0] or b[3] <= b[1]]:
            print("FLIP", i, "is outside the frame, skipped")
            del boxes[i]
        group = [e for e in group if e["id"] in boxes]
        if not group:
            continue
        hits = {e["id"]: None for e in group}
        n_all = max(e["n"] for e in group)
        for k in range(2):
            i = int(k * n_all / 2)
            pose(i)
            sc.frame_set(i * step)
            a = render_region(union(list(boxes.values())), tmp / f"probe_{kind}.exr")[:, :, 3]
            reg = union(list(boxes.values()))
            for e in group:
                m = crop(a, reg, boxes[e["id"]]) > 0.01
                hits[e["id"]] = m if hits[e["id"]] is None else hits[e["id"]] | m
        rects = {}
        for e in group:
            m, b = hits[e["id"]], boxes[e["id"]]
            if not m.any():
                print("FLIP", e["id"], "is hidden from the camera, skipped")
                continue
            ys, xs = np.nonzero(m)
            rects[e["id"]] = [max(0, b[0] + int(xs.min()) - PAD_PX), max(0, b[1] + int(ys.min()) - PAD_PX),
                              min(gf.RES[0], b[0] + int(xs.max()) + 1 + PAD_PX),
                              min(gf.RES[1], b[1] + int(ys.max()) + 1 + PAD_PX)]
        group = [e for e in group if e["id"] in rects]
        if not group:
            continue
        region = union(list(rects.values()))
        steps = max(e["n"] + e["fade_n"] for e in group)
        tf = time.time()
        # first a short run to measure, then the rest
        seq = render_sequence(region, kind, min(3, steps), step, pose, tmp)
        per = (time.time() - tf) / len(seq)
        print(f"FLIP {kind}: region {region[2] - region[0]}x{region[3] - region[1]} px, {per:.2f} s/frame "
              f"(3-frame run), {steps} frames, estimate {per * steps:.0f}s")
        tf = time.time()
        seq = render_sequence(region, kind, steps, step, pose, tmp)
        frames = {e["id"]: [] for e in group}
        for i, img in enumerate(seq):
            for e in group:
                if i < e["n"] + e["fade_n"]:
                    f = crop(img, region, rects[e["id"]]).copy()
                    f[:, :, :3] *= gain
                    frames[e["id"]].append(f)
        per_frame = (time.time() - tf) / steps
        for e in group:
            fr = loop(frames[e["id"]], e["n"], e["fade_n"]) if e["fade_n"] else frames[e["id"]][:e["n"]]
            img, cols, rows, cw, ch = atlas(fr)
            scale = write_atlas(out / "assets" / "flipbooks" / f"{e['id']}.png", img)
            ob = e["objects"][0]
            centre = (ob.matrix_world.translation if kind == "smoke" else
                      sum((o.matrix_world @ (sum((Vector(c) for c in o.bound_box), Vector()) / 8)
                           for o in e["objects"]), Vector()) / len(e["objects"]))
            x0, y0, x1, y1 = rects[e["id"]]
            meta[e["id"]] = {
                "id": e["id"], "atlas": f"assets/flipbooks/{e['id']}.png", "cols": cols, "rows": rows,
                "frames": e["n"], "fps": round(e["fps"], 4), "loop": True, "rect": [x0, y0, x1 - x0, y1 - y0],
                "cell": [cw, ch], "blend": "premul", "encoding": "srgb", "scale": scale, "depth": None,
                "depth_m": round(float((centre - cam.matrix_world.translation).dot(view)), 3),
                "group": e["group"], "kind": kind}
        timing[kind] = {"seconds": round(time.time() - tk), "frames": steps, "s_per_frame": round(per_frame, 2),
                        "region_px": [region[2] - region[0], region[3] - region[1]], "elements": len(group)}
        print(f"FLIP {kind} done: {len(group)} elements, {steps} frames, {per_frame:.2f} s/frame, "
              f"{time.time() - tk:.0f}s")
        stage.show([])
    timing["total_s"] = round(time.time() - t0)
    meta_path.write_text(json.dumps(meta, indent=1))
    (out / "build" / "flipbooks_timing.json").write_text(json.dumps(timing, indent=1))
    print(f"FLIP done in {time.time() - t0:.0f}s: {json.dumps(timing)}")


if __name__ == "__main__":
    main()

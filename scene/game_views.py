"""Zoom views of the game frame: the wide intro view, the 2x tiles around the hotspots, and the
hotspot id masks.

    B=/Applications/Blender.app/Contents/MacOS/Blender
    $B --background --python scene/game_views.py -- --view ids               # main-frame ids, ~2 min
    $B --background --python scene/game_views.py -- --view wide --samples 64  # about 16 min
    $B --background --python scene/game_views.py -- --view tiles --samples 80 # about 60 min
    add --measure to render a reduced pass and print the time estimate instead

All views use the main game camera's direction and image centre (scene/game_frame.py):

- `wide`: 2560 x 1440 over twice the main frame's width and height (half the pixel density).
- `tiles`: one 1280 x 720 main-frame-pixel rectangle around each hotspot (the screen at zoom 2),
  rendered at twice the main density, so 2560 x 1440 tile pixels. The tiles overlap, so this
  renders the union of the rectangles once, as a few border renders of the 5120 x 2880 frame that
  overlap by MARGIN main pixels, and cuts the tiles out of it. In the overlaps the regions are
  cross-faded, so the seams of the per-region denoising do not show.
- `ids`: only the main frame's id mask.

Each view is two renders of the same static scene as game_layers.py:

1. Beauty: Cycles with the same light groups, each group denoised on its own, and the same checks
   (the group sum against the combined pass, raw and denoised, and through the view transform).
2. Data: the haze box and the fog banks hidden, no bounces, a few samples. It gives depth, the camera-space normal,
   the shading roughness (wet and puddle masks) and the object index pass for the hotspot ids.
   Without the volumes no camera sample scatters before it reaches a surface, so depth and ids need
   no hole filling except behind cut-outs.

Ids: 8-bit, 0 = nothing, k = hotspot k (1-based, in hotspots.json order) where the visible surface
belongs to that hotspot's objects (location.json `hotspots`: the prop's objects, or the named object).

Writes under <out>/:

  assets/masks/ids.png                         --view ids
  assets/wide/base.exr, lg_<id>.exr, depth.f32, ids.png, puddle.png, wet.png, reference.png
  assets/tiles/<hotspot>/base.exr, lg_<id>.exr, depth.f32, ids.png, puddle.png, wet.png, reference.png
  build/view_<view>.json                       read by export_game.py
  build/views_exr/                             the raw multilayer renders

A tile lists only the light groups that reach it (REACH_LUM, REACH_PEAK). The small rest of the others is
added to the tile's base, so base + listed groups is the whole picture at rest.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scene"))

import game_frame as gf  # noqa: E402
import game_layers as gl  # noqa: E402
import location  # noqa: E402

WIDE_FACTOR = 2.0                  # the wide view covers twice the main frame's width and height
TILE_SCALE = 2                     # tile pixel density relative to the main frame
TILE_MAIN = (1280, 720)            # tile rectangle in main-frame pixels: the screen at zoom 2
MARGIN = 24                        # main-frame pixels of overlap between tile regions
REGION_WASTE = 0.12                # merge bands into one region while it adds less than this share
REACH_LUM = 2e-3                   # a group reaches a tile if its 99.9th percentile luminance is above this,
REACH_PEAK = 0.1                   # or if it lights any pixel above this (a small glow such as an oven mouth)
DATA_SAMPLES = 8
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


# ---------- scene ----------

def hotspot_ids():
    """pass_index k (1-based, hotspots.json order) on every object of hotspot k."""
    counts = {}
    for k, h in enumerate(location.table("hotspots"), 1):
        root = gf.hotspot_root(h)
        obs = [root, *root.children_recursive]
        for ob in obs:
            ob.pass_index = k
        counts[h["id"]] = sum(1 for o in obs if o.type == "MESH" and not o.hide_render)
    return counts


def tile_rects(plan, cam):
    """1280 x 720 main-frame rectangle around each hotspot's click volume, inside the frame."""
    out = []
    for h in gf.hotspots():
        c = h["volume"]["center"]                       # Godot axes
        px, py = gf.to_px(cam, (c[0], -c[2], c[1]))
        x0 = int(round(min(max(px - TILE_MAIN[0] / 2, 0), gf.RES[0] - TILE_MAIN[0])))
        y0 = int(round(min(max(py - TILE_MAIN[1] / 2, 0), gf.RES[1] - TILE_MAIN[1])))
        out.append({"id": h["id"], "hotspot": h["id"], "rect": [x0, y0, *TILE_MAIN], "center_px": [px, py]})
    return out


def union_regions(rects):
    """Cover the union of the rectangles with a few rectangles (main-frame px, x0 y0 x1 y1).

    Horizontal bands between the rectangles' edges, each band's covered span, then consecutive
    bands merged while the merge adds less than REGION_WASTE of uncovered area."""
    xs = sorted({r[0] for r in rects} | {r[0] + r[2] for r in rects})
    ys = sorted({r[1] for r in rects} | {r[1] + r[3] for r in rects})

    def covered(x, y):
        return any(r[0] <= x < r[0] + r[2] and r[1] <= y < r[1] + r[3] for r in rects)
    bands = []
    for y0, y1 in zip(ys, ys[1:]):
        cells = [(a, b) for a, b in zip(xs, xs[1:]) if covered((a + b) / 2, (y0 + y1) / 2)]
        if cells:
            bands.append([cells[0][0], y0, cells[-1][1], y1, sum((b - a) for a, b in cells) * (y1 - y0)])
    out = [bands[0]]
    for b in bands[1:]:
        c = out[-1]
        m = [min(c[0], b[0]), c[1], max(c[2], b[2]), b[3], c[4] + b[4]]
        if c[3] == b[1] and 1 - m[4] / ((m[2] - m[0]) * (m[3] - m[1])) < REGION_WASTE:
            out[-1] = m
        else:
            out.append(b)
    return [tuple(r[:4]) for r in out]


def expand(r, margin, size):
    return (max(r[0] - margin, 0), max(r[1] - margin, 0), min(r[2] + margin, size[0]), min(r[3] + margin, size[1]))


def set_border(px_rect, size):
    """Border render of a pixel rectangle (top-left origin). Blender truncates border * size."""
    r = bpy.context.scene.render
    if px_rect is None:
        r.use_border = False
        return
    x0, y0, x1, y1 = px_rect
    w, h = size
    r.use_border = True
    r.use_crop_to_border = True
    r.border_min_x, r.border_max_x = (x0 + 0.25) / w, (x1 + 0.25) / w
    r.border_min_y, r.border_max_y = (h - y1 + 0.25) / h, (h - y0 + 0.25) / h


# ---------- compositor ----------

def _tree(name):
    sc = bpy.context.scene
    ng = bpy.data.node_groups.new(name, "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    sc.compositing_node_group = ng
    sc.render.use_compositing = True
    rl = ng.nodes.new("CompositorNodeRLayers")
    out = ng.nodes.new("NodeGroupOutput")
    ng.links.new(rl.outputs["Image"], out.inputs[0])
    return ng, rl


def _file_out(ng, exr_dir, depth):
    fo = ng.nodes.new("CompositorNodeOutputFile")
    fo.directory = str(exr_dir)
    fo.file_name = "view"
    fo.format.file_format = "OPEN_EXR_MULTILAYER"
    fo.format.color_depth = depth
    fo.format.exr_codec = "ZIP"
    return fo


def beauty_compositor(groups, exr_dir):
    """Denoise each light group; write denoised and raw groups and the combined pass (half float)."""
    ng, rl = _tree("views_beauty")
    outs = {s.name: s for s in rl.outputs}
    fo = _file_out(ng, exr_dir, "16")

    def write(name, sock):
        item = fo.file_output_items.new("RGBA", name)
        ng.links.new(sock, fo.inputs[item.name])
    for g in groups:
        dn = ng.nodes.new("CompositorNodeDenoise")
        dn.inputs["HDR"].default_value = True
        ng.links.new(outs[f"Combined_{g}"], dn.inputs["Image"])
        ng.links.new(outs["Denoising Albedo"], dn.inputs["Albedo"])
        ng.links.new(outs["Denoising Normal"], dn.inputs["Normal"])
        write(f"lg_{g}", dn.outputs["Image"])
        write(f"raw_{g}", outs[f"Combined_{g}"])
    write("combined", outs["Image"])
    return fo


def data_compositor(exr_dir):
    """Depth, normal, roughness AOV and object index (full float)."""
    ng, rl = _tree("views_data")
    outs = {s.name: s for s in rl.outputs}
    fo = _file_out(ng, exr_dir, "32")
    index = next(outs[n] for n in ("IndexOB", "Object Index") if n in outs)
    for name, sock, kind in (("depth", outs["Depth"], "FLOAT"), ("normal", outs["Normal"], "VECTOR"),
                             (gl.AOV_ROUGH, outs[gl.AOV_ROUGH], "FLOAT"), ("index", index, "FLOAT")):
        item = fo.file_output_items.new(kind, name)
        ng.links.new(sock, fo.inputs[item.name])
    return fo


def render_regions(fo, regions, size, tag, reuse=False):
    """Render each pixel rectangle (or the whole frame for None); returns [(rect, exr path, seconds)]."""
    exr_dir = Path(fo.directory)
    exr_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for i, rect in enumerate(regions):
        fo.file_name = f"{tag}_{i}_"
        if not reuse:
            for f in exr_dir.glob(f"{tag}_{i}_*.exr"):
                f.unlink()
            set_border(rect, size)
            t = time.time()
            bpy.ops.render.render(write_still=False)
            dt = time.time() - t
        else:
            dt = 0.0
        exr = sorted(exr_dir.glob(f"{tag}_{i}_*.exr"))[-1]
        print(f"VIEWS {tag} region {i} {rect} {dt:.0f}s -> {exr.name}", flush=True)
        out.append((rect, exr, dt))
    set_border(None, size)
    return out


# ---------- render settings ----------

def beauty_settings(srcs, samples):
    sc = bpy.context.scene
    vl = sc.view_layers[0]
    gf.assign_light_groups(srcs)
    vl.cycles.denoising_store_passes = True
    vl.use_pass_object_index = False
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = LAYOUT["render"].get("cycles_bounces", 6)
    for ob in volumes():
        ob.hide_render = False


def data_settings(samples=DATA_SAMPLES):
    sc = bpy.context.scene
    vl = sc.view_layers[0]
    for lg in list(vl.lightgroups):
        vl.lightgroups.remove(lg)
    vl.cycles.denoising_store_passes = False
    vl.use_pass_object_index = True
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 0
    for ob in volumes():
        ob.hide_render = True


_VOLUMES = []


def volumes():
    """The visible volume-only objects of the static frame: the haze box and the fog banks."""
    if not _VOLUMES:
        _VOLUMES.extend(ob for ob in bpy.data.objects if ob.type == "MESH" and not ob.hide_render
                        and ob.data.materials and all(m and gf.volume_only(m) for m in ob.data.materials))
    return _VOLUMES


# ---------- reading and assembling ----------

def feather(h, w, m):
    """Weights that fall from 1 to near 0 over m pixels toward every edge of a region."""
    y = np.minimum(np.arange(h), np.arange(h)[::-1]) + 0.5
    x = np.minimum(np.arange(w), np.arange(w)[::-1]) + 0.5
    return np.clip(np.minimum(y[:, None], x[None, :]) / max(m, 1), 0.02, 1.0).astype(np.float32)


def assemble(parts, rect, channels, weighted):
    """Cut `rect` (x0 y0 x1 y1, render px) out of region parts [(region rect, {layer: arr})].

    weighted: cross-fade the overlaps with feather weights; else later regions overwrite."""
    x0, y0, x1, y1 = rect
    acc = {c: None for c in channels}
    wsum = np.zeros((y1 - y0, x1 - x0, 1), np.float32)
    for (rx0, ry0, rx1, ry1), L in parts:
        ix0, iy0, ix1, iy1 = max(x0, rx0), max(y0, ry0), min(x1, rx1), min(y1, ry1)
        if ix0 >= ix1 or iy0 >= iy1:
            continue
        src = (slice(iy0 - ry0, iy1 - ry0), slice(ix0 - rx0, ix1 - rx0))
        dst = (slice(iy0 - y0, iy1 - y0), slice(ix0 - x0, ix1 - x0))
        w = feather(ry1 - ry0, rx1 - rx0, MARGIN * SCALE)[src][:, :, None] if weighted else None
        for c in channels:
            a = L[c][src].astype(np.float32)
            if acc[c] is None:
                acc[c] = np.zeros((y1 - y0, x1 - x0, a.shape[2]), np.float32)
            if weighted:
                acc[c][dst] += a * w
            else:
                acc[c][dst] = a
        if weighted:
            wsum[dst] += w
        else:
            wsum[dst] = 1
    if (wsum == 0).any():
        raise SystemExit(f"rect {rect} not covered by the rendered regions")
    if weighted:
        for c in channels:
            acc[c] /= wsum
    return acc


# ---------- outputs ----------

def fill_ids(ids, holes, rounds=50):
    """Give hole pixels the most common id among their known 3x3 neighbours, growing inward."""
    ids, holes = ids.copy(), holes.copy()
    h, w = ids.shape
    values = np.unique(ids[~holes])
    for _ in range(rounds):
        if not holes.any():
            break
        pad = np.pad(np.where(holes, 255, ids), 1, constant_values=255)
        stack = np.stack([pad[1 + dy:h + 1 + dy, 1 + dx:w + 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
        best, bestc = np.zeros_like(ids), np.zeros(ids.shape, np.int16)
        for v in values:
            c = (stack == v).sum(0)
            m = c > bestc
            best[m], bestc[m] = v, c[m]
        fill = holes & (bestc > 0)
        ids[fill] = best[fill]
        holes &= ~fill
    return ids


def data_outputs(D, cam, folder, px_scale, prefix=""):
    """depth.f32, ids.png, puddle.png, wet.png from assembled data passes; returns meta."""
    maps, sky, holes, stats = gl.surface_maps(D, cam, px_scale=px_scale)
    ids = np.rint(D["index"][:, :, 0]).clip(0, 255).astype(np.uint8)
    ids = fill_ids(ids, holes)
    ids[sky] = 0
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "depth.f32").write_bytes(maps["depth"].tobytes())
    gl.write_png(folder / "ids.png", ids)
    gl.write_png(folder / "puddle.png", (maps["puddle"] * 255 + 0.5).astype(np.uint8))
    gl.write_png(folder / "wet.png", (maps["wet"] * 255 + 0.5).astype(np.uint8))
    d = maps["depth"]
    ground = d[~sky] if (~sky).any() else d
    h, w = d.shape
    hot = location.table("hotspots")
    present = {hot[k - 1]["id"]: int((ids == k).sum()) for k in np.unique(ids) if k}
    return {"depth": {"file": f"{prefix}depth.f32", "width": w, "height": h, "min_m": float(ground.min()),
                      "max_m": float(ground.max()), "sky_m": maps["far_m"], "sky_fraction": float(sky.mean())},
            "ids": f"{prefix}ids.png", "masks": {"puddle": f"{prefix}puddle.png", "wet": f"{prefix}wet.png"},
            "ids_pixels": present, "mask_stats": stats}


def beauty_outputs(B, groups, gain, folder, prefix, select):
    """base.exr, lg_<id>.exr (the groups that reach, or all), reference.png; returns meta."""
    G = {g: np.maximum(B[f"lg_{g}"][:, :, :3], 0.0) for g in groups}
    comb = B["combined"][:, :, :3]
    ck, _ = gl.checks(G, comb, B["rawsum"][:, :, :3], gain)
    reach = {}
    for g in groups[1:]:
        lum = G[g] @ LUMA * gain
        reach[g] = {"p999": float(np.percentile(lum, 99.9)), "max": float(lum.max()), "mean": float(lum.mean())}
    listed = [g for g in groups[1:] if not select or reach[g]["p999"] > REACH_LUM or reach[g]["max"] > REACH_PEAK]
    base = G["base"] + sum((G[g] for g in groups[1:] if g not in listed), np.zeros_like(G["base"]))
    folder.mkdir(parents=True, exist_ok=True)
    gl.write_exr(folder / "base.exr", base * gain)
    for g in listed:
        gl.write_exr(folder / f"lg_{g}.exr", G[g] * gain)
    gl.display_png(folder / "reference.png", sum(G.values()) * gain)
    return {"base": f"{prefix}base.exr", "groups": [{"id": g, "image": f"{prefix}lg_{g}.exr"} for g in listed],
            "reference": f"{prefix}reference.png", "group_reach": reach,
            "folded_into_base": [g for g in groups[1:] if g not in listed], "checks": ck}


def load_beauty(path, groups):
    """A beauty region as float16 {lg_<g>, combined, rawsum}."""
    L = gl.read_exr(path, keep=lambda n: n.startswith(("lg_", "raw_")) or n == "combined", dtype=np.float16)
    raw = sum(L.pop(f"raw_{g}")[:, :, :3].astype(np.float32) for g in groups)
    L["rawsum"] = raw.astype(np.float16)
    for k in list(L):
        L[k] = L[k][:, :, :3]
    return L


# ---------- main ----------

LAYOUT = {}
SCALE = 1


def main():
    global SCALE
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--view", choices=("ids", "wide", "tiles"), required=True)
    location.add_argument(ap)
    ap.add_argument("--layout", default=None, help="default: the location's layout.json")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--data-samples", type=int, default=DATA_SAMPLES)
    ap.add_argument("--out", default=None, help="game folder to write (default: location.game_dir())")
    ap.add_argument("--measure", action="store_true", help="render at half resolution and 8 samples, print estimates")
    ap.add_argument("--reuse", action="store_true", help="skip the renders, re-read build/views_exr")
    ap.add_argument("--only", default="", help="tiles: comma-separated hotspot ids")
    args = ap.parse_args(argv)
    location.use(args.location)
    out = Path(args.out) if args.out else location.game_dir()
    exr_dir = out / "build" / "views_exr"
    t0 = time.time()

    plan, trace, layout, cam = gf.build(args.layout)
    LAYOUT.update(layout)
    srcs, _ = gf.sources()
    gf.hide_moving(srcs)
    groups = gf.assign_light_groups(srcs)
    n_ids = hotspot_ids()
    gl.add_rough_aov()
    exposure = gl.setup_render(layout, args.samples, 100)
    gain = 2.0 ** exposure
    sc = bpy.context.scene
    # persistent data would keep the BVH between the region renders, but it ended a full-size
    # render in a Metal GPU fault here; the BVH build is small next to a region's render
    sc.render.use_persistent_data = False
    rects = tile_rects(plan, cam)
    if args.only:
        rects = [r for r in rects if r["id"] in args.only.split(",")]
    print(f"VIEWS built in {time.time() - t0:.0f}s: groups {groups}, hotspot objects {n_ids}", flush=True)

    if args.view == "ids":
        size, regions, SCALE = gf.RES, [None], 1
    elif args.view == "wide":
        cam.data.ortho_scale = gf.width_m() * WIDE_FACTOR
        size, regions, SCALE = gf.RES, [None], 1
    else:
        SCALE = TILE_SCALE
        size = (gf.RES[0] * SCALE, gf.RES[1] * SCALE)
        main_regions = union_regions([r["rect"] for r in rects])
        regions = [tuple(c * SCALE for c in expand(r, MARGIN, gf.RES)) for r in main_regions]
        px = sum((r[2] - r[0]) * (r[3] - r[1]) for r in regions)
        print(f"VIEWS tile regions (main px) {main_regions}; {px / 1e6:.2f} Mpx at x{SCALE} "
              f"= {px / (gf.RES[0] * gf.RES[1]):.2f} main frames", flush=True)
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.resolution_percentage = 100

    if args.measure:
        # warm-up: kernels and BVH, then the data pass for real and the beauty pass at half size, 8 samples
        data_settings(1)
        sc.render.resolution_percentage = 10
        fo = data_compositor(exr_dir / "measure")
        t = time.time()
        render_regions(fo, regions[:1], size, "warm")
        print(f"VIEWS warm-up {time.time() - t:.0f}s", flush=True)
        sc.render.resolution_percentage = 100
        data_settings(args.data_samples)
        t = time.time()
        render_regions(fo, regions, size, "data")
        t_data = time.time() - t
        beauty_settings(srcs, 8)
        fo = beauty_compositor(groups, exr_dir / "measure")
        sc.render.resolution_percentage = 50
        t = time.time()
        res = render_regions(fo, regions, size, "beauty")
        t_b = time.time() - t
        est = {s: t_b * 4 * s / 8 for s in (32, 48, 64, 96, 128)}
        print(f"VIEWS MEASURE {args.view}: data pass {t_data:.0f}s at {args.data_samples} spp; beauty at 50% "
              f"and 8 spp {t_b:.0f}s ({[round(r[2]) for r in res]}); full-size estimates (incl. denoise) "
              + ", ".join(f"{s} spp {v / 60:.0f} min" for s, v in est.items()), flush=True)
        return

    # 1. data pass
    data_settings(args.data_samples)
    fo = data_compositor(exr_dir)
    t = time.time()
    dres = render_regions(fo, regions, size, f"{args.view}_data", args.reuse)
    t_data = time.time() - t
    dparts = [((r or (0, 0, *size)), gl.read_exr(p, keep=lambda n: n in ("depth", "normal", gl.AOV_ROUGH, "index")))
              for r, p, _ in dres]
    if args.view == "ids":
        D = assemble(dparts, (0, 0, *size), ("depth", "normal", gl.AOV_ROUGH, "index"), False)
        maps, sky, holes, _ = gl.surface_maps(D, cam)
        ids = fill_ids(np.rint(D["index"][:, :, 0]).clip(0, 255).astype(np.uint8), holes)
        ids[sky] = 0
        gl.write_png(out / "assets" / "masks" / "ids.png", ids)
        meta = {"ids": "assets/masks/ids.png", "data_seconds": round(t_data), "data_samples": args.data_samples,
                "ids_pixels": {location.table("hotspots")[k - 1]["id"]: int((ids == k).sum())
                               for k in np.unique(ids) if k},
                "hotspot_objects": n_ids}
        (out / "build" / "view_ids.json").write_text(json.dumps(meta, indent=1))
        print(f"VIEWS ids done in {time.time() - t0:.0f}s: {meta['ids_pixels']}")
        return

    # 2. beauty pass
    beauty_settings(srcs, args.samples)
    fo = beauty_compositor(groups, exr_dir)
    t = time.time()
    bres = render_regions(fo, regions, size, f"{args.view}_beauty", args.reuse)
    t_beauty = time.time() - t
    print(f"VIEWS rendered: data {t_data:.0f}s, beauty {t_beauty:.0f}s", flush=True)
    bparts = [((r or (0, 0, *size)), load_beauty(p, groups)) for r, p, _ in bres]
    bchan = [f"lg_{g}" for g in groups] + ["combined", "rawsum"]
    timing = {"data_seconds": round(t_data), "beauty_seconds": round(t_beauty), "samples": args.samples,
              "data_samples": args.data_samples, "regions": [list(r) if r else None for r in regions],
              "region_seconds": [round(r[2]) for r in bres]}

    if args.view == "wide":
        folder = out / "assets" / "wide"
        D = assemble(dparts, (0, 0, *size), ("depth", "normal", gl.AOV_ROUGH, "index"), False)
        dm = data_outputs(D, cam, folder, 1.0 / WIDE_FACTOR, "assets/wide/")
        B = assemble(bparts, (0, 0, *size), bchan, False)
        bm = beauty_outputs(B, groups, gain, folder, "assets/wide/", select=False)
        meta = {"camera": gf.camera_block(cam, trace, gf.RES, gf.width_m() * WIDE_FACTOR), **bm, **dm,
                "render": timing}
        (out / "build" / "view_wide.json").write_text(json.dumps(meta, indent=1))
    else:
        tiles = []
        for r in rects:
            x0, y0, w, h = r["rect"]
            prect = (x0 * SCALE, y0 * SCALE, (x0 + w) * SCALE, (y0 + h) * SCALE)
            folder = out / "assets" / "tiles" / r["id"]
            prefix = f"assets/tiles/{r['id']}/"
            D = assemble(dparts, prect, ("depth", "normal", gl.AOV_ROUGH, "index"), False)
            dm = data_outputs(D, cam, folder, SCALE, prefix)
            del D
            B = assemble(bparts, prect, bchan, True)
            bm = beauty_outputs(B, groups, gain, folder, prefix, select=True)
            del B
            tiles.append({"id": r["id"], "hotspot": r["hotspot"], "rect": r["rect"], "scale": SCALE,
                          "base": bm["base"], "groups": bm["groups"], "depth": dm["depth"]["file"],
                          "ids": dm["ids"], "masks": dm["masks"], "reference": bm["reference"],
                          "depth_meta": dm["depth"], "ids_pixels": dm["ids_pixels"],
                          "group_reach": bm["group_reach"], "folded_into_base": bm["folded_into_base"],
                          "checks": bm["checks"], "mask_stats": dm["mask_stats"]})
            print(f"VIEWS tile {r['id']} {r['rect']}: groups {[g['id'] for g in bm['groups']]}, "
                  f"display p99 {bm['checks']['display_8bit_vs_combined']['p99']}", flush=True)
        prev = out / "build" / "view_tiles.json"
        if args.only and prev.exists():
            old = {t["id"]: t for t in json.loads(prev.read_text())["tiles"]}
            old.update({t["id"]: t for t in tiles})
            tiles = [old[r["id"]] for r in tile_rects(plan, cam) if r["id"] in old]
        meta = {"tiles": tiles, "render": timing, "margin_main_px": MARGIN, "reach_lum": REACH_LUM}
        prev.write_text(json.dumps(meta, indent=1))
    print(f"VIEWS {args.view} done in {time.time() - t0:.0f}s: {json.dumps(timing)}")


if __name__ == "__main__":
    main()

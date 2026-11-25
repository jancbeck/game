"""Render the static game frame in Cycles, split into light groups, with depth and surface masks.

    /Applications/Blender.app/Contents/MacOS/Blender --background --python scene/game_layers.py -- \
        [--location courtyard] [--percent 100] [--samples 128] [--out game]

Builds the static scene of game_frame.py at the 2560 x 1440 game camera and renders it once in
Cycles with one light group per flickering source. The compositor denoises every light-group pass
on its own (Cycles denoises only the combined pass) and writes them, with the raw passes, to
build/layers.exr. Then this script writes, under <out>/:

  assets/layers/base.exr          everything static: sky, moon and haze (half float, RGB)
  assets/layers/lg_<id>.exr       one light group each: direct and indirect light of the source,
                                  its flames' reflections and its own glow (half float, RGB)
  assets/layers/reference.png     Blender's display transform of base + all groups
  assets/layers/reference_post.png the same with the compositor post (bloom, grade, vignette)
  assets/depth.f32, depth_preview.png
  assets/masks/puddle.png, wet.png, normal.png
  build/layers.json               the group list and the checks, read by export_game.py

The EXRs are scene-linear Rec.709 with the scene's exposure already multiplied in, so
base + sum(groups) through AgX with the scene's look is the picture.

Haze. The haze box is static, so it is in the frame: the sky and moon light it scatters is in
`base` and the firelight it scatters is in each fire's group, which flickers with the fire.
The ground mist is not in the frame (game_frame.HIDDEN_PROPS); it is a flipbook.
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
import location  # noqa: E402

AOV_ROUGH = "rough"
LOOK = "AgX - Punchy"
VIEW = "AgX"


# ---------- render setup ----------

def add_rough_aov():
    """Shader AOV `rough`: the roughness every Principled BSDF uses (water and wet film are smooth)."""
    n = 0
    for mat in bpy.data.materials:
        if not mat.use_nodes or not mat.node_tree:
            continue
        nt = mat.node_tree
        bsdf = next((x for x in nt.nodes if x.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None or nt.nodes.get("game_aov_rough"):
            continue
        aov = nt.nodes.new("ShaderNodeOutputAOV")
        aov.name = "game_aov_rough"
        aov.aov_name = AOV_ROUGH
        sock = bsdf.inputs["Roughness"]
        if sock.is_linked:
            nt.links.new(sock.links[0].from_socket, aov.inputs["Value"])
        else:
            aov.inputs["Value"].default_value = sock.default_value
        n += 1
    return n


def setup_render(layout, samples, percent):
    sc = bpy.context.scene
    vl = sc.view_layers[0]
    vl.use_pass_z = True
    vl.use_pass_normal = True
    vl.cycles.denoising_store_passes = True
    aov = vl.aovs.add()
    aov.name, aov.type = AOV_ROUGH, "VALUE"
    sc.render.engine = "CYCLES"
    sc.render.resolution_percentage = percent
    sc.render.film_transparent = False
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    spec = layout["render"]
    sc.cycles.device = "GPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = spec.get("cycles_bounces", 6)
    sc.cycles.volume_bounces = 1
    sc.cycles.volume_step_rate = spec.get("cycles_volume_step", 4.0)
    sc.cycles.light_sampling_threshold = 0.01
    sc.view_settings.view_transform = VIEW
    sc.view_settings.look = LOOK
    sc.view_settings.exposure = spec.get("exposure", 0.0)
    return spec.get("exposure", 0.0)


def setup_compositor(groups, exr_dir, post):
    """Denoise each light group and write everything to one multilayer EXR; post chain to a PNG."""
    import build_scene as bs
    sc = bpy.context.scene
    # the look of the main still: the scene's post chain, to the group output (reference_post.png)
    bs.setup_post(post)
    ng = sc.compositing_node_group
    sc.render.use_compositing = True
    nodes, links = ng.nodes, ng.links
    rl = nodes.new("CompositorNodeRLayers")
    outs = {s.name: s for s in rl.outputs}
    fo = nodes.new("CompositorNodeOutputFile")
    fo.directory = str(exr_dir)
    fo.file_name = "layers"
    fo.format.file_format = "OPEN_EXR_MULTILAYER"
    fo.format.color_depth = "32"
    fo.format.exr_codec = "ZIP"

    def write(name, sock, kind="RGBA"):
        item = fo.file_output_items.new(kind, name)
        links.new(sock, fo.inputs[item.name])

    albedo, normal = outs["Denoising Albedo"], outs["Denoising Normal"]
    for g in groups:
        dn = nodes.new("CompositorNodeDenoise")
        dn.inputs["HDR"].default_value = True
        links.new(outs[f"Combined_{g}"], dn.inputs["Image"])
        links.new(albedo, dn.inputs["Albedo"])
        links.new(normal, dn.inputs["Normal"])
        write(f"lg_{g}", dn.outputs["Image"])
        write(f"raw_{g}", outs[f"Combined_{g}"])
    write("combined", outs["Image"])
    write("depth", outs["Depth"], "FLOAT")
    write("normal", outs["Normal"], "VECTOR")
    write(AOV_ROUGH, outs[AOV_ROUGH], "FLOAT")
    write("albedo", albedo)



# ---------- reading and writing ----------

def read_exr(path, keep=None, dtype=np.float32):
    """Layers of a multilayer EXR as {layer: HxWxC array}, row 0 at the top; `keep(layer)` filters,
    `dtype` stores."""
    import OpenImageIO as oiio
    inp = oiio.ImageInput.open(str(path))
    if inp is None:
        raise SystemExit(f"cannot open {path}: {oiio.geterror()}")
    out = {}
    k = 0
    while inp.seek_subimage(k, 0):
        spec = inp.spec()
        names = list(spec.channelnames)
        layers = {}
        for i, n in enumerate(names):
            layer, _, ch = n.rpartition(".")
            layers.setdefault(layer or n, []).append((ch, i))
        if keep is None or any(keep(x) for x in layers):
            px = np.asarray(inp.read_image(k, 0, 0, len(names), "float"), np.float32)
            px = px.reshape(spec.height, spec.width, len(names))
            for layer, chs in layers.items():
                if keep is not None and not keep(layer):
                    continue
                order = sorted(chs, key=lambda c: "RGBAXYZV".find(c[0][-1:]) if c[0][-1:] in "RGBAXYZV" else 9)
                out[layer] = px[:, :, [i for _, i in order]].astype(dtype)
            del px
        k += 1
    inp.close()
    return out


def write_exr(path, rgb):
    import OpenImageIO as oiio
    h, w, _ = rgb.shape
    spec = oiio.ImageSpec(w, h, 3, oiio.HALF)
    spec.channelnames = ("R", "G", "B")
    spec.attribute("compression", "zip")
    out = oiio.ImageOutput.create(str(path))
    out.open(str(path), spec)
    out.write_image(np.ascontiguousarray(rgb.astype(np.float16)))
    out.close()


def write_png(path, arr):
    """8-bit PNG of the array as given. RGBA is written literally: PNG readers take alpha as
    unassociated, so OpenImageIO would otherwise divide premultiplied colour by alpha on write."""
    import OpenImageIO as oiio
    a = np.ascontiguousarray(arr)
    if a.ndim == 2:
        a = a[:, :, None]
    h, w, c = a.shape
    spec = oiio.ImageSpec(w, h, c, oiio.UINT8)
    if c == 4:
        spec.attribute("oiio:UnassociatedAlpha", 1)
    out = oiio.ImageOutput.create(str(path))
    out.open(str(path), spec)
    out.write_image(a)
    out.close()


def display_png(path, rgb, exposure=0.0):
    """Save scene-linear RGB through the scene's view transform and look (Blender's own colour management)."""
    sc = bpy.context.scene
    h, w, _ = rgb.shape
    img = bpy.data.images.new("game_ref", w, h, float_buffer=True, alpha=True)
    img.colorspace_settings.name = "Linear Rec.709"
    rgba = np.ones((h, w, 4), np.float32)
    rgba[:, :, :3] = rgb
    img.pixels.foreach_set(rgba[::-1].ravel())     # Blender images start at the bottom row
    vs = sc.view_settings
    saved = (vs.exposure, sc.render.image_settings.file_format, sc.render.image_settings.color_depth)
    vs.exposure = exposure
    st = sc.render.image_settings
    if hasattr(st, "media_type"):
        st.media_type = "IMAGE"
    st.file_format = "PNG"
    st.color_mode = "RGB"
    st.color_depth = "8"
    img.save_render(str(path), scene=sc)
    vs.exposure = saved[0]
    bpy.data.images.remove(img)


def display_array(rgb, exposure=0.0):
    """The display-referred 8-bit image of scene-linear RGB, read back from Blender's PNG."""
    import OpenImageIO as oiio
    tmp = Path(bpy.app.tempdir or "/tmp") / "game_display_tmp.png"
    display_png(tmp, rgb, exposure)
    return np.asarray(oiio.ImageBuf(str(tmp)).get_pixels(oiio.UINT8))


def checks(G, comb, raw_total, gain):
    """The light-group sum against Cycles' combined pass: raw and denoised, and through the view transform."""
    def err(a, b):
        d = np.abs(a - b)
        return {"mean_abs": float(d.mean()), "p99_abs": float(np.percentile(d, 99)), "max_abs": float(d.max()),
                "mean_rel": float(d.sum() / max(np.abs(b).sum(), 1e-9))}
    total = sum(G.values())
    out = {"raw_sum_vs_combined": err(raw_total, comb), "denoised_sum_vs_combined": err(total, comb)}
    ref8 = display_array(total * gain)
    comb8 = display_array(comb * gain)
    d8 = np.abs(ref8.astype(np.int16) - comb8.astype(np.int16))
    out["display_8bit_vs_combined"] = {"mean": float(d8.mean()), "p99": float(np.percentile(d8, 99)),
                                       "max": int(d8.max()), "share_over_4": float((d8 > 4).mean())}
    return out, d8


# ---------- depth and masks ----------

def fill_holes(a, holes, sky, rounds=50):
    """Replace `holes` pixels by the median of their valid 3x3 neighbours, growing inward."""
    a, holes = a.copy(), holes.copy()
    h, w = a.shape
    for _ in range(rounds):
        if not holes.any():
            break
        zz = np.where(holes | sky, np.nan, a)
        pad = np.pad(zz, 1, constant_values=np.nan)
        stack = np.stack([pad[1 + dy:h + 1 + dy, 1 + dx:w + 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
        with np.errstate(all="ignore"):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                med = np.nanmedian(stack, axis=0)
        fill = holes & ~np.isnan(med)
        a[fill] = med[fill]
        holes &= ~fill
    return a


def blur(a, sigma):
    """Separable gaussian blur of a 2D array (sigma in pixels)."""
    r = int(3 * sigma + 0.5)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    a = np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode="edge"), k, "valid"), 0, a)
    return np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode="edge"), k, "valid"), 1, a)


def surface_maps(L, cam, near=1.0, far=200.0, px_scale=1.0):
    """Depth, camera-space normal, wet and puddle masks from the data passes of one render.

    `px_scale` is the pixel density relative to the main frame: the mask blurs scale with it, so
    a mask covers the same metres at every zoom. Returns (arrays, sky mask, stats)."""
    z = L["depth"][:, :, 0].copy()
    nw = L["normal"][:, :, :3]
    # Cycles writes the depth of one sample; where that sample went through a cut-out (leaves, straw)
    # the pixel reads as sky although the normal pass saw a surface: fill those from their neighbours
    sky = (z > 1e3) & (np.linalg.norm(nw, axis=2) < 0.05)
    holes = (z > 1e3) & ~sky
    n_holes = int(holes.sum())
    z = fill_holes(z, holes, sky)
    far_m = far * 0.98
    d = np.where(sky, far_m, np.clip(z, near, far_m)).astype("<f4")

    # camera-space normal: Cycles' normal pass is in world space
    R = np.array(cam.matrix_world.to_3x3().normalized())          # columns: camera x, y, z in world
    nc = nw @ R                                                   # world -> camera
    nc /= np.maximum(np.linalg.norm(nc, axis=2, keepdims=True), 1e-6)
    nc[sky] = (0, 0, 1)

    # wet and puddle from the shading roughness and the world normal
    # samples that scatter in the haze write no AOV and no normal: divide by the normal pass's
    # length, which is the share of samples that reached a surface
    cover = np.linalg.norm(nw, axis=2)
    rough = L[AOV_ROUGH][:, :, 0] / np.maximum(cover, 1e-3)
    rough = fill_holes(rough, (cover < 0.3) & ~sky, sky)
    up = nw[:, :, 2] / np.maximum(cover, 1e-3)
    wet = np.clip((0.65 - rough) / 0.5, 0, 1)
    wet[sky] = 0
    wet = blur(wet, 1.0 * px_scale)
    puddle = blur(np.clip((0.085 - rough) / 0.04, 0, 1) * np.clip((up - 0.85) / 0.1, 0, 1), 1.5 * px_scale)
    puddle[sky] = 0
    stats = {"depth_holes_filled": n_holes, "puddle_fraction": float((puddle > 0.5).mean()), "wet_mean": float(wet.mean()),
             "rough_hist": np.histogram(rough[~sky], bins=10, range=(0, 1))[0].tolist()}
    return {"depth": d, "normal": nc, "wet": wet, "puddle": puddle, "far_m": far_m}, sky, holes, stats


def depth_and_masks(L, cam, out, near=1.0, far=200.0):
    m, sky, _, stats = surface_maps(L, cam, near, far)
    d = m["depth"]
    h, w = d.shape
    (out / "assets" / "depth.f32").write_bytes(d.tobytes())
    ground = d[~sky]
    lo, hi = float(ground.min()), float(ground.max())
    prev = np.clip((d - lo) / (hi - lo), 0, 1)
    write_png(out / "assets" / "depth_preview.png", ((1 - prev) * 255).astype(np.uint8))
    write_png(out / "assets" / "masks" / "normal.png", np.clip((m["normal"] * 0.5 + 0.5) * 255 + 0.5, 0, 255).astype(np.uint8))
    write_png(out / "assets" / "masks" / "wet.png", (m["wet"] * 255 + 0.5).astype(np.uint8))
    write_png(out / "assets" / "masks" / "puddle.png", (m["puddle"] * 255 + 0.5).astype(np.uint8))
    meta = {"_doc": "depth.f32: float32 little-endian, width*height, row 0 = top. Metres along the camera "
                    "axis from the camera origin (orthographic). Sky pixels hold sky_m.",
            "file": "assets/depth.f32", "width": w, "height": h, "min_m": lo, "max_m": hi, "sky_m": m["far_m"],
            "sky_fraction": float(sky.mean())}
    return meta, stats


# ---------- main ----------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    location.add_argument(ap)
    ap.add_argument("--layout", default=None, help="default: the location's layout.json")
    ap.add_argument("--samples", type=int, default=None)
    ap.add_argument("--percent", type=int, default=100)
    ap.add_argument("--out", default=None, help="game folder to write (default: location.game_dir())")
    ap.add_argument("--reuse", action="store_true", help="skip the render, re-read build/layers.exr")
    args = ap.parse_args(argv)
    location.use(args.location)
    out = Path(args.out) if args.out else location.game_dir()
    for d in ("assets/layers", "assets/masks", "build"):
        (out / d).mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    plan, trace, layout, cam = gf.build(args.layout)
    srcs, summary = gf.sources()
    hidden = gf.hide_moving(srcs)
    groups = gf.assign_light_groups(srcs)
    n_aov = add_rough_aov()
    samples = args.samples or layout["render"].get("cycles_samples", 128)
    exposure = setup_render(layout, samples, args.percent)
    exr_dir = out / "build" / "layers_exr"
    setup_compositor(groups, exr_dir, layout.get("post", {}))
    print(f"LAYERS built in {time.time() - t0:.0f}s: {len(groups)} groups {groups}, {n_aov} AOV materials, "
          f"{len(hidden)} hidden objects, anim {summary}")

    t1 = time.time()
    post_png = out / "assets" / "layers" / "reference_post.png"
    if not args.reuse:
        for f in exr_dir.glob("layers*.exr"):
            f.unlink()
        sc = bpy.context.scene
        sc.render.filepath = str(post_png)
        st = sc.render.image_settings
        if hasattr(st, "media_type"):
            st.media_type = "IMAGE"
        st.file_format = "PNG"
        bpy.ops.render.render(write_still=True)
    t_render = time.time() - t1
    exr = sorted(exr_dir.glob("layers*.exr"))[-1]
    L = read_exr(exr)
    print("LAYERS read", exr, sorted(L))

    gain = 2.0 ** exposure
    comb = L["combined"][:, :, :3]
    G = {g: np.maximum(L[f"lg_{g}"][:, :, :3], 0.0) for g in groups}
    total = sum(G.values())
    raw_total = sum(L[f"raw_{g}"][:, :, :3] for g in groups)
    ck, d8 = checks(G, comb, raw_total, gain)
    ck = {"raw_groups_vs_noisy_combined_identity": "Cycles combined is denoised; raw groups are not", **ck}
    print("LAYERS checks", json.dumps(ck, indent=1))

    lay = out / "assets" / "layers"
    write_exr(lay / "base.exr", G["base"] * gain)
    for g in groups[1:]:
        write_exr(lay / f"lg_{g}.exr", G[g] * gain)
    display_png(lay / "reference.png", total * gain)
    display_png(out / "build" / "combined_blender.png", comb * gain)
    write_png(out / "build" / "diff_ref_vs_combined_x10.png", np.clip(d8 * 10, 0, 255).astype(np.uint8))
    depth_meta, mask_stats = depth_and_masks(L, cam, out)

    by_id = {d["id"]: d for d in srcs}
    meta = {
        "color_space": "linear Rec.709, scene-referred, exposure already applied",
        "view_transform": VIEW, "look": LOOK, "exposure_applied_ev": exposure,
        "post": layout.get("post", {}),
        "base": "assets/layers/base.exr",
        "groups": [{"id": g, "image": f"assets/layers/lg_{g}.exr", "curve": by_id[g]["kind"],
                    "seed": by_id[g]["seed"], "prop": by_id[g]["key"],
                    "anchor_blender": list(gf.anchor(by_id[g]))} for g in groups[1:]],
        "reference": "assets/layers/reference.png",
        "reference_post": "assets/layers/reference_post.png",
        "depth": depth_meta, "mask_stats": mask_stats, "checks": ck,
        "render": {"samples": samples, "percent": args.percent, "seconds": round(t_render),
                   "resolution": [comb.shape[1], comb.shape[0]], "exr": str(exr)},
    }
    (out / "build" / "layers.json").write_text(json.dumps(meta, indent=1))
    print(f"LAYERS done in {time.time() - t0:.0f}s (render {t_render:.0f}s)")


if __name__ == "__main__":
    main()

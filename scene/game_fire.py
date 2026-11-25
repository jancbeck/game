"""Fire flipbooks from Mantaflow fire simulations, rendered in EEVEE at the game camera.

    /Applications/Blender.app/Contents/MacOS/Blender --background --python scene/game_fire.py -- \
        [--location courtyard] [--only fire_basket,...] [--out game] [--frames 72] [--quick] [--bake-only] [--reuse]

--bake-only runs the simulations without touching the GPU; --reuse renders from earlier bakes whose
settings match (build/fire/cache_<fire>/stamp.json), so a look change costs about 2 minutes.

Builds the static scene of game_frame.py once. For every open fire in location.json `fires` it bakes a gas
simulation (fuel and smoke) whose emitter is the fire's own fuel (coals, logs, torch head, oven
coal bed), with a light wind that gusts like anim.gust() and, for the oven, the chamber walls
and roof as colliders. Then it renders the baked grids (the cache's VDB files as a Volume object) in EEVEE at twice the game frame's pixel density, with every
static object as a holdout, and writes two flipbooks per fire in the flipbook format of the game-export skill:

  assets/flipbooks/<fire>_flame.png      main frame density (the 2x render, averaged 2 x 2)
  assets/flipbooks/<fire>_flame@2.png    2x density, for the zoom tiles
  build/fire_flipbooks.json              the entries, merged by export_game.py

Look. The volume shader turns the simulation's `flame` field into a temperature (TEMP_K) and
takes the colour from Blender's blackbody node, so the flame runs from deep orange-red at the edges
to orange in the hottest core. The temperatures stay low on purpose: the view transform turns a
bright, yellow emission white, and a flame that is white in the middle reads as cold. Emission
grows with flame^EMIT_POW, a steep stand-in for the T^4 law. Smoke is the simulation's `density`,
dark grey, absorbing only. Both fade out before the
domain walls, so the box never shows.

Light. Flames only emit. Frames are rendered without lights or sky, the Cycles exposure of
layout.json is multiplied in, and each fire is scaled so that its brightest pixels (99.5th
percentile of the flame's luminance, before the exposure) sit at `peak`.
The runtime multiplies the flipbook by its light group's intensity, so `group` is the fire's id.

Loop. A simulation is not periodic. After `WARMUP` frames, `frames + fade + search` frames are
rendered; the loop start is the offset within `search` where the frames `frames` later look most
alike, and the last `fade` frames are cross-faded (smootherstep) into the first ones.
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
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scene"))

import anim  # noqa: E402
import location  # noqa: E402

FPS = 24
WARMUP = 30            # frames before the fire has reached its height and the first smoke has left
TEMP_K = (1250.0, 2000.0)   # temperature at flame 0 and 1: deep orange-red at the rim, orange in the core
EMIT_POW = 1.6
SMOKE_DENSITY = 150.0   # absorption per metre per unit of the simulation's smoke density
EDGE = (0.06, 0.22)      # flame values over which a tongue's rim goes from clear to lit
CELL_RATE_S = 2.8e-6   # measured bake seconds per cell per frame (M1 Pro, gas with fire)


# ---------- simulation ----------

def _copy_evaluated(ob, name):
    """A hidden copy of an object's evaluated mesh (modifiers applied) at its world transform."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    cp = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(cp)
    cp.matrix_world = ob.matrix_world.copy()
    cp.hide_render = True
    cp.visible_shadow = False
    return cp


def _bbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def _unit_box(name):
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def domain_box(spec, fuel_objs):
    """World corners (low, high) of a fire's simulation domain."""
    lo, hi = _bbox(fuel_objs)
    px0, px1, py0, py1 = spec["pad"]
    z0 = (spec["emit_from"] or lo.z) - spec["below"]
    return (Vector((lo.x - px0, lo.y - py0, z0)),
            Vector((hi.x + px1, hi.y + py1, hi.z + spec["height"])))


def chamber_walls(fid, coals, height, lo_d, hi_d):
    """Closed boxes (one object each: overlapping boxes in one mesh confuse the inside test) around an oven chamber over a coal bed (assets/_shed_hearth.oven): left and right
    walls, back wall and roof, the roof running out to the facade. Separate closed boxes, because
    the boolean-cut dome is not a clean solid for the collider test."""
    import bmesh
    (x0, y0, z0), (x1, y1, z1) = _bbox([coals])
    mw, md = (x1 - x0) + 0.04, (y1 - y0) + 0.10
    cx = (x0 + x1) / 2
    y_front = (y0 + y1) / 2 - md / 2 - 0.05
    floor = z0 + 0.01
    top = floor + height
    t = 0.3
    big_lo, big_hi = lo_d - Vector((t, t, t)), hi_d + Vector((t, t, t))
    boxes = [((big_lo.x, y_front, floor - t), (cx - mw / 2, big_hi.y, big_hi.z)),          # left wall
             ((cx + mw / 2, y_front, floor - t), (big_hi.x, big_hi.y, big_hi.z)),          # right wall
             ((big_lo.x, y_front + md, floor - t), (big_hi.x, big_hi.y, big_hi.z)),        # back
             ((big_lo.x, y_front, top), (big_hi.x, big_hi.y, big_hi.z))]                   # roof and facade
    obs = []
    for i, (lo, hi) in enumerate(boxes):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        lo, hi = Vector(lo), Vector(hi)
        bmesh.ops.scale(bm, vec=hi - lo, verts=bm.verts)
        bmesh.ops.translate(bm, vec=(lo + hi) / 2, verts=bm.verts)
        me = bpy.data.meshes.new(f"fire_chamber_{fid}_{i}")
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(f"fire_chamber_{fid}_{i}", me)
        bpy.context.scene.collection.objects.link(ob)
        ob.hide_render = True
        obs.append(ob)
    return obs


def build_sim(fid, spec, fuel_objs, colliders, cache, n_frames):
    """Domain, emitters, colliders and wind of one fire; returns (domain, cell count, all objects)."""
    lo_d, hi_d = domain_box(spec, fuel_objs)
    size = hi_d - lo_d
    dom = _unit_box(f"fire_domain_{fid}")
    objs = [dom]
    dom.location = (lo_d + hi_d) / 2
    dom.scale = size
    dom.visible_shadow = False
    mod = dom.modifiers.new("fluid", "FLUID")
    mod.fluid_type = "DOMAIN"
    ds = mod.domain_settings
    ds.domain_type = "GAS"
    ds.resolution_max = int(math.ceil(max(size) / spec["voxel"]))
    ds.cache_directory = str(cache)
    ds.cache_type = "ALL"
    ds.cache_frame_start, ds.cache_frame_end = 1, n_frames
    ds.use_adaptive_domain = False
    for side in ("front", "back", "right", "left", "top"):
        setattr(ds, f"use_collision_border_{side}", False)
    ds.use_collision_border_bottom = True
    ds.alpha = -0.1
    ds.beta = spec["beta"]
    ds.vorticity = spec["vort"]
    ds.burning_rate = spec["burn"]
    ds.flame_smoke = spec["smoke"]
    ds.flame_vorticity = spec["flame_vort"]
    ds.flame_ignition = 1.25
    ds.flame_max_temp = 3.0
    ds.flame_smoke_color = (0.10, 0.095, 0.09)
    ds.use_dissolve_smoke = True
    ds.dissolve_speed = 30
    cells = ds.resolution_max ** 3 * (size.x * size.y * size.z) / max(size) ** 3

    tex = bpy.data.textures.new(f"fuel_noise_{fid}", "CLOUDS")
    tex.noise_scale = spec["noise"]
    tex.noise_depth = 0
    parts = [_copy_evaluated(src, f"fire_fuel_{fid}_{i}") for i, src in enumerate(fuel_objs)]
    for pt in parts:
        # Mantaflow's mesh emission finds no cells for a box whose faces are axis-aligned (an oven's
        # coal bed); a tilt of under two degrees fixes that
        c = sum((Vector(v.co) for v in pt.data.vertices), Vector()) / max(1, len(pt.data.vertices))
        rot = Matrix.Rotation(0.03, 4, "X") @ Matrix.Rotation(0.03, 4, "Y")
        pt.data.transform(Matrix.Translation(c) @ rot @ Matrix.Translation(-c))
    em = parts[0]
    if len(parts) > 1:
        with bpy.context.temp_override(active_object=em, object=em, selected_objects=parts,
                                       selected_editable_objects=parts):
            bpy.ops.object.join()
    objs.append(em)
    f = em.modifiers.new("fluid", "FLUID")
    f.fluid_type = "FLOW"
    fs = f.flow_settings
    fs.flow_type = "BOTH"
    fs.flow_behavior = "INFLOW"
    fs.flow_source = "MESH"
    fs.surface_distance = spec.get("surf", 0.6 * spec["voxel"] + 0.01)
    fs.fuel_amount = spec["fuel"]
    fs.density = 0.12
    fs.smoke_color = (0.1, 0.1, 0.1)
    fs.temperature = 1.0
    fs.use_texture = True
    fs.noise_texture = tex
    fs.texture_map_type = "AUTO"
    fs.texture_size = 1.0
    # the noise slides through the fuel, so the hot spots wander and the tongues break up
    for fr, off in ((1, 0.0), (n_frames, n_frames / FPS * 0.8)):
        fs.texture_offset = off
        fs.keyframe_insert("texture_offset", frame=fr)
    if spec.get("chamber"):
        colliders = list(colliders) + chamber_walls(fid, fuel_objs[0], spec["chamber"], lo_d, hi_d)
    for ob in colliders:
        c = ob if ob.name.startswith("fire_chamber") else _copy_evaluated(ob, f"fire_collider_{fid}_{ob.name}")
        e = c.modifiers.new("fluid", "FLUID")
        e.fluid_type = "EFFECTOR"
        e.effector_settings.effector_type = "COLLISION"
        objs.append(c)
    # only this fire's own wind reaches its domain
    winds = bpy.data.collections.new(f"fire_wind_{fid}")
    ds.effector_weights.collection = winds
    if spec["wind"] > 0:
        yaw = math.radians(anim.WIND_YAW)
        bpy.ops.object.effector_add(type="WIND", location=lo_d - Vector((0.5, 0, 0)),
                                    rotation=(0, math.radians(90), yaw))
        w = bpy.context.object
        w.name = f"fire_wind_{fid}"
        winds.objects.link(w)
        objs.append(w)
        w.field.flow = 0.0
        seed = anim.seed_of(fid)
        for fr in range(1, n_frames + 1, 3):
            w.field.strength = spec["wind"] * (0.35 + 1.1 * anim.gust(fr / FPS, seed))
            w.field.keyframe_insert("strength", frame=fr)
    return dom, cells, objs


def bake(dom, objs):
    """Bake in a scene that holds only the simulation's objects: in the castle scene every frame
    step re-evaluates thousands of objects and doubles the bake time."""
    main = bpy.context.scene
    bs = bpy.data.scenes.new("fire_bake")
    bs.render.fps = FPS
    for ob in objs:
        bs.collection.objects.link(ob)
        if ob.name in main.collection.objects:
            main.collection.objects.unlink(ob)
    with bpy.context.temp_override(scene=bs, view_layer=bs.view_layers[0], object=dom, active_object=dom,
                                   selected_objects=[dom]):
        bpy.ops.fluid.bake_all()
    bpy.data.scenes.remove(bs)


def cache_ok(cache, stamp, n_frames):
    """True when `cache` holds a finished bake made with the same settings."""
    f = cache / "stamp.json"
    vdbs = list((cache / "data").glob("fluid_data_*.vdb")) if (cache / "data").exists() else []
    return f.exists() and len(vdbs) >= n_frames and json.loads(f.read_text()) == stamp


def volume_object(fid, cache, n_frames, lo_d, size, mat):
    """The baked grids as a Volume object: the cache's VDB files hold the grids in metres from
    the domain's low corner, so this renders the bake without the domain (and without a re-bake)."""
    vol = bpy.data.volumes.new(f"fire_volume_{fid}")
    vol.filepath = str(cache / "data" / "fluid_data_0001.vdb")
    vol.is_sequence = True
    vol.frame_start = 1
    vol.frame_duration = n_frames
    vol.sequence_mode = "CLIP"
    vol.materials.append(mat)
    ob = bpy.data.objects.new(f"fire_volume_{fid}", vol)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = lo_d
    ob.visible_shadow = False
    return ob


# ---------- look ----------

def fire_material(name, size, temp_k=TEMP_K):
    """Blackbody flame and dark absorbing smoke, both faded out before the domain walls (the volume's
    object coordinates run 0..size from the domain's low corner)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new

    def math_(op, a, b=None, clamp=False):
        m = N("ShaderNodeMath")
        m.operation = op
        m.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                L(v, m.inputs[i])
        return m.outputs[0]

    def smooth(v, a, b):
        m = N("ShaderNodeMapRange")
        m.interpolation_type = "SMOOTHSTEP"
        m.inputs["From Min"].default_value, m.inputs["From Max"].default_value = a, b
        L(v, m.inputs["Value"])
        return m.outputs["Result"]

    out = N("ShaderNodeOutputMaterial")
    pv = N("ShaderNodeVolumePrincipled")
    pv.inputs["Color"].default_value = (0.04, 0.04, 0.04, 1)
    dens = N("ShaderNodeAttribute")
    dens.attribute_name = "density"
    flame = N("ShaderNodeAttribute")
    flame.attribute_name = "flame"
    # walls: object coordinates of the unit box run -0.5..0.5; fade the top fifth and the sides
    tc = N("ShaderNodeTexCoord")
    sep = N("ShaderNodeSeparateXYZ")
    mp = N("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / size.x, 1 / size.y, 1 / size.z)
    mp.inputs["Location"].default_value = (-0.5, -0.5, -0.5)
    L(tc.outputs["Object"], mp.inputs["Vector"])
    L(mp.outputs["Vector"], sep.inputs[0])
    top = smooth(sep.outputs[2], 0.47, 0.25)
    sx = smooth(math_("ABSOLUTE", sep.outputs[0]), 0.48, 0.38)
    sy = smooth(math_("ABSOLUTE", sep.outputs[1]), 0.48, 0.38)
    wall = math_("MULTIPLY", math_("MULTIPLY", top, sx), sy)

    f = math_("MULTIPLY", flame.outputs["Fac"], wall)
    L(math_("MULTIPLY", math_("MULTIPLY", dens.outputs["Fac"], wall), SMOKE_DENSITY), pv.inputs["Density"])
    temp = N("ShaderNodeMapRange")
    temp.inputs["To Min"].default_value, temp.inputs["To Max"].default_value = temp_k
    L(f, temp.inputs["Value"])
    bb = N("ShaderNodeBlackbody")
    L(temp.outputs["Result"], bb.inputs["Temperature"])
    # the blackbody node is normalised; brightness follows flame^EMIT_POW, cut softly at the rim
    strength = math_("MULTIPLY", math_("POWER", f, EMIT_POW), smooth(f, EDGE[0], EDGE[1]))
    L(bb.outputs[0], pv.inputs["Emission Color"])
    L(math_("MULTIPLY", strength, 8.0), pv.inputs["Emission Strength"])
    L(pv.outputs[0], out.inputs["Volume"])
    return mat


# ---------- rendering ----------

def setup_eevee(sc, res2):
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.film_transparent = True
    sc.render.use_compositing = False
    sc.render.resolution_x, sc.render.resolution_y = res2
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    ee = sc.eevee
    ee.taa_render_samples = 8
    if hasattr(ee, "use_raytracing"):
        ee.use_raytracing = False
    ee.use_volumetric_shadows = False
    ee.volumetric_tile_size = "1"
    ee.volumetric_samples = 128
    ee.volumetric_sample_distribution = 0.0
    for fn in [f for f in bpy.app.handlers.render_pre if f.__name__ == "_fit_volume_range"]:
        bpy.app.handlers.render_pre.remove(fn)
    sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    st = sc.render.image_settings
    if hasattr(st, "media_type"):
        st.media_type = "IMAGE"
    st.file_format = "OPEN_EXR"
    st.color_mode = "RGBA"
    st.color_depth = "16"


def domain_region(lo_d, hi_d, cam, res2):
    """Even pixel rect [x0, y0, x1, y1] (2x frame) of the domain box, and its depth range."""
    sc = bpy.context.scene
    corners = [Vector((x, y, z)) for x in (lo_d.x, hi_d.x) for y in (lo_d.y, hi_d.y) for z in (lo_d.z, hi_d.z)]
    uv = [world_to_camera_view(sc, cam, c) for c in corners]
    x0 = max(0, int(min(v.x for v in uv) * res2[0]) // 2 * 2)
    y0 = max(0, int(min(1 - v.y for v in uv) * res2[1]) // 2 * 2)
    x1 = min(res2[0], (int(math.ceil(max(v.x for v in uv) * res2[0])) + 1) // 2 * 2)
    y1 = min(res2[1], (int(math.ceil(max(1 - v.y for v in uv) * res2[1])) + 1) // 2 * 2)
    depth = [(c - cam.matrix_world.translation).dot(view_dir(cam)) for c in corners]
    return [x0, y0, x1, y1], (min(depth), max(depth))


def view_dir(cam):
    return -Vector(cam.matrix_world.to_3x3().col[2]).normalized()


def region_camera(cam, region, res2):
    """An orthographic camera that sees exactly the pixel rect `region` of the 2x frame, so EEVEE's
    volume froxels cover only that rect (the game camera has no lens shift)."""
    W, H = res2
    x0, y0, x1, y1 = region
    ppm = W / cam.data.ortho_scale
    data = cam.data.copy()
    data.ortho_scale = (x1 - x0) / ppm
    data.sensor_fit = "HORIZONTAL"
    rc = bpy.data.objects.new("fire_cam", data)
    bpy.context.scene.collection.objects.link(rc)
    m = cam.matrix_world
    right, up = Vector(m.to_3x3().col[0]).normalized(), Vector(m.to_3x3().col[1]).normalized()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rc.matrix_world = m.copy()
    rc.location = m.translation + right * ((cx - W / 2) / ppm) + up * ((H / 2 - cy) / ppm)
    return rc


def render_frames(cam, region, res2, first, n, tmp, tag):
    """Frames first..first+n-1 of the pixel rect `region` of the 2x frame, as RGBA float arrays."""
    import OpenImageIO as oiio
    sc = bpy.context.scene
    r = sc.render
    rc = region_camera(cam, region, res2)
    sc.camera = rc
    r.resolution_x, r.resolution_y = region[2] - region[0], region[3] - region[1]
    r.use_border = r.use_crop_to_border = False
    for f in tmp.glob(f"{tag}_*.exr"):
        f.unlink()
    r.filepath = str(tmp / f"{tag}_####")
    sc.frame_start, sc.frame_end, sc.frame_step = first, first + n - 1, 1
    try:
        bpy.ops.render.render(animation=True)
    finally:
        sc.camera = cam
        bpy.data.objects.remove(rc)
        r.resolution_x, r.resolution_y = res2
    out = []
    for i in range(n):
        buf = oiio.ImageBuf(str(tmp / f"{tag}_{first + i:04d}.exr"))
        a = np.asarray(buf.get_pixels(oiio.FLOAT)).reshape(buf.spec().height, buf.spec().width, -1)
        out.append(a[:, :, :4].astype(np.float32))
    return out


# ---------- loop ----------

def choose_loop(frames, n, fade, search):
    """Start offset within `search` whose fade window best matches the one n frames later."""
    small = [f[::2, ::2] for f in frames]
    costs = []
    for s in range(search + 1):
        c = np.mean([np.abs(small[s + i] - small[s + n + i]).mean() for i in range(fade)])
        costs.append(float(c))
    s = int(np.argmin(costs))
    return s, costs


def make_loop(frames, s, n, fade):
    out = [frames[s + i].copy() for i in range(n)]
    for i in range(fade):
        x = i / fade
        w = x * x * x * (x * (6 * x - 15) + 10)
        out[i] = w * frames[s + i] + (1 - w) * frames[s + n + i]
    return out


def half(f):
    """2 x 2 box average of a premultiplied RGBA frame."""
    h, w = f.shape[0] // 2 * 2, f.shape[1] // 2 * 2
    f = f[:h, :w]
    return 0.25 * (f[0::2, 0::2] + f[1::2, 0::2] + f[0::2, 1::2] + f[1::2, 1::2])


# ---------- main ----------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    location.add_argument(ap)
    ap.add_argument("--layout", default=None, help="default: the location's layout.json")
    ap.add_argument("--only", default=None)
    ap.add_argument("--frames", type=int, default=72, help="loop length in frames (24 fps)")
    ap.add_argument("--fade", type=int, default=18)
    ap.add_argument("--search", type=int, default=24)
    ap.add_argument("--quick", action="store_true", help="coarser voxels and a short loop, for tests")
    ap.add_argument("--bake-only", action="store_true", help="stop after the simulations (no GPU use)")
    ap.add_argument("--reuse", action="store_true", help="render from earlier bakes with the same settings")
    ap.add_argument("--out", default=None, help="game folder to write (default: location.game_dir())")
    args = ap.parse_args(argv)
    location.use(args.location)
    import game_flipbooks as fb
    import game_frame as gf

    out = Path(args.out) if args.out else location.game_dir()
    FIRES = {k: v for k, v in location.table("fires").items() if not k.startswith("_")}
    tmp = out / "build" / "fire"
    for d in ("assets/flipbooks", "build/fire"):
        (out / d).mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    plan, trace, layout, cam = gf.build(args.layout)
    srcs, _ = gf.sources()
    gf.hide_moving(srcs)
    sc = bpy.context.scene
    gain = 2.0 ** layout["render"].get("exposure", 0.0)
    n, fade, search = args.frames, args.fade, args.search
    if args.quick:
        n, fade, search = 24, 6, 4
    n_render = n + fade + search
    n_sim = WARMUP + n_render
    fires = [d for d in srcs if d["id"] in FIRES and (not args.only or d["id"] in args.only.split(","))]
    for d in srcs:
        if d["kind"] in gf.FLIPBOOK_KINDS:
            for ob in d["flames"]:
                ob.hide_render = True
    t_build = time.time() - t0
    print(f"FIRE built in {t_build:.0f}s: {[d['id'] for d in fires]}, {n_sim} sim frames, {n_render} rendered")
    timing = {"build_s": round(t_build)}

    # simulations
    doms = {}
    for d in fires:
        spec = dict(FIRES[d["id"]])
        if args.quick:
            spec["voxel"] *= 1.6
        cols = [o for o in bpy.data.objects if gf.prop_key(o) == gf.prop_key(d["coals"][0])
                and o.name.split(".")[0] in spec.get("colliders", ())]
        fuel = list(d["coals"]) + [o for o in bpy.data.objects if o.parent is not None
                                   and o.parent == d["coals"][0].parent and o.name.split(".")[0] in spec.get("extra_fuel", ())]
        lo_d, hi_d = domain_box(spec, fuel)
        cache = tmp / f"cache_{d['id']}"
        stamp = {"spec": {k: v for k, v in spec.items() if k not in ("peak", "temp")}, "frames": n_sim,
                 "box": [list(lo_d), list(hi_d)]}
        stamp = json.loads(json.dumps(stamp))
        timing[d["id"]] = {"sim_frames": n_sim}
        if args.reuse and cache_ok(cache, stamp, n_sim):
            print(f"FIRE {d['id']}: reusing the bake in {cache}")
            timing[d["id"]]["bake_s"] = 0
        else:
            dom, cells, objs = build_sim(d["id"], spec, fuel, cols, cache, n_sim)
            est = cells * CELL_RATE_S * n_sim
            print(f"FIRE {d['id']}: domain {tuple(round(v, 2) for v in dom.scale)} m, "
                  f"res {dom.modifiers['fluid'].domain_settings.resolution_max}, {cells / 1e6:.2f} M cells, "
                  f"bake estimate {est:.0f}s", flush=True)
            tb = time.time()
            bake(dom, objs)
            tb = time.time() - tb
            (cache / "stamp.json").write_text(json.dumps(stamp))
            print(f"FIRE {d['id']} baked in {tb:.0f}s ({tb / n_sim:.2f} s/frame)", flush=True)
            timing[d["id"]].update({"bake_s": round(tb), "cells_M": round(cells / 1e6, 3)})
        vob = volume_object(d["id"], cache, n_sim, lo_d, hi_d - lo_d,
                            fire_material(f"fire_volume_{d['id']}", hi_d - lo_d, spec.get("temp", TEMP_K)))
        doms[d["id"]] = (vob, lo_d, hi_d)

    if args.bake_only:
        (out / "build" / "fire_timing_bake.json").write_text(json.dumps(timing, indent=1))
        print(f"FIRE bakes done in {time.time() - t0:.0f}s", flush=True)
        return

    # renders
    res2 = (gf.RES[0] * 2, gf.RES[1] * 2)
    for name in ("haze",):
        if bpy.data.objects.get(name):
            bpy.data.objects[name].hide_render = True
    fb.holdout_static({v[0] for v in doms.values()}, "fire_holdout")
    for ob in bpy.data.objects:
        if ob.type == "LIGHT":
            ob.hide_render = True
    setup_eevee(sc, res2)
    meta_path = out / "build" / "fire_flipbooks.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() and args.only else {}
    view = view_dir(cam)
    for d in fires:
        fid = d["id"]
        spec = FIRES[fid]
        for k, v in doms.items():
            v[0].hide_render = k != fid
        vob, lo_d, hi_d = doms[fid]
        region, (dn, dx) = domain_region(lo_d, hi_d, cam, res2)
        sc.eevee.volumetric_start = max(0.1, dn - 0.5)
        sc.eevee.volumetric_end = dx + 0.5
        tr = time.time()
        probe = render_frames(cam, region, res2, WARMUP + 1, 2, tmp, f"{fid}_probe")
        per = (time.time() - tr) / 2
        print(f"FIRE {fid}: region {region[2] - region[0]}x{region[3] - region[1]} px (2x), {per:.2f} s/frame, "
              f"render estimate {per * n_render:.0f}s")
        del probe
        tr = time.time()
        frames = render_frames(cam, region, res2, WARMUP + 1, n_render, tmp, fid)
        t_render = time.time() - tr
        # crop to what the fire ever covers, on even pixels
        lit = np.zeros(frames[0].shape[:2], bool)
        for f in frames:
            lit |= (f[:, :, 3] > 0.003) | (f[:, :, :3].max(axis=2) > 0.003)
        if not lit.any():
            print(f"FIRE {fid} is hidden from the camera, skipped")
            continue
        ys, xs = np.nonzero(lit)
        pad = 8
        cx0, cy0 = max(0, (xs.min() - pad) // 2 * 2), max(0, (ys.min() - pad) // 2 * 2)
        cx1 = min(lit.shape[1] // 2 * 2, (xs.max() + pad + 2) // 2 * 2)
        cy1 = min(lit.shape[0] // 2 * 2, (ys.max() + pad + 2) // 2 * 2)
        frames = [f[cy0:cy1, cx0:cx1] for f in frames]
        s, costs = choose_loop(frames, n, fade, search)
        loop2 = make_loop(frames, s, n, fade)
        # brightness: the brightest flame pixels at `peak` (base-layer units, exposure included)
        lum = np.concatenate([(0.2126 * f[:, :, 0] + 0.7152 * f[:, :, 1] + 0.0722 * f[:, :, 2]).ravel()
                              for f in loop2[::4]])
        lum = lum[lum > 0.01]
        raw = float(np.percentile(lum, 99.5)) if lum.size else 1.0
        k = spec["peak"] / max(raw, 1e-6)
        for f in loop2:
            f[:, :, :3] *= k * gain
        main_rect = [int(region[0] + cx0) // 2, int(region[1] + cy0) // 2, int(cx1 - cx0) // 2, int(cy1 - cy0) // 2]
        centre = (lo_d + hi_d) / 2
        depth_m = round(float((centre - cam.matrix_world.translation).dot(view)), 3)
        for suffix, fr in (("", [half(f) for f in loop2]), ("@2", loop2)):
            eid = f"{fid}_flame{suffix}"
            img, cols, rows, cw, ch = fb.atlas(fr)
            scale = fb.write_atlas(out / "assets" / "flipbooks" / f"{eid}.png", img)
            meta[eid] = {"id": eid, "atlas": f"assets/flipbooks/{eid}.png", "cols": cols, "rows": rows,
                         "frames": n, "fps": float(FPS), "loop": True, "rect": main_rect, "cell": [cw, ch],
                         "blend": "premul", "encoding": "srgb", "scale": scale, "depth": None,
                         "depth_m": depth_m, "group": fid, "kind": "flame",
                         "density": 2 if suffix else 1, "source": "mantaflow"}
            np.save(tmp / f"{eid}_loop.npy", np.stack(fr).astype(np.float16))
        timing[fid].update({"render_s": round(t_render), "s_per_frame": round(t_render / n_render, 2),
                            "region_2x": [region[2] - region[0], region[3] - region[1]], "loop_start": s,
                            "seam_cost": round(costs[s], 5), "seam_cost_worst": round(max(costs), 5),
                            "raw_peak": round(raw, 3)})
        print(f"FIRE {fid}: rendered {n_render} frames in {t_render:.0f}s, loop start {s} "
              f"(seam cost {costs[s]:.4f}, worst {max(costs):.4f}), raw peak {raw:.3f}, rect {main_rect}")
    timing["total_s"] = round(time.time() - t0)
    for e in meta.values():
        e["rect"] = [int(v) for v in e["rect"]]
    meta_path.write_text(json.dumps(meta, indent=1))
    (out / "build" / "fire_timing.json").write_text(json.dumps(timing, indent=1))
    print(f"FIRE done in {time.time() - t0:.0f}s: {json.dumps(timing)}")


if __name__ == "__main__":
    main()

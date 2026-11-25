"""The game frame: the 2560 x 1440 game camera, the static scene the game layers are rendered from,
and what every game step shares about it (the Godot axes, pixel positions, hotspot volumes).

Used by game_layers.py, game_flipbooks.py, game_fire.py, game_views.py and export_game.py.

Camera. The game camera is the main orthographic camera of trace.json (elevation 38 deg, yaw 11 deg)
with the same image centre and the same vertical coverage as the 1536 x 1024 still at 52 px/m
(19.69 m), and a wider view: 35.0 m across 2560 px, so 73.14 px/m.

Static scene. `build()` builds the scene as build_scene.py does with the Cycles layout, without
rain, and with everything that moves taken out of the camera's view:

- rain streaks and splashes are not built;
- smoke plumes, flying embers, drip strands, the ground mist and every crow are hidden;
- the flame tongues of open fires are hidden from camera rays only: they still light the scene and
  still show in glossy and transmission rays, so their reflections in puddles and wet stone stay in
  the picture and land in the fire's light group. The flipbooks draw the flames themselves.

Light groups. `assign_light_groups()` gives every flickering source of anim.py (each open fire,
each lit window and door, the lanterns, the banked forge) its own Cycles light group: its point
lights, flame tongues, coals and room glow. Everything else (sky, moon) is the `base` group. The
group ids come from location.json `light_groups`.

Coordinates. plan.json and Blender are Z-up: X east, Y north, Z up. Godot is Y-up with -Z
forward. Every point and direction goes through the same rotation as the glTF exporter uses:

    godot (x, y, z) = blender (x, z, -y)

so north is Godot -Z, and the glTF files, the camera, the lights and the hotspots share one frame.
"""

import json
import math
import re
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scene"))

import anim  # noqa: E402
import build_scene as bs  # noqa: E402
import location  # noqa: E402

RES = (2560, 1440)
WIDTH_M = 35.0
# the still whose image centre and vertical coverage the game frame keeps
STILL_RES = (1536, 1024)

# props hidden from the static frame entirely (they move or are drawn by the runtime)
HIDDEN_PROPS = ("drips", "ground_mist", "crow", "crow_flying")
# anim.py source kinds whose flames are drawn by flipbooks; interior and lamp flames stay in the frame
FLIPBOOK_KINDS = ("fire",)
# Blender Z-up -> Godot Y-up, the same rotation the glTF exporter applies (+Y up, -Z forward)
TO_GODOT = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
# materials of effects: no collision, no depth, no click volume
EFFECT_MATS = ("smoke", "fire", "flame", "ember", "spark", "mist", "haze", "steam", "drip", "plume", "rain_")
EFFECT_EXACT = {"rain", "glow"}


def width_m():
    """Width of the game frame in metres: `width_m` of the location's trace.json camera, else WIDTH_M."""
    return float(location.load("trace.json")["camera"].get("width_m", WIDTH_M))


def g(v):
    """Blender point or direction -> Godot [x, y, z]."""
    return [round(c, 5) for c in TO_GODOT @ Vector(v)]


def camera_game(spec, res=RES, width=None):
    """Orthographic game camera: trace.json's camera with the still's image centre, `width` m wide
    (default `width_m()`)."""
    return bs.ortho_camera(spec, STILL_RES, width or width_m(), "HORIZONTAL")


def camera_info(spec, res=RES, width=None):
    """Pixel scale of the game frame, and the pixel where the world origin lands."""
    s_old, s_new = spec["px_per_m"], res[0] / (width or width_m())
    cu, cv = spec["center_px"]
    return {"px_per_m": s_new,
            "center_px": [res[0] / 2 + (cu - STILL_RES[0] / 2) * s_new / s_old,
                          res[1] / 2 + (cv - STILL_RES[1] / 2) * s_new / s_old],
            "height_m": res[1] / s_new}


def build(layout_path=None, res=RES):
    """Build the location's scene with the game camera; returns (plan, trace, layout, cam).

    `layout_path` defaults to the location's layout.json."""
    plan = location.plan()
    trace = location.load("trace.json")
    layout = json.loads(Path(layout_path).read_text()) if layout_path else location.load("layout.json")
    bs.build_world(plan, layout)
    cam = camera_game(trace["camera"], res)
    bs.install_camera(cam, res)
    bs.setup_atmosphere(layout["environment"])
    bpy.context.view_layer.update()
    return plan, trace, layout, cam


# ---------- moving parts ----------

def prop_key(ob):
    """Plan key of the prop an object belongs to (`brazier`, `lit_door#2`), or None."""
    o = ob
    while o is not None:
        if o.name.startswith("prop_") and o.parent is None:
            return o.name[len("prop_"):]
        o = o.parent
    m = re.match(r"light_(.+)_\d+$", ob.name)
    return m.group(1) if m else None


def _mats(ob):
    return {anim._base(s.material.name) for s in ob.material_slots if s.material} if ob.type == "MESH" else set()


def sources():
    """anim.py's flickering sources, each with its plan key, an id and its objects.

    Returns a list of dicts: id, key, kind, seed, flames, coals, lights, smoke, rooms (objects).
    """
    summary = anim.setup(perches=bs.PERCHES)
    names = location.table("light_groups")
    by_key = {}
    out = []
    for src in anim._STATE["sources"]:
        obs = [f.ob for f in src.flames] + src.coals + [li for li, _, _ in src.lights]
        key = next((prop_key(o) for o in obs if prop_key(o)), None)
        by_key.setdefault(key, []).append(src)
        out.append(dict(src=src, key=key, kind=src.kind, seed=src.seed,
                        flames=[f.ob for f in src.flames], coals=list(src.coals),
                        lights=[li for li, _, _ in src.lights], smoke=[o for o, _ in src.smoke], rooms=[]))
    for d in out:
        n = len(by_key[d["key"]])
        base = re.sub(r"[^a-z0-9]+", "_", d["key"].lower()).strip("_")
        i = by_key[d["key"]].index(d["src"])
        d["id"] = names.get(f"{d['key']}/{i}", base if n == 1 else f"{base}_{i}")
    # lit rooms: the meshes with the window_room material, given to the first source of their prop
    for ob in bpy.data.objects:
        if "window_room" in _mats(ob):
            key = prop_key(ob)
            d = next((d for d in out if d["key"] == key), None)
            if d:
                d["rooms"].append(ob)
    return out, summary


def hide_moving(srcs):
    """Take everything that moves out of the static frame (see the module doc)."""
    hidden = []
    for ob in bpy.data.objects:
        key = prop_key(ob)
        if key and key.split("#")[0] in HIDDEN_PROPS:
            ob.hide_render = True
            hidden.append(ob.name)
        elif ob.type == "MESH" and ({"smoke"} & _mats(ob) or ("embers" in _mats(ob) and "spark" in ob.data.attributes)):
            ob.hide_render = True
            hidden.append(ob.name)
    for d in srcs:
        if d["kind"] in FLIPBOOK_KINDS:
            for ob in d["flames"]:
                ob.visible_camera = False
    # anim_crows adds animated fliers that are not under a prop root
    for root in bpy.data.objects:
        if root.name.startswith("anim_crow") and root.parent is None:
            for ob in [root, *root.children_recursive]:
                ob.hide_render = True
                hidden.append(ob.name)
    return hidden


def assign_light_groups(srcs, view_layer=None):
    """One Cycles light group per source, `base` for the sky and every other light."""
    vl = view_layer or bpy.context.scene.view_layers[0]
    for lg in list(vl.lightgroups):
        vl.lightgroups.remove(lg)
    vl.lightgroups.add(name="base")
    bpy.context.scene.world.lightgroup = "base"
    for ob in bpy.data.objects:
        if ob.type == "LIGHT":
            ob.lightgroup = "base"
    for d in srcs:
        vl.lightgroups.add(name=d["id"])
        for ob in d["flames"] + d["coals"] + d["lights"] + d["rooms"]:
            ob.lightgroup = d["id"]
    return ["base"] + [d["id"] for d in srcs]


def anchor(d):
    """World position of a source: the mean of its lights, else of its flames and coals."""
    obs = d["lights"] or d["flames"] or d["coals"] or d["rooms"]
    return sum((o.matrix_world.translation for o in obs), Vector()) / len(obs)


# ---------- shared by the game steps ----------

def camera_block(cam, trace, res=RES, width=None):
    """The camera block of scene.json (and of each zoom view)."""
    width_m_ = width or width_m()
    mw = cam.matrix_world
    rot = mw.to_3x3().normalized()
    spec = trace["camera"]
    info = camera_info(spec, res, width_m_)
    return {
        "_doc": "Orthographic game camera. basis columns are the camera's local +X (right), +Y (up), "
                "+Z (back; it looks along -Z), already in Godot axes. size is the frame width in meters "
                "(Godot keep_aspect = KEEP_WIDTH). The image-centre shift is baked into origin.",
        "origin": g(mw.translation),
        "basis_x": g(rot.col[0]), "basis_y": g(rot.col[1]), "basis_z": g(rot.col[2]),
        "ortho_width_m": width_m_, "ortho_height_m": round(info["height_m"], 5),
        "px_per_m": round(info["px_per_m"], 5),
        "resolution": list(res),
        "near": 1.0, "far": 200.0,
        "blender": {"location": list(mw.translation), "rotation_euler_xyz": list(cam.rotation_euler),
                    "ortho_scale": width_m_, "elevation_deg": spec["elevation_deg"],
                    "yaw_deg": spec["yaw_deg"], "px_per_m": info["px_per_m"],
                    "world_origin_px": [round(c, 2) for c in info["center_px"]]},
    }


def to_px(cam, p):
    """Blender world point -> [x, y] pixel of the game frame (row 0 at the top)."""
    from bpy_extras.object_utils import world_to_camera_view
    v = world_to_camera_view(bpy.context.scene, cam, Vector(p))
    return [round(v.x * RES[0], 1), round((1 - v.y) * RES[1], 1)]


def volume_only(mat):
    """A material that is a volume (smoke, fog) with no surface: invisible as a solid."""
    if not mat.use_nodes or not mat.node_tree:
        return False
    outs = [n for n in mat.node_tree.nodes if n.type == "OUTPUT_MATERIAL"]
    return bool(outs) and all(not o.inputs["Surface"].is_linked and o.inputs["Volume"].is_linked for o in outs)


def is_effect(ob):
    mats = [m for m in ob.data.materials if m] if ob.type == "MESH" else []
    if not mats:
        return False
    return all(volume_only(m) or m.name.lower() in EFFECT_EXACT
               or any(e in m.name.lower() for e in EFFECT_MATS) and m.name.lower() != "rainwater" for m in mats)


def world_verts(ob):
    me = ob.data
    co = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    m = np.array(ob.matrix_world)
    return co @ m[:3, :3].T + m[:3, 3]


def prop_parts(key):
    """The root of a placed prop and its solid meshes (no effects)."""
    root = bpy.data.objects.get(f"prop_{key}")
    if root is None:
        return None, []
    return root, [o for o in root.children_recursive if o.type == "MESH" and not is_effect(o)]


def obb_of(parts, rot):
    """Box around the parts in a frame turned by rot about Z: (center xyz, size xyz)."""
    v = np.concatenate([world_verts(o) for o in parts])
    c, s = math.cos(-rot), math.sin(-rot)
    lx = v[:, 0] * c - v[:, 1] * s
    ly = v[:, 0] * s + v[:, 1] * c
    lo = np.array([lx.min(), ly.min(), v[:, 2].min()])
    hi = np.array([lx.max(), ly.max(), v[:, 2].max()])
    mid = (lo + hi) / 2
    cx = mid[0] * math.cos(rot) - mid[1] * math.sin(rot)
    cy = mid[0] * math.sin(rot) + mid[1] * math.cos(rot)
    return (cx, cy, mid[2]), tuple(hi - lo)


def hotspot_root(h):
    """The object a hotspot is anchored to: a prop root, or a named object (`obj:<name>`)."""
    a = h["anchor"]
    return bpy.data.objects[a[4:]] if a.startswith("obj:") else bpy.data.objects[f"prop_{a}"]


def hotspots():
    """hotspots.json entries for location.json `hotspots`: look text, click volume, stand point."""
    out = []
    for h in location.table("hotspots"):
        anchor = h["anchor"]
        if "volume" in h:
            v = h["volume"]
            center, size, rot = v["center"], v["size"], math.radians(v["rot"])
        else:
            root, parts = prop_parts(anchor)
            rot = root.rotation_euler.z
            parts = [o for o in parts if not o.name.startswith(("cut_", "hole_"))]
            center, size = obb_of(parts, rot)
            # cap tall props: smoke stacks and roofs need not be clickable sky
            if size[2] > 4.5:
                center = (center[0], center[1], 2.25)
                size = (size[0], size[1], 4.5)
            # low props with flames above them: the flames are clickable too
            if size[2] < h.get("min_h", 0):
                z0 = center[2] - size[2] / 2
                center = (center[0], center[1], z0 + h["min_h"] / 2)
                size = (size[0], size[1], h["min_h"])
        pos = hotspot_root(h).matrix_world.translation
        sx, sy = h["stand"]
        out.append({
            "id": h["id"], "name": h["name"], "text": h["text"],
            "position": g(pos),
            # the box is turned about the vertical axis; Godot's yaw is the same angle (Z-up -> Y-up)
            "volume": {"center": g(center), "size": [size[0], size[2], size[1]], "yaw_rad": rot},
            "stand": g((sx, sy, 0.0)),
            "plan": {"stand_xy": [sx, sy]},
        })
    return out

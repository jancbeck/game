"""Export a location for the real-time game: camera, layers, flipbooks, walkable space.

    /Applications/Blender.app/Contents/MacOS/Blender --background --python scene/export_game.py -- \
        [--location courtyard] [--out game]

The last step of the game export (scripts/game.py final runs them all; the game-export skill). The
render steps write their file lists to <out>/build/layers.json, flipbooks.json and
view_<view>.json; the fire flipbooks of <out>/build/fire_flipbooks.json replace entries by id.
This script builds the scene with the game camera (scene/game_frame.py) and writes:

  <out>/assets/proxy.glb        invisible proxy geometry: walls (the gate passage open), prop obstacles,
                                the floor
  <out>/assets/walk.glb         walkable surfaces only, one material per surface type (scene/game_walk.py)
  <out>/assets/crow.glb         one crow with body, head, tail, wing_l and wing_r nodes
  <out>/data/scene.json         camera, depth, layers, masks, views, flipbooks, crows, walk, lights
  <out>/data/hotspots.json      interactable objects: name, look text, click volume, stand point

Points and directions are in Godot axes (game_frame.g).
"""

import argparse
import json
import math
import shutil
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Vector
from mathutils.geometry import tessellate_polygon

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scene"))

import anim_crows  # noqa: E402
import build_scene as bs  # noqa: E402
import game_frame as gf  # noqa: E402
import game_room  # noqa: E402
import game_walk  # noqa: E402
import location  # noqa: E402
from game_frame import g, prop_parts, world_verts  # noqa: E402
from planlib import entries, height, inside_polygon, resolve_block  # noqa: E402

# body band for obstacles: anything with geometry between these heights blocks walking
BAND = (0.25, 1.8)
# props that do not block walking (flat, scene-wide or covered by the wall boxes)
NOT_OBSTACLES = {"grate", "drips", "ground_mist", "ground_dressing", "age_dressing", "road", "debris",
                 "straw_pile", "base_dressing", "gate_door", "palas", "west_ditch", "treeline", "tree",
                 "dead_bush", "grass_tuft", "drip_bucket_well", "ladder", "kitchen_door", "tower_stair_door",
                 "tower_surround"}
def hull2d(pts):
    """Convex hull (counter-clockwise) of 2D points, monotone chain."""
    pts = sorted(set((round(float(x), 4), round(float(y), 4)) for x, y in pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def inside(x, y, poly):
    return inside_polygon(x, y, [Vector((px, py)) for px, py in poly])


# ---------- proxy geometry ----------

def block_boxes(plan):
    """Every masonry block as (name, center xy, half size, rot rad, z0, z1), as build_block lays it out."""
    out = []
    heights = plan["heights"]
    for name, b in entries(plan["blocks"]):
        h = height(b["h"], heights) + b.get("h_offset", 0.0)
        base = b.get("base", heights["lower_ward"])
        b = resolve_block(b)
        out.append((name, b["center"], (b["size"][0] / 2, b["size"][1] / 2), math.radians(b.get("rot_z", 0)),
                    base, h))
    return out


def prism(name, poly, z0, z1, coll):
    n = len(poly)
    verts = [(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly]
    faces = [list(range(n - 1, -1, -1)), list(range(n, 2 * n))]
    faces += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def box_poly(c, hs, rot):
    cr, sr = math.cos(rot), math.sin(rot)
    return [(c[0] + x * cr - y * sr, c[1] + x * sr + y * cr)
            for x, y in ((-hs[0], -hs[1]), (hs[0], -hs[1]), (hs[0], hs[1]), (-hs[0], hs[1]))]


def obstacle_hulls(plan):
    """Footprint hulls of props in the body band. Parts whose footprints touch are merged, so a post
    stays its own collider and a cart stays one."""
    platform = plan["platform"]["polygon"]
    out = []
    for key, p in entries(plan["props"]):
        if key.split("#")[0] in NOT_OBSTACLES or not inside(*p["pos"], platform):
            continue
        _, parts = prop_parts(key)
        items = []
        for ob in parts:
            v = world_verts(ob)
            if not len(v) or v[:, 2].max() < BAND[0] or v[:, 2].min() > BAND[1]:
                continue
            items.append((v[:, :2], float(v[:, 2].max()), v[:, :2].min(0) - 0.08, v[:, :2].max(0) + 0.08))
        # union-find on overlapping, slightly grown footprint boxes
        parent = list(range(len(items)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                if (a[2] <= b[3]).all() and (b[2] <= a[3]).all():
                    parent[find(i)] = find(j)
        groups = {}
        for i, it in enumerate(items):
            groups.setdefault(find(i), []).append(it)
        for k, grp in enumerate(groups.values()):
            pts = np.concatenate([it[0] for it in grp])
            hull = hull2d(pts)
            if len(hull) < 3:
                continue
            top = min(max(it[1] for it in grp), 4.0)
            out.append((f"prop_{key.replace('#', '_')}_{k}", hull, top))
    return out


def wall_pieces(plan):
    """Wall and tower boxes as (name, footprint, z0, z1), with the gate passage left open: the gatehouse
    and the north curtain behind it are split either side of the passage and bridged above the vault."""
    gx0, gx1 = game_walk.GATE_X
    out = []
    for name, c, hs, rot, z0, z1 in block_boxes(plan):
        poly = box_poly(c, hs, rot)
        if name in ("gatehouse", "north_curtain") and abs(rot) < 1e-6:
            x0, x1, y0, y1 = c[0] - hs[0], c[0] + hs[0], c[1] - hs[1], c[1] + hs[1]
            rect = lambda a, b: [(a, y0), (b, y0), (b, y1), (a, y1)]  # noqa: E731
            out += [(f"{name}_w", rect(x0, gx0), z0, z1), (f"{name}_e", rect(gx1, x1), z0, z1),
                    (f"{name}_vault", rect(gx0, gx1), 0.0 + bs_vault_top(), z1)]
            if name == "gatehouse":
                out.append(("gatehouse_below", rect(gx0, gx1), z0, 0.0))
        else:
            out.append((name, poly, z0, z1))
    return out


def bs_vault_top():
    from assets import gate_door as GD
    return GD.SPRING + GD.HALF


def export_proxies(plan, out):
    coll = bpy.data.collections.new("proxies")
    bpy.context.scene.collection.children.link(coll)
    objs = []
    walls = wall_pieces(plan)
    for name, poly, z0, z1 in walls:
        objs.append(prism(f"wall_{name}", poly, z0, z1, coll))
    if plan.get("kind", "yard") == "yard":
        # the barred gate leaves close the passage
        from assets import gate_door as GD
        gx0, gx1 = game_walk.GATE_X
        gy = 3.0 + GD.DOOR_Y
        objs.append(prism("gate_leaves", [(gx0, gy), (gx1, gy), (gx1, gy + 0.15), (gx0, gy + 0.15)], 0.0,
                          GD.SPRING + GD.DOOR_R - 0.2, coll))
    hulls = obstacle_hulls(plan)
    for name, hull, top in hulls:
        objs.append(prism(name, hull, 0.0, top, coll))
    # walkable floor: the courtyard platform at z = 0
    poly = plan["platform"]["polygon"]
    tris = tessellate_polygon([[Vector((x, y, 0)) for x, y in poly]])
    me = bpy.data.meshes.new("floor")
    me.from_pydata([(x, y, 0.0) for x, y in poly], [], [tuple(reversed(t)) for t in tris])
    me.update()
    floor = bpy.data.objects.new("floor", me)
    coll.objects.link(floor)
    for f in me.polygons:  # faces up
        if f.normal.z < 0:
            f.flip()
    objs.append(floor)
    export_glb(objs, out / "assets" / "proxy.glb")
    return {"walls": len(walls), "prop_obstacles": len(hulls)}, hulls


def export_glb(objs, path, materials="NONE"):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=True, export_materials=materials, export_animations=False)


# ---------- walkable space ----------

def walk_obstacles(plan, z):
    """Footprints of prop parts that stand in the body band above a walk at height z."""
    out = []
    items = entries(plan["props"]) + entries(plan["mounted"])
    for key, _ in items:
        if key.split("#")[0] in NOT_OBSTACLES or key.startswith("lit_door"):
            continue
        _, parts = prop_parts(key)
        for ob in parts:
            v = world_verts(ob)
            sel = v[(v[:, 2] > z + BAND[0]) & (v[:, 2] < z + BAND[1])] if len(v) else v
            if len(sel) >= 3:
                hull = hull2d(sel[:, :2])
                if len(hull) >= 3:
                    out.append((f"{key}_{ob.name}".replace("#", "_"), hull))
    return out


def export_room_walk(plan, hulls, out):
    """walk of a room (game_room.py): one floor mesh, no stairs, wall-walks or portals."""
    coll = bpy.data.collections.new("walk")
    bpy.context.scene.collection.children.link(coll)
    floor = game_room.floor(plan, hulls, coll)
    renamed = game_walk.surface_materials([floor])
    export_glb([floor], out / "assets" / "walk.glb", materials="EXPORT")
    game_walk.restore_names(renamed)
    area = sum(f.area for f in floor.data.polygons)
    surface = plan["platform"].get("surface", "cobble")
    return {
        "_doc": "walk.glb: the room's walkable floor, prop footprints cut out, no agent radius. exits: walking "
                "into one leaves for the location named by target.",
        "mesh": "assets/walk.glb", "area_m2": round(area, 1), "surfaces": list(game_walk.SURFACES),
        "surface_area_m2": {surface: round(area, 1)}, "wall_walks": {}, "links": [],
        "exits": game_room.exits(), "portals": [],
    }


def export_walk(plan, hulls, out):
    if plan.get("kind", "yard") == "room":
        return export_room_walk(plan, hulls, out)
    coll = bpy.data.collections.new("walk")
    bpy.context.scene.collection.children.link(coll)
    boxes = block_boxes(plan)
    walls = [(name, box_poly(c, hs, rot)) for name, c, hs, rot, z0, z1 in boxes]
    floor, gate_y1 = game_walk.floor(plan, walls, hulls, coll)
    surfaces = game_walk.floor_surfaces(floor, plan)
    stairs, links, spots = game_walk.stairs(plan, coll)
    walks, walk_info = game_walk.wall_walks(plan, boxes, coll, walk_obstacles(plan, game_walk.WALK_TOP))
    obs = [floor, stairs] + ([walks] if walks else [])
    renamed = game_walk.surface_materials(obs)
    export_glb(obs, out / "assets" / "walk.glb", materials="EXPORT")
    for ob in obs:
        for f in ob.data.polygons:
            name = game_walk.SURFACES[f.material_index]
            if ob is not floor:
                surfaces[name] = surfaces.get(name, 0.0) + f.area
    game_walk.restore_names(renamed)
    area = sum(f.area for ob in obs for f in ob.data.polygons)
    return {
        "_doc": "walk.glb: walkable surfaces only, obstacle footprints cut out, no agent radius. Stairs are "
                "treads (risers up to 0.25 m): bake with agent_max_climb >= 0.26. links join stair foot and top. "
                "Each face's material names the surface underfoot: " + ", ".join(game_walk.SURFACES) + ". "
                "Puddles are not a face type: use the puddle mask under the figure. portals: walking into a "
                "hides the figure for `seconds`, then it steps out at b (and the reverse); label names a, "
                "label_b names b.",
        "mesh": "assets/walk.glb", "area_m2": round(area, 1),
        "surfaces": list(game_walk.SURFACES),
        "surface_area_m2": {k: round(v, 1) for k, v in surfaces.items()},
        "wall_walks": walk_info,
        "links": [{"from": g(l["from"]), "to": g(l["to"]), "kind": l["kind"]} for l in links],
        "exits": [{"id": e["id"], "pos": g(e["pos"]), "label": e["label"], "target": e["target"]}
                  for e in game_walk.exits(plan, gate_y1)],
        "portals": [{"id": p["id"], "a": g(p["a"]), "b": g(p["b"]), "label": p["label"], "label_b": p["label_b"],
                     "seconds": p["seconds"], "sound": p["sound"], "via": p["via"]}
                    for p in game_walk.portals(plan)],
    }


# ---------- crows ----------

def export_crows(plan, out):
    """crow.glb (one perched crow, folded wings, pivots at the joints) and the perch list, with the
    plan's crow points named by location.json `perch_names`."""
    import random
    from assets import crow as crow_asset
    mats = bs.Materials()
    root = None
    for seed in range(200):
        root = crow_asset.build(bs.kit, mats, random.Random(seed))
        if root["pose"] == "alert":
            break
        for ob in [root, *root.children_recursive]:
            bpy.data.objects.remove(ob)
    root.name = "crow_export"
    for ob in bpy.data.objects:      # free the node names for this crow
        if ob.name in ("crow", "body", "head", "tail", "wing_l", "wing_r") and ob not in root.children_recursive:
            ob.name = ob.name + "_scene"
    perched = anim_crows.Perched(root, 0)
    names = {perched.head: "head", perched.tail: "tail"}
    for piv, sx in perched.wings:
        names[piv] = "wing_r" if sx > 0 else "wing_l"
        # anim_crows pivots a wing where it comes closest to the body's midline, which for folded
        # wings is the tips over the tail; a wingbeat turns about the shoulder, the wing's front end
        kids = list(piv.children)
        v = np.concatenate([anim_crows._local_verts(o) for o in kids]) + np.array(piv.location)
        shoulder = Vector(v[np.argsort(v[:, 1])[:24]].mean(0))
        bpy.context.view_layer.update()
        mw = {o: o.matrix_world.copy() for o in kids}
        piv.location = shoulder
        bpy.context.view_layer.update()
        for o in kids:
            o.matrix_world = mw[o]
    for ob, n in names.items():
        ob.name = n
    body = perched.body
    body.name = "body"
    root.name = "crow"
    mat = bpy.data.materials.new("crow_feather")
    mat.use_nodes = True
    p = mat.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (0.012, 0.012, 0.014, 1)
    p.inputs["Roughness"].default_value = 0.32
    objs = [root, *root.children_recursive]
    for ob in objs:
        if ob.type == "MESH":
            ob.data.materials.clear()
            ob.data.materials.append(mat)
    export_glb(objs, out / "assets" / "crow.glb", materials="EXPORT")
    head_h = names and perched.head.matrix_world.translation.z

    names = location.table("perch_names")
    perches = []
    for i, (x, y, z, rot) in enumerate(plan["crows"]["points"]):
        perches.append({"id": names[i] if i < len(names) else f"plan_{i}", "pos": g((x, y, z)), "yaw": float(rot),
                        "kind": "ground" if z < 0.1 else "prop"})
    taken = [Vector(p[:3]) for p in plan["crows"]["points"]]
    k = 0
    for x, y, z, rot in bs.PERCHES:
        if bs._buried(x, y, z) or any((Vector((x, y, z)) - t).length < 0.5 for t in taken):
            continue
        perches.append({"id": f"merlon_{k}", "pos": g((x, y, z)), "yaw": float(rot), "kind": "merlon"})
        k += 1
    return {
        "_doc": "crow.glb faces Godot +Z (Blender -Y) at yaw 0, feet at the origin. Perch yaw is degrees about "
                "Godot +Y (the same angle as Blender rot_z). Nodes body, head, tail, wing_l, wing_r; the "
                "pivots sit at the neck, the tail base and the shoulders.",
        "model": "assets/crow.glb", "head_height_m": round(float(head_h), 3),
        "perches": perches,
        "start": [names[i] for i in range(len(plan["crows"]["points"])) if i < len(names)],
    }


# ---------- lights ----------

def inside_wall(p, plan):
    for _, c, hs, rot, z0, z1 in block_boxes(plan):
        dx, dy = p.x - c[0], p.y - c[1]
        lx = dx * math.cos(rot) + dy * math.sin(rot)
        ly = -dx * math.sin(rot) + dy * math.cos(rot)
        if abs(lx) < hs[0] and abs(ly) < hs[1] and z0 < p.z < z1:
            return True
    return False


def export_lights(plan):
    out = []
    for ob in bpy.data.objects:
        if ob.type != "LIGHT" or ob.data.type != "POINT":
            continue
        w = ob.data.energy
        reach = ob.data.cutoff_distance if ob.data.use_custom_distance else None
        out.append({"name": ob.name, "position": g(ob.matrix_world.translation),
                    "color": [round(c, 4) for c in ob.data.color], "watts": round(w, 2),
                    # reach: the light's own cutoff, else where its irradiance falls to ~0.1 W/m^2
                    "reach_m": round(reach or min(12.0, max(2.0, math.sqrt(w / (4 * math.pi * 0.1)))), 2),
                    "radius_m": round(ob.data.shadow_soft_size, 3),
                    # inside a wall proxy box (a door or window light): it must not cast proxy shadows
                    "inside_wall": inside_wall(ob.matrix_world.translation, plan)})
    return out


# ---------- zoom views ----------

def export_views(build):
    """The zoom views written by game_views.py: wide intro view and the 2x tiles."""
    views, checks = {"_doc": "Zoom views. wide: zoom 0.5, its own camera block (same direction and image centre, "
                             "twice the coverage). tiles: zoom 2 around each hotspot; rect is in main-frame px "
                             "[x0, y0, w, h], the tile images are rect * scale px. A tile lists only the light "
                             "groups that reach it; the others are zero there (their faint rest is in its base). "
                             "Images, depth, ids and masks follow the main frame's formats."}, {}
    wide = build / "view_wide.json"
    if wide.exists():
        w = json.loads(wide.read_text())
        views["wide"] = {"camera": w["camera"], "base": w["base"], "groups": w["groups"],
                         "depth": w["depth"]["file"], "depth_meta": w["depth"], "ids": w["ids"],
                         "masks": w["masks"], "reference": w["reference"]}
        checks["wide"] = {"checks": w["checks"], "render": w["render"], "mask_stats": w["mask_stats"]}
    tiles = build / "view_tiles.json"
    if tiles.exists():
        t = json.loads(tiles.read_text())
        keys = ("id", "hotspot", "rect", "scale", "base", "groups", "depth", "ids", "masks", "reference")
        views["tiles"] = [{k: x[k] for k in keys} for x in t["tiles"]]
        checks["tiles"] = {"render": t["render"],
                           "per_tile": {x["id"]: {"checks": x["checks"], "folded_into_base": x["folded_into_base"],
                                                  "ids_pixels": x["ids_pixels"]} for x in t["tiles"]}}
    return views, checks


def prefixed(o, prefix):
    """`o` with every string that starts with "assets/" given `prefix`: the files of a location other
    than the first lie under game/locations/<name>/, and scene.json paths are relative to game/."""
    if not prefix:
        return o
    if isinstance(o, dict):
        return {k: prefixed(v, prefix) for k, v in o.items()}
    if isinstance(o, list):
        return [prefixed(v, prefix) for v in o]
    return prefix + o if isinstance(o, str) and o.startswith("assets/") else o


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    location.add_argument(ap)
    ap.add_argument("--layout", default=None, help="default: the location's layout.json")
    ap.add_argument("--out", default=None, help="game folder to write (default: location.game_dir())")
    args = ap.parse_args(argv)
    location.use(args.location)
    out = Path(args.out) if args.out else location.game_dir()

    t0 = time.time()
    for d in ("assets", "data", "build"):
        (out / d).mkdir(parents=True, exist_ok=True)
    plan, trace, layout, cam = gf.build(args.layout)
    print(f"EXPORT built scene in {time.time() - t0:.0f}s")

    cam_spec = gf.camera_block(cam, trace)
    hotspots = gf.hotspots()
    for h in hotspots:
        h["screen_px"] = gf.to_px(cam, (h["plan"]["stand_xy"][0], h["plan"]["stand_xy"][1], 0.0))
    counts, hulls = export_proxies(plan, out)
    walk = export_walk(plan, hulls, out)
    crows = export_crows(plan, out)
    srcs, _ = gf.sources()
    lights = export_lights(plan)
    owner = {li.name: d["id"] for d in srcs for li in d["lights"]}
    for li in lights:
        li["group"] = owner.get(li["name"], "base")

    build = out / "build"
    layers = json.loads((build / "layers.json").read_text())
    flip = json.loads((build / "flipbooks.json").read_text()) if (build / "flipbooks.json").exists() else {}
    # the fire flipbooks of game_fire.py (flames and their "@2" zoom versions) replace entries by id
    fire = build / "fire_flipbooks.json"
    if fire.exists():
        extra = json.loads(fire.read_text())
        extra = extra.get("flipbooks", extra) if isinstance(extra, dict) else extra
        for f in (extra.values() if isinstance(extra, dict) else extra):
            flip[f["id"]] = f
    for grp in layers["groups"]:
        grp["anchor"] = g(grp.pop("anchor_blender"))
    order = {"mist": 0, "flame": 1, "smoke": 2, "embers": 3}
    flipbooks = sorted(flip.values(), key=lambda f: (order.get(f["kind"], 9), f["id"]))
    for f in flipbooks:
        f.pop("samples", None)
        f.pop("seconds", None)
    # runtime-loaded raw files: keep the Godot editor from importing them
    for d in ("assets", "build"):
        (out / d / ".gdignore").write_text("")
    if location.name() == location.DEFAULT:
        audio = out / "assets" / "audio"
        audio.mkdir(exist_ok=True)
        for name in ("rain_bed_t1_loop", "brazier_t1_loop"):
            src = ROOT / "audio" / "sfx" / "stable-audio-3" / "norm" / f"{name}.wav"
            if src.exists():
                shutil.copyfile(src, audio / f"{name}.wav")
    views, view_checks = export_views(build)
    masks = {"puddle": "assets/masks/puddle.png", "wet": "assets/masks/wet.png",
             "normal": "assets/masks/normal.png",
             "_doc": "normal: camera-space unit normal as rgb = n * 0.5 + 0.5 (x right, y up, z toward the camera). "
                     "ids: 8-bit, 0 = nothing, k = hotspot k (1-based, hotspots.json order)"}
    if (build / "view_ids.json").exists():
        masks["ids"] = json.loads((build / "view_ids.json").read_text())["ids"]
    moon = layout["environment"]["moon"]
    moon_dir = Euler([math.radians(a) for a in moon["direction_euler"]]).to_matrix() @ Vector((0, 0, -1))

    scene = {
        "_doc": "Written by scene/export_game.py. Godot axes: godot (x, y, z) = blender (x, z, -y). Pixels: "
                "the 2560 x 1440 game frame, row 0 at the top.",
        "conversion": {"godot_from_blender": [list(r) for r in gf.TO_GODOT], "meters": 1.0},
        "camera": cam_spec,
        "depth": layers["depth"],
        "background": layers["reference"],
        "layers": {k: layers[k] for k in ("color_space", "view_transform", "look", "exposure_applied_ev", "post",
                                          "base", "groups", "reference", "reference_post")},
        "masks": masks,
        "views": views,
        "flipbooks": flipbooks,
        "crows": crows,
        "walk": walk,
        "proxy": "assets/proxy.glb", "proxy_counts": counts,
        "ambient": {"_doc": "blue-hour sky fill for real-time objects",
                    "color": layout["environment"]["sky_color"], "moon": moon,
                    "moon_direction": g(moon_dir)},
        "lights": lights,
        "checks": {"layers": layers["checks"], "mask_stats": layers["mask_stats"], "render": layers["render"],
                   "views": view_checks},
    }
    if plan.get("kind", "yard") == "room":
        scene["people"] = game_room.people()
        scene["rain"] = False          # an interior: no rain particles, no rain bed
    scene = prefixed(scene, location.rel_prefix())
    (out / "data" / "scene.json").write_text(json.dumps(scene, indent=1))
    (out / "data" / "hotspots.json").write_text(json.dumps(hotspots, indent=1, ensure_ascii=False))
    print(f"EXPORT done in {time.time() - t0:.0f}s: {counts}, {len(lights)} lights, {len(hotspots)} hotspots, "
          f"walk {walk['area_m2']} m2, {len(crows['perches'])} perches, {len(flipbooks)} flipbooks")


if __name__ == "__main__":
    main()

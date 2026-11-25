"""Walkable space, exits and people of a room (plan.json `"kind": "room"`), for export_game.py.

A room is a place whose walls are plan blocks and whose floor is `platform.polygon` at z = 0; the
camera looks into it from outside, so some of its walls are low or missing. Where a person may
walk is `platform.walk`, a polygon of its own (the inside of the room and the tongue of each door),
because the floor under the cutaway walls is not walkable. The surface underfoot is
`platform.surface`, one of game_walk.SURFACES.

Exits and people come from the location's tables (location.json `exits`, `people`); `people` are
written in Godot axes in the fields of data/npcs/<id>.json.
"""

import bmesh
import bpy

import game_walk as gw
import location
from game_frame import g


def floor(plan, hulls, coll):
    """The walk polygon as a floor mesh at z = 0 with the footprint hulls of the props cut out,
    every face carrying the room's surface."""
    slab = gw._slab("walk_floor", plan["platform"]["walk"], -0.2, 0.0, coll)
    cut = [gw._slab(f"cut_{n}", h, -1, 2, coll) for n, h, _ in hulls]
    if cut:
        gw._boolean(slab, cut, "DIFFERENCE")
    for c in cut:
        bpy.data.objects.remove(c)
    bm = bmesh.new()
    bm.from_mesh(slab.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < 0.9 or f.calc_center_median().z < -0.01],
                     context="FACES")
    # a prop that stands out from the wall can cut off a corner: keep the largest piece
    comp = gw._components(bm)
    keep = {f.index for f in max(comp, key=lambda p: sum(f.calc_area() for f in p))}
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep], context="FACES")
    bm.to_mesh(slab.data)
    bm.free()
    surface = gw.SURFACES.index(plan["platform"].get("surface", "cobble"))
    for f in slab.data.polygons:
        f.material_index = surface
    return slab


def exits():
    """walk.exits of scene.json from the location's `exits` table."""
    return [{"id": e["id"], "pos": g((*e["pos"], 0.0)), "label": e["label"], "target": e["target"]}
            for e in location.table("exits")["list"]]


def people():
    """scene.json `people`: [{id, position, face, stand, plan}] in Godot axes, floor level."""
    out = []
    for pid, p in location.table("people").items():
        if pid.startswith("_"):
            continue
        out.append({"id": pid, "position": g((*p["position"], 0.0)), "face": g((*p["face"], 1.0)),
                    "stand": g((*p["stand"], 0.0)), "plan": {k: p[k] for k in ("position", "face", "stand")}})
    return out

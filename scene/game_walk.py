"""Walkable surfaces, exits, portals and navmesh links of the game, from the real asset geometry.

walk.glb holds only surfaces a person can stand on, with the obstacle footprints already cut out
(no agent radius applied):

- the courtyard floor (plan platform at z = 0) minus the wall and tower boxes and the footprint
  hulls of the props in the body band (export_game.obstacle_hulls);
- the gate passage from the arch to the barred leaves (gate_door.DOOR_Y);
- the wall stair's 24 treads and its landing at 6.0 m (assets/wall_stair.py);
- the curtain wall-walks at 6 m: the top of every curtain block (plan heights "curtain") behind
  its parapet (merlon depth), minus the towers and the gatehouse, the door cases of the NW and NE
  tower doors and the props that stand on them. The north curtain lies wholly inside the NW
  tower, the gatehouse and the NE tower, so it adds nothing. Two walks remain: the west curtain
  from the NW tower door to the curtain's south end, and the east chamfer, east curtain and
  south-east curtain from the NE tower door to where the wall steps down to 3 m;
- the gallows stair's 6 treads and its deck at 1.6 m, without the two posts (assets/gallows.py).

Every face carries a material named after what is underfoot (SURFACES): the floor is cut into
CELL-sized squares and each takes the ground material's own maps (mats/cobble_wet.py) under it:
`mud` where the mud covers the setts (macro mud, tracked mud, packed earth), `straw` where straw
is trodden in, else `cobble`. Stair treads are `stone_stair`, the landing and the wall-walks
`stone_walk`, the gallows stair and deck `wood`. Puddles are not a face type: the runtime reads
the puddle mask under the figure.

Stairs are treads, so a navmesh needs a step height of at least the riser (0.25 m wall stair,
0.23 m gallows). `links` join the foot and the top of each stair for runtimes that would rather
link than climb.

Portals. The NW tower door at the stair landing and the NE tower door on the east chamfer are
the two ends of one way through the towers: in at one door, through the NW tower, the gatehouse
at wall-walk level and the NE tower, and out at the other (the wall-walk is continuous through
the gatehouse; AGENTS.md, consistency rules).
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from assets import gallows as G
from assets import gate_door as GD
from assets import lit_door as LD
from assets import wall_stair as WS
import location
from planlib import inside_polygon as _inside

SURFACES = ("cobble", "mud", "straw", "stone_stair", "stone_walk", "wood")
SURFACE_COLORS = {"cobble": (0.45, 0.47, 0.52), "mud": (0.36, 0.25, 0.10), "straw": (0.85, 0.72, 0.25),
                  "stone_stair": (0.55, 0.55, 0.62), "stone_walk": (0.30, 0.55, 0.85), "wood": (0.65, 0.35, 0.15)}
CELL = 0.5               # floor cells for the surface type, metres
# thresholds on the ground maps at the middle of the material's noise (mats/cobble_wet.build)
MUD_AT = 0.57            # macro mud field: MUD_EDGE (0.52, 0.62)
TRACK_AT = 0.38          # tracked mud x 1.25: track_cov range (0.26, 0.50)
EARTH_AT = 0.485         # packed earth: range (0.42, 0.55)
STRAW_AT = 0.35          # straw density: strands appear from 0.06, full at 0.45
WALK_TOP = 6.0           # curtain wall-walk level (plan heights "curtain")

# door openings in the floor that are cut out of the walls (x0, x1, y0, y1) in world metres
GATE_X = (-1.15 - GD.HALF + 0.05, -1.15 + GD.HALF - 0.05)


def _prop(plan, key):
    p = plan["props"][key]
    return Matrix.Translation((*p["pos"], 0.0)) @ Matrix.Rotation(math.radians(p.get("rot_z", 0)), 4, "Z")


def _quad(bm, m, x0, x1, y0, y1, z, surface="cobble"):
    vs = [bm.verts.new(m @ Vector((x, y, z))) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    f = bm.faces.new(vs)
    if f.normal.z < 0:
        f.normal_flip()
    f.material_index = SURFACES.index(surface)
    return f


def surface_materials(obs):
    """One material per surface type, named exactly as in SURFACES, on every walk mesh (in that
    order, so a face's material_index is SURFACES.index). Scene materials of the same name are
    renamed while the walk exists; returns the renames for restore_names()."""
    renamed = []
    mats = []
    for name in SURFACES:
        old = bpy.data.materials.get(name)
        if old is not None and not old.get("walk_surface"):
            old.name = f"{name}__scene"
            renamed.append((old, name))
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m["walk_surface"] = True
        m.diffuse_color = (*SURFACE_COLORS[name], 1.0)
        mats.append(m)
    for ob in obs:
        me = ob.data
        index = [f.material_index for f in me.polygons]      # clearing the slots resets them
        me.materials.clear()
        for m in mats:
            me.materials.append(m)
        me.polygons.foreach_set("material_index", index)
        me.update()
    return renamed


def restore_names(renamed):
    for m, name in renamed:
        mine = bpy.data.materials.get(name)
        if mine is not None:
            mine.name = f"walk_{name}"
        m.name = name


def _components(bm):
    """Faces of a bmesh in edge-connected groups."""
    bm.faces.ensure_lookup_table()
    comp, seen = [], set()
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, part = [f], []
        seen.add(f.index)
        while stack:
            c = stack.pop()
            part.append(c)
            for e in c.edges:
                for o in e.link_faces:
                    if o.index not in seen:
                        seen.add(o.index)
                        stack.append(o)
        comp.append(part)
    return comp


def _slab(name, poly, z0, z1, coll):
    """Closed prism over a polygon, for booleans."""
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


def _boolean(target, cutters, op):
    for i, c in enumerate(cutters):
        mod = target.modifiers.new(f"b{i}", "BOOLEAN")
        mod.operation = op
        mod.solver = "EXACT"
        mod.object = c
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier=mod.name)


def floor(plan, walls, hulls, coll):
    """Courtyard floor: the platform slab minus walls and prop footprints, plus the gate passage."""
    poly = plan["platform"]["polygon"]
    slab = _slab("walk_floor", poly, -0.2, 0.0, coll)
    gate_y1 = 3.0 + GD.DOOR_Y - 0.05
    cut = [_slab(f"cut_{n}", p, -1, 2, coll) for n, p in walls]
    cut += [_slab(f"cut_{n}", h, -1, 2, coll) for n, h, _ in hulls]
    # the guardroom door case: two jambs standing 0.62 m out from the NE tower's face
    for x0, x1 in ((3.15, 3.6), (4.6, 5.05)):
        cut.append(_slab("cut_door_jamb", [(x0, 1.98), (x1, 1.98), (x1, 2.6), (x0, 2.6)], -1, 2, coll))
    _boolean(slab, cut, "DIFFERENCE")
    passage = _slab("walk_passage", [(GATE_X[0], 2.9), (GATE_X[1], 2.9), (GATE_X[1], gate_y1),
                                     (GATE_X[0], gate_y1)], -0.2, 0.0, coll)
    _boolean(slab, [passage], "UNION")
    for c in cut + [passage]:
        bpy.data.objects.remove(c)
    # keep the top faces only
    bm = bmesh.new()
    bm.from_mesh(slab.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < 0.9 or f.calc_center_median().z < -0.01],
                     context="FACES")
    # keep the courtyard: the platform's strips outside the walls (west ledge, bridge abutment, the
    # ground south of the parapet) are not connected to it
    comp = _components(bm)
    keep = max(comp, key=lambda p: sum(f.calc_area() for f in p))
    keep_ids = {f.index for f in keep}
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep_ids], context="FACES")
    bm.to_mesh(slab.data)
    bm.free()
    return slab, gate_y1


def stairs(plan, coll):
    """Wall stair and landing; gallows treads and deck. One mesh."""
    bm = bmesh.new()
    links = []
    # wall stair: tread k (1..24) has its top at k * RISE; the 24th tread is the landing
    m = _prop(plan, "wall_stair")
    for k in range(1, WS.RISERS + 1):
        x_a = WS.RISER_X[k - 1] - WS.NOSE
        x_b = WS.RISER_X[k] if k < WS.RISERS else WS.X1
        _quad(bm, m, x_a, x_b, WS.Y_OPEN, WS.Y_WALL, WS.RISE * k,
              "stone_walk" if k == WS.RISERS else "stone_stair")
    top = WS.RISE * WS.RISERS
    links.append(dict(**{"from": m @ Vector((WS.RISER_X[0] - 0.3, 0.0, 0.0)),
                         "to": m @ Vector(((WS.RISER_X[-1] + WS.X1) / 2, 0.0, top))}, kind="stair"))
    door = door_case(plan, "lit_door#2")

    # gallows: treads 1..6 west of the deck, then the deck without the two posts
    m = _prop(plan, "gallows")
    for i in range(1, G.STAIR_STEPS):
        xc = -G.HX - (6.5 - i) * G.STAIR_RUN
        _quad(bm, m, xc - G.STAIR_RUN / 2, xc + G.STAIR_RUN / 2, G.STAIR_Y - G.STAIR_W / 2,
              G.STAIR_Y + G.STAIR_W / 2, i * G.STAIR_RISE, "wood")
    deck = bmesh.new()
    xs = [-G.HX, -G.POST_X - G.POST_W / 2, -G.POST_X + G.POST_W / 2, G.POST_X - G.POST_W / 2,
          G.POST_X + G.POST_W / 2, G.HX]
    ys = [-G.HY, G.POST_Y - G.POST_W / 2, G.POST_Y + G.POST_W / 2, G.HY]
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            post = i in (1, 3) and j == 1
            if not post:
                _quad(bm, m, xs[i], xs[i + 1], ys[j], ys[j + 1], G.DECK_TOP, "wood")
    deck.free()
    foot = -G.HX - 6 * G.STAIR_RUN
    links.append(dict(**{"from": m @ Vector((foot - 0.3, G.STAIR_Y, 0.0)),
                         "to": m @ Vector((-G.HX + 0.4, G.STAIR_Y, G.DECK_TOP))}, kind="stair"))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    me = bpy.data.meshes.new("walk_stairs")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("walk_stairs", me)
    coll.objects.link(ob)
    return ob, links, dict(nw_door=door["threshold"])


def exits(plan, gate_y1):
    """Doors to locations not built yet. The NW tower door is a portal (portals()), not an exit."""
    shed = plan["props"]["shed"]["pos"]
    stable = plan["props"]["stable"]["pos"]
    guard = plan["mounted"]["lit_door"]["pos"]
    out = [
        dict(id="gate_out", pos=(-1.15, gate_y1 - 0.25, 0.0), label="Out to the road", target="road"),
        dict(id="guardroom_door", pos=(guard[0], guard[1] - 0.75, 0.0), label="Guardroom", target="guardroom"),
        dict(id="cookhouse", pos=(shed[0] + 0.6, shed[1] - 2.15 - 0.35, 0.0), label="Cookhouse", target="cookhouse"),
        dict(id="stable", pos=(stable[0] - 2.0, stable[1], 0.0), label="Stable", target="stable"),
    ]
    # exits of location.json's `exits` table: doors that are not tied to a prop (the way to the commander's tower)
    for e in location.load("location.json").get("exits", {}).get("list", []):
        out.append(dict(id=e["id"], pos=(e["pos"][0], e["pos"][1], 0.0), label=e["label"], target=e["target"]))
    return out


# ---------- door cases, wall-walks, portals ----------

def door_case(plan, key):
    """A mounted lit_door on a tower face (wall face toward -Y, rot_z 0): its two jamb footprints
    and the threshold point inside the opening."""
    m = plan["mounted"][key]
    s = m.get("scale", 1.0)
    x, y, z = m["pos"]
    case_half = (LD.HALF + max(LD.JAMB_W)) * s
    half, depth = LD.HALF * s, LD.DEPTH * s
    jambs = [[(x0, y - depth), (x1, y - depth), (x1, y), (x0, y)]
             for x0, x1 in ((x - case_half, x - half), (x + half, x + case_half))]
    return {"jambs": jambs, "threshold": (x, y - 0.25, z), "front": (x, y - depth - 0.35, z)}


def _top_faces(ob, z_min):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < 0.9 or f.calc_center_median().z < z_min],
                     context="FACES")
    bmesh.ops.dissolve_limit(bm, angle_limit=0.01, verts=bm.verts, edges=bm.edges)
    bm.to_mesh(ob.data)
    bm.free()


def wall_walks(plan, boxes, coll, obstacles=()):
    """The curtain wall-walks at WALK_TOP behind the parapets, minus towers, gatehouse, door cases
    and `obstacles` (footprints of props standing on the walk). boxes: export_game.block_boxes."""
    md = plan["merlon"]["depth"]
    walks, cut = [], []
    for name, c, hs, rot, z0, z1 in boxes:
        b = plan["blocks"][name]
        edges = b.get("merlons", [])
        if "all" in edges:
            edges = ["+x", "-x", "+y", "-y"]
        cr, sr = math.cos(rot), math.sin(rot)

        def poly(x0, x1, y0, y1):
            return [(c[0] + x * cr - y * sr, c[1] + x * sr + y * cr) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        if z1 > WALK_TOP + 0.3:
            cut.append((f"tall_{name}", poly(-hs[0], hs[0], -hs[1], hs[1])))
            continue
        if abs(z1 - WALK_TOP) > 0.05 or "from" in b:
            continue
        x0, x1, y0, y1 = -hs[0], hs[0], -hs[1], hs[1]
        x0 += md * ("-x" in edges)
        x1 -= md * ("+x" in edges)
        y0 += md * ("-y" in edges)
        y1 -= md * ("+y" in edges)
        walks.append((name, poly(x0, x1, y0, y1), WALK_TOP))   # one level, so the walks join (h_offset differs by mm)
        # this curtain's parapets also stand where another curtain's walk overlaps it
        for e in edges:
            strip = {"+x": (hs[0] - md, hs[0], -hs[1], hs[1]), "-x": (-hs[0], -hs[0] + md, -hs[1], hs[1]),
                     "+y": (-hs[0], hs[0], hs[1] - md, hs[1]), "-y": (-hs[0], hs[0], -hs[1], -hs[1] + md)}[e]
            cut.append((f"parapet_{name}_{e}", poly(*strip)))
    for key in ("lit_door#2", "lit_door#3"):
        for i, j in enumerate(door_case(plan, key)["jambs"]):
            cut.append((f"jamb_{key}_{i}", j))
    cut += [(f"obstacle_{n}", h) for n, h in obstacles if any(_overlap(h, w) for _, w, _ in walks)]
    if not walks:
        return None, {}
    target = _slab("walk_walls", walks[0][1], walks[0][2] - 0.2, walks[0][2], coll)
    rest = [_slab(f"walk_{n}", p, z - 0.2, z, coll) for n, p, z in walks[1:]]
    _boolean(target, rest, "UNION")
    cutters = [_slab(f"cut_{n}", p, WALK_TOP - 1.0, WALK_TOP + 3.0, coll) for n, p in cut]
    _boolean(target, cutters, "DIFFERENCE")
    for o in rest + cutters:
        bpy.data.objects.remove(o)
    _top_faces(target, WALK_TOP - 0.5)
    for f in target.data.polygons:
        f.material_index = SURFACES.index("stone_walk")
    # slivers left between the cutters (under 0.5 m2) are no place to stand
    bm = bmesh.new()
    bm.from_mesh(target.data)
    parts = [(sum(f.calc_area() for f in part), part) for part in _components(bm)]
    bmesh.ops.delete(bm, geom=[f for a, part in parts if a < 0.5 for f in part], context="FACES")
    bm.to_mesh(target.data)
    bm.free()
    parts = sorted((round(a, 1) for a, _ in parts if a >= 0.5), reverse=True)
    return target, {"walks": [n for n, _, _ in walks], "cut": [n for n, _ in cut if not n.startswith("parapet")],
                    "pieces_m2": parts}


def _overlap(p, q):
    """Two simple polygons share area or touch (vertex inside, or crossing edges)."""
    from mathutils.geometry import intersect_line_line_2d
    if any(_inside(x, y, q) for x, y in p) or any(_inside(x, y, p) for x, y in q):
        return True
    for i in range(len(p)):
        for j in range(len(q)):
            if intersect_line_line_2d(p[i], p[(i + 1) % len(p)], q[j], q[(j + 1) % len(q)]):
                return True
    return False


def portals(plan):
    """The way through the towers between the two wall-walk doors (see the module doc)."""
    nw, ne = door_case(plan, "lit_door#2"), door_case(plan, "lit_door#3")
    return [dict(id="nw_tower", a=nw["threshold"], b=ne["threshold"], label="North-west tower",
                 label_b="North-east tower", seconds=3.0, sound="door_heavy",
                 via=["nw_tower", "gatehouse", "ne_tower"])]


# ---------- surface types of the floor ----------

def floor_surfaces(ob, plan):
    """Cut the floor into CELL squares and give each the surface the ground material shows there."""
    import numpy as np
    from mats import cobble_wet as cw
    M = cw.ground_maps(plan)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    for axis, lo, hi in ((0, min(xs), max(xs)), (1, min(ys), max(ys))):
        k = math.floor(lo / CELL) + 1
        while k * CELL < hi:
            no = (1, 0, 0) if axis == 0 else (0, 1, 0)
            co = (k * CELL, 0, 0) if axis == 0 else (0, k * CELL, 0)
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=co, plane_no=no)
            k += 1

    def sample(name, x, y):
        a = M[name]
        c = np.clip(((x - cw.MAP_X0) * cw.PPM - 0.5).astype(int), 0, a.shape[1] - 1)
        r = np.clip(((y - cw.MAP_Y0) * cw.PPM - 0.5).astype(int), 0, a.shape[0] - 1)
        return a[r, c]
    counts = {n: 0.0 for n in SURFACES}
    for f in bm.faces:
        bx = [v.co.x for v in f.verts]
        by = [v.co.y for v in f.verts]
        g = np.linspace(0.1, 0.9, 5)
        X = (min(bx) + g[None, :] * (max(bx) - min(bx))).repeat(5, 0).ravel()
        Y = (min(by) + g[:, None] * (max(by) - min(by))).repeat(5, 1).ravel()
        mud = ((sample("mud", X, Y) > MUD_AT) | (sample("earth", X, Y) > EARTH_AT)
               | (sample("track", X, Y) * 1.25 > TRACK_AT)).mean()
        straw = (sample("straw", X, Y) > STRAW_AT).mean()
        kind = "straw" if straw >= 0.5 else "mud" if mud >= 0.5 else "cobble"
        f.material_index = SURFACES.index(kind)
        counts[kind] += f.calc_area()
    bm.to_mesh(ob.data)
    bm.free()
    return {k: round(v, 1) for k, v in counts.items() if v}

"""Approach to the north gate: a timber trestle bridge from the gate apron to the ridge, and the muddy track on both ends.

The gate floor is at z = 0 and the ground outside is 2-3 m lower, in a dip between the castle's mound
and the ridge of the tree line hill (see `treeline.py`), whose crest is about as high as the gate floor.
A level trestle bridge spans the dip: stringers rest on a bed course in the north face of a masonry
abutment in front of the gate, three bents carry them over the low ground and an end sill rests on the
hill's slope. A bridge
is what a small outpost would build, because it is cheap, needs no fill and can be burned.

Origin: the gate axis on the outer face of the gatehouse (world x = -1.15, y = 6.6), at gate floor
level. +Y points north, away from the castle. Place it with "pos": [-1.15, 6.6], "z": 0 and list it
after the trees in plan.json "props": the ground heights below are computed for that position,
and build() removes trees, bushes and tufts from the corridor of the road so none grows through
the deck.

From the castle outward:

- y 0 to 2.4: the abutment. Its top is the floor polygon's apron (cobbles at floor level) with a worn
  mud track on it; wing walls with coping line both sides and end in piers at the bridge; its foot is
  battered out into the mound.
- y 2.4 to about 12.4: the bridge. Plank deck on four stringers, kerbs, posts and rails, three trestle
  bents with stone footings, cross braces and longitudinal braces, and a log sill at the far end.
- beyond the bridge: a rutted mud track over the hill's crest, following its surface.
- a bank of ground fog north of the castle (`FOG`) that is clear at the gatehouse and thick at the tree
  line.
"""

import math

import bmesh
import bpy
from mathutils import Vector, noise

ORIGIN = (-1.15, 6.6)          # world x, y of the prop root
LOWER_WARD = -3.0
HILL = (0.0, 17.0)             # world x, y of the treeline prop (hill ground comes from its hill_height)
EDGE = 2.4                     # local y of the platform's north edge: the bridge starts here
WIDTH = 3.9                    # deck width
PLANK = 0.07                   # deck plank thickness
STRINGER = (0.20, 0.27)        # stringer section, width and height
CAP = 0.26                     # cap beam height
BENT_X = 1.45                  # trestle posts stand this far either side of the axis
BENT_GAP = 2.6                 # distance between bents
CLEAR = ((-5.7, 2.4), (11.8, 26.0))   # world x and y range cleared of trees and bushes
RAIL_Z = 1.0
ABUT_HALF = 2.6                # half width of the abutment (the floor polygon's apron: world x -3.75 to 1.45)
BATTER = 0.75                  # how far the abutment's battered foot spreads beyond its upright face
BATTER_TOP = -1.1              # height where the batter leaves the upright face
WING_T, WING_H = 0.45, 0.95    # wing walls on the abutment: thickness and height under the coping

LIGHTS = []   # nothing burns outside the walls

def _terrain_z(x, y):
    """World height of the outside ground: the mound at the wall feet and the mud plain (terrain.py)."""
    import terrain
    return terrain.ground_z(x, y)


def _hill_z(x, y):
    """World height of the tree line hill; far below the ground where it does not reach."""
    try:
        from . import treeline
        return LOWER_WARD + treeline.hill_height(x - HILL[0], y - HILL[1]) - 0.02
    except (ImportError, AttributeError):
        return -99.0


def _ground(x, y):
    """World height of the ground at world (x, y)."""
    return max(_terrain_z(x, y), _hill_z(x, y))


def _ground_local(x, y):
    return _ground(ORIGIN[0] + x, ORIGIN[1] + y)


def _bridge_end():
    """Local y where the hill's slope reaches the deck level along the axis."""
    y = 9.0
    while y < 14.0:
        if _ground_local(0.0, y) >= -0.12:
            return y
        y += 0.05
    return 12.4


# ---------- clearing ----------

def _in_corridor(x, y, margin=0.0):
    return CLEAR[0][0] - margin <= x <= CLEAR[0][1] + margin and CLEAR[1][0] - margin <= y <= CLEAR[1][1] + margin


def _clear_props():
    """Remove trees, bushes and tufts standing in the corridor (their roots are the `prop_*` empties)."""
    roots = [ob.name for ob in bpy.data.objects
             if ob.type == "EMPTY" and ob.name.split("#")[0] in ("prop_tree", "prop_dead_bush", "prop_grass_tuft")
             and _in_corridor(ob.location.x, ob.location.y)]
    for name in roots:
        ob = bpy.data.objects.get(name)
        if ob is None:
            continue
        for child in ob.children_recursive:
            bpy.data.objects.remove(child, do_unlink=True)
        bpy.data.objects.remove(ob, do_unlink=True)


def _clear_treeline():
    """Remove the trees of the tree line hill whose trunk stands in the corridor, island by island."""
    ob = bpy.data.objects.get("treeline_trees")
    if ob is None or ob.parent is None:
        return
    off = ob.parent.location
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    seen = set()
    doomed = []
    for v0 in bm.verts:
        if v0.index in seen:
            continue
        stack, island = [v0], []
        seen.add(v0.index)
        while stack:
            v = stack.pop()
            island.append(v)
            for e in v.link_edges:
                w = e.other_vert(v)
                if w.index not in seen:
                    seen.add(w.index)
                    stack.append(w)
        base = min(island, key=lambda v: v.co.z)
        if _in_corridor(base.co.x + off.x, base.co.y + off.y):
            doomed.extend(island)
    if doomed:
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
        bm.to_mesh(ob.data)
        ob.data.update()
    bm.free()


# ---------- mud track ----------

def _ribbon(kit, mats, root, name, y0, y1, half_width, center, ground, hump=0.04, rut=0.045):
    """Muddy track as a height field: crowned, with two wheel ruts, dipping below the ground at its edges.

    `center(y)` is the local x of the track axis, `half_width(y)` its half width and `ground(x, y)` the
    local height of the surface it lies on.
    """
    rows = max(2, int((y1 - y0) / 0.12))
    cols = 18
    verts, faces = [], []
    for j in range(rows + 1):
        y = y0 + (y1 - y0) * j / rows
        xc, hw = center(y), half_width(y)
        for i in range(cols + 1):
            u = -1.0 + 2.0 * i / cols
            x = xc + u * hw
            ruts = -rut * math.exp(-((abs(x - xc) - 0.66) / 0.15) ** 2)
            lumps = 0.022 * noise.noise(Vector((x * 2.3, y * 2.3, 5.0)))
            z = ground(x, y) + 0.014 + hump * (1 - u * u) + ruts + lumps - 0.075 * u ** 6
            verts.append((x, y, z))
    for j in range(rows):
        for i in range(cols):
            a = j * (cols + 1) + i
            faces.append((a, a + 1, a + cols + 2, a + cols + 1))
    ob = kit.mesh(name, verts, faces, mat=mats["mud"], parent=root)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


# ---------- bridge ----------

def _deck(kit, mats, rng, root, y0, y1):
    wood, new_wood = mats["wood_old"], mats["door_wood"]
    # stringers: four beams from the retaining wall to the end sill
    for i, x in enumerate((-1.35, -0.45, 0.45, 1.35)):
        kit.box(f"stringer_{i}", (STRINGER[0], y1 - y0 + 0.4, STRINGER[1]),
                (x, (y0 + y1) / 2 - 0.2, -PLANK - STRINGER[1] / 2), mat=mats["wood_dark"], bevel=0.01, parent=root)
    # planks across the beams, with gaps; a few are newer repairs
    y = y0 + 0.02
    k = 0
    missing = {rng.randrange(14, 24), rng.randrange(26, 33)}   # planks that have rotted out
    while y < y1 - 0.1:
        w = rng.uniform(0.21, 0.29)
        mat = new_wood if rng.random() < 0.12 else wood
        if k in missing:
            y += w + 0.02
            k += 1
            continue
        kit.box(f"plank_{k}", (WIDTH + kit.jitter(rng, 0.03), w, PLANK),
                (kit.jitter(rng, 0.015), y + w / 2, -PLANK / 2 + kit.jitter(rng, 0.005)),
                (0, kit.jitter(rng, 0.3), kit.jitter(rng, 0.5)), mat=mat, bevel=0.006, parent=root)
        y += w + rng.uniform(0.012, 0.024)
        k += 1
    # kerbs keep the wheels on the deck
    for side in (-1, 1):
        kit.box(f"kerb_{side}", (0.18, y1 - y0 - 0.1, 0.18), (side * (WIDTH / 2 - 0.12), (y0 + y1) / 2, 0.09),
                mat=mats["wood_dark"], bevel=0.012, parent=root)


def _bent(kit, mats, rng, root, y):
    """Trestle bent: two round posts on stone footings, a cap beam and cross braces."""
    dark, iron = mats["wood_dark"], mats["iron"]
    stone = _dressed(mats["stone_wall"])
    cap_top = -PLANK - STRINGER[1]
    cap_mid = cap_top - CAP / 2
    kit.box("cap", (2 * BENT_X + 0.5, 0.30, CAP), (0, y, cap_mid), mat=dark, bevel=0.012, parent=root)
    tops = {}
    for side in (-1, 1):
        x = side * BENT_X
        zg = _ground_local(x, y)
        bottom = zg + 0.10                      # the post stands on its footing stone
        top = cap_top - CAP
        h = top - bottom
        tops[side] = zg
        kit.cylinder(f"post_{side}", 0.17, h, (x, y, bottom + h / 2), mat=dark, segments=8, radius_top=0.15,
                     parent=root)
        kit.box(f"footing_{side}", (0.75, 0.65, 0.24), (x, y, zg), (0, 0, kit.jitter(rng, 8)),
                mat=stone, bevel=0.02, parent=root)
        kit.box(f"strap_{side}", (0.34, 0.07, 0.5), (x, y - 0.17, top + 0.1), mat=iron, bevel=0.006, parent=root)
    # cross braces in the plane of the bent, when the posts are tall enough to need them
    low = max(tops.values())
    if cap_top - CAP - low > 1.0:
        a = low + 0.3
        b = cap_top - CAP - 0.35
        kit.beam("xbrace_a", (-BENT_X, y - 0.18, tops[-1] + 0.3), (BENT_X, y - 0.18, b), section=(0.12, 0.12),
                 mat=dark, bevel=0.008, parent=root)
        kit.beam("xbrace_b", (BENT_X, y + 0.18, tops[1] + 0.3), (-BENT_X, y + 0.18, b), section=(0.12, 0.12),
                 mat=dark, bevel=0.008, parent=root)
        kit.box("ledger", (2 * BENT_X, 0.13, 0.14), (0, y, (a + b) / 2), mat=dark, bevel=0.01, parent=root)


def _braces(kit, mats, root, ys):
    """Diagonal braces along each side, from the foot of one bent to the cap of the next."""
    dark = mats["wood_dark"]
    for side in (-1, 1):
        x = side * (BENT_X + 0.2)
        for k in range(len(ys) - 1):
            y0, y1 = ys[k], ys[k + 1]
            z0, z1 = _ground_local(x, y0), _ground_local(x, y1)
            top = -PLANK - STRINGER[1] - CAP - 0.25
            if top - max(z0, z1) < 1.0:
                continue
            kit.beam(f"brace_{side}_{k}", (x, y0, z0 + 0.5), (x, y1, top), section=(0.11, 0.11), mat=dark,
                     bevel=0.008, parent=root)


def _railings(kit, mats, rng, root, ys):
    """Posts at every bent and two rails between them; one bay has lost its rails."""
    dark = mats["wood_dark"]
    gap_side, gap_bay = rng.choice((-1, 1)), rng.randrange(1, max(2, len(ys) - 1))
    for side in (-1, 1):
        x = side * (WIDTH / 2 - 0.02)
        for k, y in enumerate(ys):
            lean = kit.jitter(rng, 2.5) if (side == gap_side and k in (gap_bay, gap_bay + 1)) else kit.jitter(rng, 0.8)
            kit.box(f"rail_post_{side}_{k}", (0.15, 0.15, RAIL_Z + 0.4), (x, y, RAIL_Z / 2 - 0.2 + 0.0),
                    (lean, kit.jitter(rng, 1.0), 0), mat=dark, bevel=0.01, parent=root)
        for k in range(len(ys) - 1):
            if side == gap_side and k == gap_bay:
                # the rails hang from one post, their free ends dropped
                kit.beam(f"rail_hi_{side}_{k}", (x, ys[k], RAIL_Z - 0.05), (x, ys[k] + 0.9, RAIL_Z - 0.55),
                         section=(0.09, 0.09), mat=dark, bevel=0.008, parent=root)
                continue
            for z, tag in ((RAIL_Z - 0.05, "hi"), (RAIL_Z * 0.5, "lo")):
                kit.beam(f"rail_{tag}_{side}_{k}", (x, ys[k], z), (x, ys[k + 1], z + kit.jitter(rng, 0.03)),
                         section=(0.09, 0.09), mat=dark, bevel=0.008, parent=root)


def _deck_mud(kit, mats, rng, root, y0, y1):
    """Mud tracked onto the planks: smears along the wheel paths, thickest toward the apron end."""
    mud = mats["mud"]
    y = y0 + 0.2
    while y < y1 - 0.3:
        fade = 1.0 - 0.7 * (y - y0) / (y1 - y0)
        for x in (-0.66, 0.66):
            if rng.random() < 0.75 * fade + 0.1:
                r = rng.uniform(0.07, 0.14)
                kit.sphere("deck_mud", r, (x + kit.jitter(rng, 0.14), y + kit.jitter(rng, 0.1), 0.0),
                           scale=(rng.uniform(0.6, 1.0), rng.uniform(1.8, 3.6), rng.uniform(0.05, 0.10)),
                           mat=mud, segments=8, parent=root)
        y += rng.uniform(0.3, 0.6)


# ---------- abutment ----------

def _abutment(kit, mats, rng, root):
    """Masonry abutment in front of the gate: the bridge's first support and the gate's forecourt.

    Its top is the floor polygon's apron (cobbles at gate floor level) and its upright faces are the
    polygon's sides. Here: a battered foot that spreads into the mound, two wing walls with coping
    that butt against the gatehouse and end in piers at the bridge, and a projecting bed course in the
    north face that the stringers rest on.
    """
    stone = mats["stone_wall"]
    dressed = _dressed(stone)
    h, b, z0, zb = ABUT_HALF, BATTER, BATTER_TOP, LOWER_WARD - 0.6
    # battered foot: a frustum from the upright faces at z0 down and out to below the ground; its back
    # half runs into the gatehouse's own plinth
    top = [(-h, -0.3, z0), (h, -0.3, z0), (h, EDGE, z0), (-h, EDGE, z0)]
    bot = [(-h - b, -0.3, zb), (h + b, -0.3, zb), (h + b, EDGE + b, zb), (-h - b, EDGE + b, zb)]
    faces = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)]
    kit.mesh("abutment_batter", top + bot, faces, mat=stone, bevel=0.03, parent=root)
    # bed course under the stringer ends
    seat_z = -PLANK - STRINGER[1] - 0.17
    kit.box("abutment_seat", (2 * h - 0.4, 0.42, 0.34), (0, EDGE + 0.2, seat_z), mat=dressed, bevel=0.02,
            parent=root)
    # wing walls with coping, ending in a pier at the bridge
    for side in (-1, 1):
        x = side * (h - WING_T / 2)
        kit.box(f"wing_{side}", (WING_T, EDGE - 0.3, WING_H), (x, (EDGE - 0.3) / 2, WING_H / 2), mat=stone,
                bevel=0.02, parent=root)
        k, y = 0, 0.0
        while y < EDGE - 0.35:
            ln = min(rng.uniform(0.45, 0.8), EDGE - 0.3 - y)
            kit.box(f"wing_cope_{side}_{k}", (WING_T + 0.1, ln - 0.012, 0.13),
                    (x + kit.jitter(rng, 0.01), y + ln / 2, WING_H + 0.065), (0, 0, kit.jitter(rng, 1.0)),
                    mat=dressed, bevel=0.015, parent=root)
            y += ln
            k += 1
        kit.box(f"wing_pier_{side}", (0.62, 0.62, WING_H + 0.32), (x + side * 0.04, EDGE - 0.31, (WING_H + 0.32) / 2),
                mat=dressed, bevel=0.02, parent=root)
        kit.box(f"wing_pier_cap_{side}", (0.72, 0.72, 0.12), (x + side * 0.04, EDGE - 0.31, WING_H + 0.38),
                mat=dressed, bevel=0.02, parent=root)


# ---------- fog ----------

FOG = True                     # a bank of ground fog north of the castle that thickens with distance
FOG_Y = (11.0, 60.0)           # world y range of the bank
FOG_DENSITY = 0.11             # per meter at the ground, where the bank is fully developed
FOG_COLOR = (0.40, 0.45, 0.54)


def _fog(kit, root):
    """Bounded volume over the ground north of the castle: clear at the gatehouse, thick at the tree line.

    The camera never looks into the castle through it, so it only veils the hill, the trees and the bridge's
    far end. Density rises with distance from the castle and falls off with height above the lower ward.
    """
    x0, x1 = -48.0 - ORIGIN[0], 48.0 - ORIGIN[0]
    y0, y1 = FOG_Y[0] - ORIGIN[1], FOG_Y[1] - ORIGIN[1]
    z0, z1 = LOWER_WARD - 0.5, 10.0
    box = kit.box("fog_bank", (x1 - x0, y1 - y0, z1 - z0), ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
                  parent=root)
    mat = bpy.data.materials.new("fog_bank")
    nt = mat.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])

    def node(kind, **attrs):
        n = nt.nodes.new(kind)
        for k, v in attrs.items():
            setattr(n, k, v)
        return n

    geo = node("ShaderNodeNewGeometry")
    sep = node("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])

    def rng_node(src, lo, hi, to_lo, to_hi):
        m = node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
        for sock, v in zip(("From Min", "From Max", "To Min", "To Max"), (lo, hi, to_lo, to_hi)):
            m.inputs[sock].default_value = v
        nt.links.new(src, m.inputs["Value"])
        return m.outputs["Result"]

    along = rng_node(sep.outputs["Y"], FOG_Y[0], FOG_Y[0] + 26.0, 0.0, 1.0)
    # height: dense in the low ground, thin by the time it reaches the wall tops
    height = rng_node(sep.outputs["Z"], LOWER_WARD, LOWER_WARD + 9.0, 1.0, 0.04)
    cloud = node("ShaderNodeTexNoise")
    cloud.inputs["Scale"].default_value = 0.07
    cloud.inputs["Detail"].default_value = 3.0
    nt.links.new(geo.outputs["Position"], cloud.inputs["Vector"])
    patchy = rng_node(cloud.outputs["Fac"], 0.3, 0.7, 0.55, 1.4)
    dens = node("ShaderNodeMath", operation="MULTIPLY")
    nt.links.new(along, dens.inputs[0])
    nt.links.new(height, dens.inputs[1])
    dens2 = node("ShaderNodeMath", operation="MULTIPLY")
    nt.links.new(dens.outputs[0], dens2.inputs[0])
    nt.links.new(patchy, dens2.inputs[1])
    gain = node("ShaderNodeMath", operation="MULTIPLY")
    nt.links.new(dens2.outputs[0], gain.inputs[0])
    gain.inputs[1].default_value = FOG_DENSITY
    vol = node("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (*FOG_COLOR, 1.0)
    vol.inputs["Anisotropy"].default_value = 0.3
    nt.links.new(gain.outputs[0], vol.inputs["Density"])
    nt.links.new(vol.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    box.data.materials.append(mat)
    box.visible_shadow = False
    return box


def _dressed(mat):
    from assets.gate_door import _dressed as dressed
    return dressed(mat)


def build(kit, mats, rng):
    root = kit.group("road")
    _clear_props()
    bpy.context.view_layer.update()
    _clear_treeline()

    y_end = _bridge_end()

    # worn mud over the cobbles of the apron
    def apron_center(y):
        return 0.0

    def apron_half(y):
        return 1.55 + 0.35 * y / EDGE

    _ribbon(kit, mats, root, "track_apron", 0.15, EDGE + 0.1, apron_half, apron_center, lambda x, y: 0.0)
    _abutment(kit, mats, rng, root)

    # the bridge
    _deck(kit, mats, rng, root, EDGE, y_end)
    ys = [EDGE + 2.2 + BENT_GAP * k for k in range(8) if EDGE + 2.2 + BENT_GAP * k < y_end - 1.2]
    for y in ys:
        _bent(kit, mats, rng, root, y)
    # end sill: a heavy log across the width on the hill's slope
    zg = _ground_local(0.0, y_end - 0.15)
    kit.cylinder("end_sill", 0.2, 3.4, (0, y_end - 0.15, zg + 0.05), rot_deg=(0, 90, 0), mat=mats["wood_dark"],
                 segments=8, parent=root)
    _braces(kit, mats, root, [EDGE] + ys)
    _railings(kit, mats, rng, root, [EDGE + 0.1] + ys + [y_end - 0.3])
    _deck_mud(kit, mats, rng, root, EDGE, y_end)

    if FOG:
        _fog(kit, root)

    # the track over the hill: wanders a little and follows the ground
    def hill_center(y):
        return 0.5 * math.sin(0.55 * (y - y_end)) * min(1.0, (y - y_end) / 3.0 + 0.2)

    _ribbon(kit, mats, root, "track_hill", y_end - 0.5, y_end + 5.2, lambda y: 1.7 + 0.1 * (y - y_end),
            hill_center, _ground_local, hump=0.03, rut=0.06)
    return root

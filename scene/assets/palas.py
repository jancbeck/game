"""The commander's tower (palas): a residential stone tower on the cliff edge at the south-west corner.

Why here: the castle rock ends in a cliff on the south (scene/terrain.py), so the south needs only a
breast-high parapet and the one comfortable building of the outpost can stand on the edge, where no
attacker can reach its windows. It is a tower, not a house: a Wohnturm with thick rubble walls,
founded on the rock, entered by a timber stair to a raised door, and slightly better built than the
garrison buildings: dressed window cases, a garderobe over the drop, a corbel table under the
battlements. At dusk nobody is in it yet: no window is lit and the hearths are cold.

The masonry is the plan block `sw_tower` (build_scene.build_block): box, battered plinth, arrow
slits and battlements, with the same stone, quoins and weathering as the other towers. This prop
adds what the block does not have: window cases cut into the block, the buttress down the cliff
face, the door, its stair, the garderobe, a corbel table and the stair-head hut. The prop root
stands on the block's center at courtyard level (z = 0).

Where it stands. The tower is outside the curtain, west of the promontory, so that it does not hide
the courtyard from the main camera: the camera looks north from the south, and the tower's screen
footprint falls left of the west curtain. Only its battlements and the hut show in the main frame.
Its top is 10.4 m over the courtyard, like the gatehouse.

Floors, like the other towers (courtyard floor z = 0; the shelf the tower stands on is z = -3.15):

- ground storey, floor -3.0: stores, arrow slits low down;
- first floor, floor 0.0: the entrance, a guard room and stores; the door is 3 m over the shelf and
  reached by a timber stair along the east face;
- second floor, floor 2.9: the commander's office and chamber, single windows;
- third floor, floor 5.8: the commander's quarters, paired windows on three sides and the
  garderobe over the cliff on the south face;
- roof platform, 8.6, with parapet and merlons; a timber hut over the stair head.

Local frame: origin on the tower's center at courtyard level, +X east, +Y north, rot_z 0. The
south face (y = -2.7) is the cliff side, the east face (x = +3.0) has the door.

`DOOR` is the door's threshold center on the east face in the prop frame, for a later portal; the
door leaf is the object `palas_door`.
"""

import math

import bpy
from mathutils import Vector

from . import garderobe as G
from ._ditch_wall import stain_material

LIGHTS = []

HX, HY = 3.0, 2.7             # half footprint of the block sw_tower
SHELF = -3.15                 # the rock shelf the tower stands on
F_STORE, F_ENTRY, F_OFFICE, F_QUARTERS, F_TOP = -3.0, 0.0, 2.9, 5.8, 8.6
DOOR = (HX, 1.4, F_ENTRY)     # threshold center of the door on the east face
DOOR_W, DOOR_H = 1.05, 2.05
STAIR_X = (3.55, 4.55)        # the stair's width, clear of the plinth's flare
STAIR_FOOT_Y = -2.95
STAIR_STEPS = 14
LANDING_Y = (0.45, 2.2)
BLOCK = "block_sw_tower"

FACES = {"-y": ((0, -1), (1, 0), HY), "+y": ((0, 1), (1, 0), HY),
         "+x": ((1, 0), (0, 1), HX), "-x": ((-1, 0), (0, 1), HX)}


def _pos(face, along, d, z):
    """Prop-frame point on a face: `along` its tangent, `d` out of the wall, height z."""
    (nx, ny), (tx, ty), half = FACES[face]
    return (nx * (half + d) + tx * along, ny * (half + d) + ty * along, z)


def _size(face, width, depth, h):
    """Box size (x, y, z) for something `width` along the face and `depth` through it."""
    return (width, depth, h) if face in ("-y", "+y") else (depth, width, h)


class Cutter:
    """Boolean cutters on the tower's block: one modifier per opening."""

    def __init__(self, kit, root):
        self.kit, self.root = kit, root
        self.block = bpy.data.objects.get(BLOCK)

    def box(self, name, face, along, z0, z1, width, depth):
        if self.block is None:
            return
        c = self.kit.box(f"cut_{name}", _size(face, width, depth, z1 - z0),
                         _pos(face, along, -depth / 2 + 0.02, (z0 + z1) / 2), parent=self.root)
        mod = self.block.modifiers.new(name, "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = c
        c.hide_render = True
        c.display_type = "WIRE"


def _opening(kit, mats, dressed, cut, root, name, face, along, z0, z1, lights=1, light_w=0.5, depth=0.55,
             shutters=False, bars=False):
    """A window: cut into the wall, a stone case, the mullion between lights, a dark back and
    optionally iron bars or a shutter leaf. `along` is the center of the whole opening."""
    w = lights * light_w + (lights - 1) * 0.12
    h = z1 - z0
    cut.box(name, face, along, z0, z1, w, depth)
    kit.box(f"{name}_back", _size(face, w, 0.03, h), _pos(face, along, -depth + 0.06, (z0 + z1) / 2),
            mat=mats["wood_dark"], parent=root)
    for side in (-1, 1):
        kit.box(f"{name}_jamb_{side}", _size(face, 0.15, 0.17, h + 0.08),
                _pos(face, along + side * (w / 2 + 0.07), 0.04, (z0 + z1) / 2), mat=dressed, bevel=0.01, parent=root)
    kit.box(f"{name}_head", _size(face, w + 0.46, 0.2, 0.17), _pos(face, along, 0.05, z1 + 0.085), mat=dressed,
            bevel=0.012, parent=root)
    kit.box(f"{name}_sill", _size(face, w + 0.5, 0.28, 0.09), _pos(face, along, 0.1, z0 - 0.045), mat=dressed,
            bevel=0.012, parent=root)
    for k in range(1, lights):
        x = along - w / 2 + k * light_w + (k - 0.5) * 0.12
        kit.box(f"{name}_mullion_{k}", _size(face, 0.12, depth * 0.7, h), _pos(face, x, -depth * 0.35 + 0.05,
                (z0 + z1) / 2), mat=dressed, bevel=0.01, parent=root)
    kit.box(f"{name}_transom", _size(face, w, 0.11, 0.08), _pos(face, along, -0.1, z0 + h * 0.62), mat=dressed,
            bevel=0.006, parent=root)
    if bars:
        for k in range(3):
            x = along - w / 2 + (k + 1) * w / 4
            kit.box(f"{name}_bar_{k}", _size(face, 0.022, 0.022, h + 0.1), _pos(face, x, -0.12, (z0 + z1) / 2),
                    mat=mats["iron"], parent=root)
    if shutters:
        # one leaf swung open against the reveal, on the left of the opening
        (nx, ny), (tx, ty), _ = FACES[face]
        theta = math.radians(72)
        hinge = Vector(_pos(face, along - w / 2 - 0.11, 0.12, 0.0))
        d2 = Vector((tx * math.cos(theta) + nx * math.sin(theta), ty * math.cos(theta) + ny * math.sin(theta), 0))
        leaf_w = w * 0.5 + 0.04
        c = hinge + d2 * (leaf_w / 2)
        rz = math.degrees(math.atan2(d2.y, d2.x))
        kit.box(f"{name}_shutter", (leaf_w, 0.045, h - 0.05), (c.x, c.y, (z0 + z1) / 2), (0, 0, rz),
                mat=mats["wood_old"], bevel=0.004, parent=root)
        for k in range(2):
            kit.box(f"{name}_shutter_strap_{k}", (leaf_w, 0.05, 0.05), (c.x, c.y, z0 + h * (0.22 + 0.55 * k)),
                    (0, 0, rz), mat=mats["iron"], parent=root)


def _openings(kit, mats, dressed, cut, root):
    # second floor: single windows (the first floor and the storey below have the block's arrow slits)
    for face, a in (("-y", -1.55), ("-y", 1.55), ("-x", 0.0), ("+y", 0.0), ("+x", -1.4)):
        _opening(kit, mats, dressed, cut, root, f"win_office_{face}_{a}", face, a, 3.95, 4.85, light_w=0.46,
                 bars=True)
    # third floor: the commander's quarters, paired lights with a shutter leaf
    for face, a in (("-y", -1.7), ("-y", 1.7), ("+x", -1.1), ("-x", 0.4), ("+y", 0.4)):
        _opening(kit, mats, dressed, cut, root, f"win_quarters_{face}_{a}", face, a, 6.85, 7.95, lights=2,
                 light_w=0.4, shutters=True)


def _door(kit, mats, dressed, cut, root):
    """Raised entrance on the east face: a stone case, an oak leaf with iron straps."""
    face, along, z = "+x", DOOR[1], DOOR[2]
    cut.box("door", face, along, z, z + DOOR_H, DOOR_W, 0.6)
    leaf = kit.group("palas_door", _pos(face, along, -0.42, z), parent=root)
    boards = 5
    bw = DOOR_W / boards
    for k in range(boards):
        a = (k - (boards - 1) / 2) * bw
        kit.box(f"leaf_board_{k}", (0.07, bw - 0.01, DOOR_H - 0.04), (0, a, DOOR_H / 2), mat=mats["door_wood"],
                bevel=0.006, parent=leaf)
    for k, zz in enumerate((0.35, DOOR_H - 0.4)):
        kit.box(f"leaf_strap_{k}", (0.03, DOOR_W, 0.09), (0.04, 0, zz), mat=mats["iron"], bevel=0.004, parent=leaf)
    kit.box("leaf_latch", (0.05, 0.16, 0.05), (0.06, DOOR_W / 2 - 0.2, 1.0), mat=mats["iron"], parent=leaf)
    kit.torus("leaf_ring", 0.05, 0.008, (0.07, DOOR_W / 2 - 0.3, 1.05), (0, 90, 0), mat=mats["iron"], parent=leaf)
    for side in (-1, 1):
        kit.box(f"door_jamb_{side}", _size(face, 0.22, 0.22, DOOR_H + 0.1),
                _pos(face, along + side * (DOOR_W / 2 + 0.11), 0.06, z + DOOR_H / 2 + 0.05), mat=dressed,
                bevel=0.012, parent=root)
    kit.box("door_lintel", _size(face, DOOR_W + 0.7, 0.3, 0.3), _pos(face, along, 0.07, z + DOOR_H + 0.15), mat=dressed,
            bevel=0.014, parent=root)
    kit.box("door_threshold", _size(face, DOOR_W + 0.3, 0.5, 0.12), _pos(face, along, 0.2, z - 0.06), mat=dressed,
            bevel=0.012, parent=root)


def _stair(kit, mats, rng, root):
    """Timber stair up the east face to the landing in front of the door: open treads on two
    stringers, posts on stone pads, a rail on the outer side and round the landing."""
    wd, wo, iron, stone = mats["wood_dark"], mats["wood_old"], mats["iron"], mats["stone_wall"]
    x0, x1 = STAIR_X
    xc, wx = (x0 + x1) / 2, x1 - x0
    y0, y1 = STAIR_FOOT_Y, LANDING_Y[0]
    rise = (F_ENTRY - SHELF) / STAIR_STEPS
    run = (y1 - y0) / STAIR_STEPS
    for side, x in (("in", x0 + 0.05), ("out", x1 - 0.05)):
        kit.beam(f"stringer_{side}", (x, y0 - 0.1, SHELF + 0.05), (x, y1 + 0.1, F_ENTRY - 0.2), (0.09, 0.3), wd,
                 bevel=0.008, parent=root)
    for k in range(1, STAIR_STEPS + 1):
        y = y0 + (k - 0.5) * run
        z = SHELF + k * rise
        kit.box(f"tread_{k}", (wx + 0.08, run + 0.05, 0.045), (xc + kit.jitter(rng, 0.01), y, z - 0.022),
                (0, 0, kit.jitter(rng, 0.8)), wo, bevel=0.005, parent=root)
    # posts on stone pads under the outer stringer, and the foot of the inner one
    for n, k in enumerate((0, 4, 8, 12)):
        y = y0 + 0.15 + k * run
        zt = SHELF + k * rise + 0.12
        kit.box(f"pad_{n}", (0.34, 0.34, 0.16), (x1 - 0.05, y, SHELF + 0.03), (0, 0, kit.jitter(rng, 10)), stone,
                bevel=0.03, parent=root)
        if zt - SHELF > 0.2:
            kit.beam(f"post_{n}", (x1 - 0.05, y, SHELF + 0.1), (x1 - 0.05, y, zt), (0.13, 0.13), wd, bevel=0.01,
                     parent=root)
    kit.box("pad_in", (0.34, 0.34, 0.16), (x0 + 0.05, y0, SHELF + 0.03), (0, 0, kit.jitter(rng, 10)), stone, bevel=0.03,
            parent=root)
    # landing: deck boards on two joists braced back to the wall
    ly0, ly1 = LANDING_Y
    lx1 = 4.65
    for k in range(7):
        w = (lx1 - HX) / 7
        kit.box(f"landing_board_{k}", (w - 0.012, ly1 - ly0 + 0.1, 0.05), (HX + (k + 0.5) * w, (ly0 + ly1) / 2,
                F_ENTRY - 0.035), (0, 0, kit.jitter(rng, 0.6)), wo, bevel=0.005, parent=root)
    for n, y in enumerate((ly0 + 0.15, ly1 - 0.15)):
        kit.beam(f"landing_joist_{n}", (HX - 0.1, y, F_ENTRY - 0.17), (lx1 + 0.05, y, F_ENTRY - 0.17), (0.16, 0.12),
                 wd, bevel=0.008, parent=root)
    for n, y in enumerate((ly0 + 0.1, ly1 - 0.1)):
        x = lx1 - 0.05
        kit.beam(f"landing_post_{n}", (x, y, SHELF + 0.1), (x, y, F_ENTRY + 0.95), (0.14, 0.14), wd, bevel=0.01,
                 parent=root)
        kit.beam(f"landing_brace_{n}", (x, y, SHELF + 1.4), (HX + 0.05, y, F_ENTRY - 0.17), (0.09, 0.09), wd,
                 bevel=0.008, parent=root)
    # rails: outer side of the stair, the landing's outer and north sides
    rail_h = 0.9
    kit.beam("rail_stair", (x1 - 0.05, y0, SHELF + rail_h), (x1 - 0.05, y1, F_ENTRY + rail_h), (0.07, 0.09), wo,
             bevel=0.006, parent=root)
    for k in range(0, STAIR_STEPS + 1, 2):
        y = y0 + k * run
        z = SHELF + k * rise
        kit.beam(f"baluster_{k}", (x1 - 0.05, y, z), (x1 - 0.05, y, z + rail_h), (0.045, 0.045), wd, bevel=0.004,
                 parent=root)
    kit.beam("rail_landing_out", (lx1 - 0.05, ly0 + 0.1, F_ENTRY + rail_h), (lx1 - 0.05, ly1 - 0.1, F_ENTRY + rail_h),
             (0.07, 0.09), wo, bevel=0.006, parent=root)
    kit.beam("rail_landing_north", (lx1 - 0.05, ly1 - 0.1, F_ENTRY + rail_h), (HX + 0.1, ly1 - 0.1, F_ENTRY + rail_h),
             (0.07, 0.09), wo, bevel=0.006, parent=root)
    kit.beam("rail_landing_north_low", (lx1 - 0.05, ly1 - 0.1, F_ENTRY + 0.45), (HX + 0.1, ly1 - 0.1, F_ENTRY + 0.45),
             (0.05, 0.07), wo, bevel=0.005, parent=root)
    # an iron ring in the wall: the stair's top flight can be hauled up
    kit.box("stair_ring", (0.05, 0.05, 0.05), (HX + 0.05, 0.2, F_ENTRY + 1.0), mat=iron, parent=root)


def _garderobe(kit, mats, rng, root):
    """The latrine over the drop, on the south face at the floor of the quarters, with its stain
    running down the wall toward the foot of the cliff."""
    g = kit.group("garderobe_room", (0.0, -HY, F_QUARTERS), parent=root)
    G._corbels(kit, mats, rng, g)
    G._room(kit, mats, rng, g)
    top = -G.SLAB_T - 0.05
    bottom = -(F_QUARTERS - SHELF + 0.5)
    strips = [(0.0, 0.22, 0.6, top, bottom), (0.08, 0.12, 0.34, top - 0.3, top - 7.0),
              (-0.12, 0.08, 0.24, top - 0.8, top - 5.0)]
    G._ribbon(kit, g, "garderobe_stain", strips, stain_material())


def _cliff_foot(kit, mats, root):
    """A battered buttress of masonry from the plinth down the cliff face, so that the south wall
    does not hang over the drop. Profile (y, z) extruded along x."""
    prof = [(-HY + 0.7, -3.0), (-HY - 0.35, -3.0), (-HY - 3.6, -12.6), (-HY + 0.7, -12.6)]
    x0, x1 = -HX - 0.4, HX + 0.4
    verts = [(x0, y, z) for y, z in prof] + [(x1, y, z) for y, z in prof]
    n = len(prof)
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    kit.mesh("cliff_foot", verts, faces, mat=mats["stone_wall"], bevel=0.04, parent=root)


def _corbel_table(kit, dressed, root):
    """A cornice and a row of corbels under the parapet on all four faces, and a string course
    under the quarters' windows."""
    for face in ("-y", "+y", "+x", "-x"):
        half_len = HX if face in ("-y", "+y") else HY
        kit.box(f"cornice_{face}", _size(face, half_len * 2 + 0.3, 0.3, 0.12), _pos(face, 0.0, 0.12, F_TOP - 0.5),
                mat=dressed, bevel=0.012, parent=root)
        n = int(half_len * 2 / 0.5)
        for k in range(n):
            a = -half_len + (k + 0.5) * half_len * 2 / n
            kit.box(f"corbel_{face}_{k}", _size(face, 0.2, 0.22, 0.34), _pos(face, a, 0.08, F_TOP - 0.36), mat=dressed,
                    bevel=0.01, parent=root)
        kit.box(f"band_{face}", _size(face, half_len * 2 + 0.1, 0.1, 0.1), _pos(face, 0.0, 0.05, F_QUARTERS - 0.3),
                mat=dressed, bevel=0.008, parent=root)


def _hut(kit, mats, rng, root):
    """Stair-head hut on the roof platform in the north-west corner: boarded timber on three sides,
    a gabled plank roof, open toward the platform."""
    wo, wd = mats["wood_old"], mats["wood_dark"]
    x0, x1, y0, y1 = -2.3, -0.4, 0.55, 2.0
    eave, ridge = 2.1, 2.75
    z0 = F_TOP
    for sx, x in ((0, x0), (1, x1)):
        for sy, y in ((0, y0), (1, y1)):
            kit.beam(f"hut_post_{sx}{sy}", (x, y, z0), (x, y, z0 + eave), (0.13, 0.13), wd, bevel=0.01, parent=root)
    for name, (ax, ay, bx, by) in (("n", (x0, y1, x1, y1)), ("w", (x0, y0, x0, y1)), ("e", (x1, y0, x1, y1))):
        length = math.hypot(bx - ax, by - ay)
        k, a = 0, 0.0
        while a < length - 0.05:
            w = min(rng.uniform(0.17, 0.24), length - a)
            t = (a + w / 2) / length
            px, py = ax + (bx - ax) * t, ay + (by - ay) * t
            size = (w - 0.012, 0.03, eave - 0.25) if name == "n" else (0.03, w - 0.012, eave - 0.25)
            kit.box(f"hut_board_{name}_{k}", size, (px, py, z0 + 0.15 + (eave - 0.25) / 2),
                    (0, 0, kit.jitter(rng, 0.5)), wo, bevel=0.004, parent=root)
            a += w
            k += 1
    pitch = math.atan2(ridge - eave, (y1 - y0) / 2 + 0.2)
    rl = ((y1 - y0) / 2 + 0.25) / math.cos(pitch)
    for s in (-1, 1):
        k, x = 0, x0 - 0.25
        while x < x1 + 0.25:
            w = rng.uniform(0.18, 0.26)
            kit.box(f"hut_roof_{s}_{k}", (w - 0.012, rl, 0.035),
                    (x + w / 2, (y0 + y1) / 2 + s * rl / 2 * math.cos(pitch),
                     z0 + eave + 0.1 + rl / 2 * math.sin(pitch)), (-s * math.degrees(pitch), 0, kit.jitter(rng, 0.5)),
                    wo, bevel=0.004, parent=root)
            x += w
            k += 1
    kit.box("hut_ridge", (x1 - x0 + 0.5, 0.14, 0.1), ((x0 + x1) / 2, (y0 + y1) / 2, z0 + ridge + 0.05), mat=wd,
            bevel=0.008, parent=root)


def build(kit, mats, rng):
    root = kit.group("palas")
    from assets.gate_door import _dressed
    dressed = _dressed(mats["stone_wall"])
    cut = Cutter(kit, root)
    _openings(kit, mats, dressed, cut, root)
    _door(kit, mats, dressed, cut, root)
    _stair(kit, mats, rng, root)
    _garderobe(kit, mats, rng, root)
    _cliff_foot(kit, mats, root)
    _corbel_table(kit, dressed, root)
    _hut(kit, mats, rng, root)
    return root

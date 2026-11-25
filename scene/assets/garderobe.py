"""Latrine (garderobe) corbelled out from a tower's outer face at first-floor level, with its stain and nettles.

Mounted asset. Origin: on the wall face at the level of the floor it is entered from. The wall face
is the XZ plane at y = 0 and is not part of this prop; the room projects toward -Y. Place it with
rot_z so +Y points into the wall. It is entered from inside the tower through the wall, so there is
no door on the outside.

- Two stacks of three corbels, each course stepping further out, carry a stone floor slab 1.1 m
  wide that projects 0.95 m. A 0.4 x 0.35 m hole in the slab between the corbels is the seat's
  drop; from below it is a black opening.
- Rubble walls 0.15 m thick close the front and sides to 2.0 m; a lean-to roof of stone slabs
  slopes down toward the front. One narrow light slit sits in the front wall 1.1 m above the floor.
- The drop falls free to the ground FOOT_Z below. A long dark stain runs down the wall from the
  corbels to the foot, wider toward the bottom; a broader, older stain spreads at the foot, where a
  dark, wet heap of muck lies, ringed by nettles that grow on the rich ground.
"""

import math

from . import _tube
from ._ditch_wall import stain_material, void_material

FOOT_Z = -6.0            # the ground below, relative to the floor: tower first floor 3 m over the lower ward at -3 m
W, D = 1.1, 0.95         # outer width and projection of the room
WALL_T = 0.15
ROOM_H = 2.0
HOLE_X, HOLE_Y = (-0.2, 0.2), (-0.62, -0.27)
SLAB_T = 0.14
CORBEL_X = 0.38
COURSE_H = 0.22


def _corbels(kit, mats, rng, root):
    st = mats["stone_wall"]
    for sx in (-1, 1):
        for i in range(3):
            d = D * (1.0 - 0.3 * i) + 0.05
            w = 0.26 - 0.02 * i
            z = -SLAB_T - COURSE_H * (i + 0.5)
            kit.box(f"corbel_{sx}_{i}", (w, d, COURSE_H - 0.01), (sx * CORBEL_X + kit.jitter(rng, 0.01), -d / 2 + 0.05, z),
                    (0, 0, kit.jitter(rng, 1.5)), st, bevel=0.025, parent=root)


def _room(kit, mats, rng, root):
    st = mats["stone_wall"]
    z = -SLAB_T / 2
    # floor slab in four pieces round the drop
    (hx0, hx1), (hy0, hy1) = HOLE_X, HOLE_Y
    kit.box("slab_back", (W, -hy1 + 0.05, SLAB_T), (0, (hy1 + 0.05) / 2, z), mat=st, bevel=0.015, parent=root)
    kit.box("slab_front", (W, hy0 + D, SLAB_T), (0, (hy0 - D) / 2, z), mat=st, bevel=0.015, parent=root)
    for n, (x0, x1) in enumerate(((-W / 2, hx0), (hx1, W / 2))):
        kit.box(f"slab_side_{n}", (x1 - x0, hy1 - hy0, SLAB_T), ((x0 + x1) / 2, (hy0 + hy1) / 2, z), mat=st,
                parent=root)
    # the drop: black from below, the hole's sides sooty
    kit.box("drop_void", (hx1 - hx0, hy1 - hy0, 0.01), ((hx0 + hx1) / 2, (hy0 + hy1) / 2, -0.02),
            mat=void_material(), parent=root)
    # walls
    kit.box("wall_front", (W, WALL_T, ROOM_H), (0, -D + WALL_T / 2, ROOM_H / 2), mat=st, bevel=0.02, parent=root)
    for sx in (-1, 1):
        kit.box(f"wall_side_{sx}", (WALL_T, D - WALL_T + 0.05, ROOM_H + 0.18),
                (sx * (W - WALL_T) / 2, -(D - WALL_T) / 2 + 0.025, (ROOM_H + 0.18) / 2), mat=st, bevel=0.02,
                parent=root)
    kit.box("slit", (0.08, 0.03, 0.42), (0.0, -D - 0.002, 1.1), mat=void_material(), parent=root)
    kit.box("slit_lintel", (0.34, 0.06, 0.1), (0.0, -D - 0.005, 1.37), mat=st, bevel=0.01, parent=root)
    # lean-to roof of two stone slabs, front low
    rise = 0.3
    ang = math.degrees(math.atan2(rise, D))
    for n, (x0, x1) in enumerate(((-W / 2 - 0.1, 0.02), (-0.02, W / 2 + 0.1))):
        kit.box(f"roof_slab_{n}", (x1 - x0, D + 0.25, 0.11),
                ((x0 + x1) / 2, -D / 2 - 0.1, ROOM_H + rise / 2 + 0.06 + kit.jitter(rng, 0.01)),
                (ang + kit.jitter(rng, 1.0), kit.jitter(rng, 1.0), 0), st, bevel=0.015, parent=root)
    # a weed tuft in the roof's joint with the wall
    kit.sphere("roof_moss", 0.12, (0.25, -0.12, ROOM_H + 0.36), scale=(1.4, 0.6, 0.4), mat=mats["moss"],
               segments=8, parent=root)


def _ribbon(kit, root, name, strips, mat, y=-0.006):
    """Stain film on the wall face. strips: (x_center, half_width_top, half_width_bottom, z_top, z_bottom).

    The object is turned 90 degrees about Z so that its own Y axis runs across the face: the stain
    material streaks along object Y and Z, as on the west wall."""
    verts, faces, uv = [], [], []
    for (xc, wt, wb, zt, zb) in strips:
        rows = max(2, int(abs(zt - zb) / 0.12))
        cols = 6
        base = len(verts)
        for r in range(rows + 1):
            t = r / rows
            hw = wt + (wb - wt) * t
            zz = zt + (zb - zt) * t
            for c in range(cols + 1):
                s = -1.0 + 2.0 * c / cols
                xa = xc + s * hw
                verts.append((y, -xa, zz))
                uv.append((s, t))
        for r in range(rows):
            for c in range(cols):
                a = base + r * (cols + 1) + c
                faces.append((a, a + 1, a + cols + 2, a + cols + 1))
    ob = kit.mesh(name, verts, faces, rot_deg=(0, 0, 90), mat=mat, parent=root)
    layer = ob.data.uv_layers.new(name="UVMap")
    for loop in ob.data.loops:
        layer.data[loop.index].uv = uv[loop.vertex_index]
    return ob


def _stain(kit, mats, rng, root):
    top = -SLAB_T - 0.05
    strips = [(0.0, 0.22, 0.55, top, FOOT_Z - 0.05),
              (0.08, 0.12, 0.3, top - 0.3, FOOT_Z - 0.05),
              (-0.12, 0.08, 0.2, top - 0.8, top - 3.2)]
    _ribbon(kit, root, "garderobe_stain", strips, stain_material())
    _ribbon(kit, root, "garderobe_stain_foot", [(0.0, 0.6, 0.95, FOOT_Z + 1.6, FOOT_Z - 0.05)],
            stain_material(damp=True), y=-0.008)
    # muck heap where the drop lands, a little out from the wall
    kit.sphere("muck", 0.55, (0.0, -0.45, FOOT_Z - 0.06), scale=(1.15, 0.85, 0.22), mat=mats["mud"], segments=14,
               parent=root)
    kit.sphere("muck_wet", 0.3, (0.05, -0.42, FOOT_Z + 0.0), scale=(1.0, 0.8, 0.2), mat=mats["wood_dark"],
               segments=12, parent=root)


def _nettles(kit, mats, rng, root):
    """Nettle stands round the muck heap: green near the foot, some stalks gone brown."""
    stalks, green, brown = _tube.Mesh(), _tube.Mesh(), _tube.Mesh()
    from mathutils import Vector
    for cx, cy in ((-0.85, -0.35), (0.8, -0.5), (-0.35, -1.0), (0.45, -1.05), (0.0, -1.35), (1.05, -0.95),
                   (-1.0, -0.85)):
        c = Vector((cx, cy, FOOT_Z))
        for _ in range(rng.randint(10, 20)):
            a = rng.uniform(0, 6.28)
            r = abs(rng.gauss(0, 0.17))
            base = c + Vector((math.cos(a) * r, math.sin(a) * r, -0.02))
            height = rng.uniform(0.45, 1.1)
            tilt = Vector((rng.gauss(0, 0.1), rng.gauss(0, 0.1) - 0.05, 1.0)).normalized()
            n = 6
            pts = [base + tilt * (height * k / n) for k in range(n + 1)]
            stalks.tube(pts, [0.004 * (1 - 0.6 * k / n) for k in range(n + 1)], 3)
            ang = rng.uniform(0, 6.28)
            for k in range(2, n + 1):
                for s in (0, 1):
                    ang = ang + math.pi if s else rng.uniform(0, 6.28)
                    size = 0.085 * (1.0 - 0.45 * k / n) * rng.uniform(0.7, 1.2)
                    out = Vector((math.cos(ang), math.sin(ang), -0.35)) * size
                    cross = Vector((-math.sin(ang), math.cos(ang), 0.0)) * size * 0.45
                    q = pts[k]
                    tgt = green if rng.random() < 0.75 else brown
                    b = len(tgt.verts)
                    tgt.verts += [tuple(q), tuple(q + out * 0.6 + cross), tuple(q + out * 1.15),
                                  tuple(q + out * 0.6 - cross)]
                    tgt.faces.append((b, b + 1, b + 2, b + 3))
    stalks.to_object("nettle_stalks", mats["wood_dark"], root)
    green.to_object("nettle_leaves", mats["moss"], root)
    brown.to_object("nettle_leaves_dead", mats["burlap"], root)


def build(kit, mats, rng):
    root = kit.group("garderobe")
    _corbels(kit, mats, rng, root)
    _room(kit, mats, rng, root)
    _stain(kit, mats, rng, root)
    _nettles(kit, mats, rng, root)
    return root

"""Wooden ladder, 3.5 m long, leaning on a wall with one rung missing.

Two tapering rails (0.50 m apart at the foot, 0.36 m at the top, 75 x 40 mm) carry 11
round rungs 0.28 m apart; the rung at 1.98 m is gone and only a splintered stub is left in
the left rail. One rung is a newer, paler replacement and one sits crooked. An iron strap
mends a split in the right rail.

The ladder leans 14 degrees from vertical. The wall plane is at local y = +0.44: the back
corners of the rail tops touch it, and the feet stand about 0.85 m out from it, centered
on x = 0. The foot ends are cut level, so they rest flat on Z = 0. Top at z = 3.4 m.
Place it with its +Y side to the wall, like the mounted props: rot_z 0 for a wall that faces
-Y, and pos 0.44 m out from the wall face.
"""

import math

from mathutils import Vector

LEAN = math.radians(14)
LENGTH = 3.5
FOOT_X, TOP_X = 0.25, 0.18
RAIL_W, RAIL_T = 0.075, 0.04
RUNGS = 12
RUNG_Z0, RUNG_DZ = 0.30, 0.28
MISSING = 6
WALL_Y = 0.44


def _rail(kit, mats, rng, side, parent):
    xf = side * (FOOT_X + kit.jitter(rng, 0.006))
    xt = side * (TOP_X + kit.jitter(rng, 0.008))
    d = Vector((xt - xf, 0, LENGTH)).normalized()
    w = Vector((0, 1, 0)).cross(d) * (RAIL_W / 2)
    n = Vector((0, RAIL_T / 2, 0))
    verts = []
    for p in (Vector((xf, 0, 0)), Vector((xt, 0, LENGTH))):
        for sw, sn in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            verts.append(tuple(p + w * sw + n * sn))
    # foot cut level with the ground once the ladder is tilted: z = y * tan(lean)
    for i in range(4):
        x, y, _ = verts[i]
        verts[i] = (x, y, y * math.tan(LEAN))
    faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = kit.mesh(f"rail_{side}", verts, faces, mat=mats["wood_old"], parent=parent, bevel=0.004)
    return ob, xf, xt


def build(kit, mats, rng):
    j = lambda a: kit.jitter(rng, a)  # noqa: E731
    root = kit.group("ladder")
    top_back = (RAIL_T / 2) * math.cos(LEAN) + LENGTH * math.sin(LEAN)
    g = kit.group("ladder_lean", (0, WALL_Y - top_back, 0), parent=root)
    g.rotation_euler = (-LEAN, 0, 0)

    rails = {}
    for side in (-1, 1):
        _, xf, xt = _rail(kit, mats, rng, side, g)
        rails[side] = (xf, xt)

    def rail_x(side, z):
        xf, xt = rails[side]
        return xf + (xt - xf) * z / LENGTH

    fresh = rng.randrange(RUNGS)
    while fresh == MISSING:
        fresh = rng.randrange(RUNGS)
    crooked = (fresh + 4) % RUNGS
    for k in range(RUNGS):
        z = RUNG_Z0 + RUNG_DZ * k
        xl, xr = rail_x(-1, z), rail_x(1, z)
        if k == MISSING:
            # splintered stub in the left rail
            kit.cylinder("rung_stub", 0.017, 0.075, (xl + RAIL_W / 2 + 0.03, 0, z), (0, 90, j(5)),
                         mats["wood_old"], segments=7, bevel=0.0, parent=g)
            continue
        length = xr - xl + RAIL_W + 0.012
        tilt = 4.0 if k == crooked else j(0.4)
        mat = mats["wood_old"] if k == fresh else mats["wood_dark"]
        kit.cylinder(f"rung_{k}", 0.0175 if k != fresh else 0.02, length,
                     ((xl + xr) / 2 + j(0.003), j(0.002), z + (0.012 if k == crooked else j(0.003))),
                     (0, 90 + tilt, 0), mat, segments=8, parent=g)

    # iron strap round a split in the right rail, two nails showing
    z = 2.45
    xr = rail_x(1, z)
    kit.box("strap", (RAIL_W + 0.014, RAIL_T + 0.014, 0.075), (xr, 0, z),
            (0, math.degrees(math.atan2(rails[1][1] - rails[1][0], LENGTH)), 0), mats["iron"], bevel=0.003, parent=g)
    for dx in (-0.02, 0.02):
        kit.cylinder("strap_nail", 0.008, 0.006, (xr + dx, -RAIL_T / 2 - 0.009, z), (90, 0, 0), mats["iron"],
                     segments=6, parent=g)
    return root

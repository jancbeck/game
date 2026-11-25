"""Stone stair along the inner face of a curtain wall, up to the wall-walk.

The wall face is the plane y = +0.6; the stair fills y = -0.6..+0.6 and x = -3.6..+3.6
from Z = 0. The flight climbs along +X in 24 risers of 0.25 m (6.0 m in total) over
23 treads of 0.28 m, then a 0.73 m landing at z = 6.0 meets the wall-walk. The open
side (-Y) has no railing.

Two parts: a solid masonry core with a stepped top, and one merged mesh of
tread slabs that overhang the core slightly at the front and on the open side.
"""

import math

X0, X1 = -3.6, 3.6
Y_OPEN, Y_WALL = -0.6, 0.6
RISERS = 24
RISE = 0.25
RUN = 0.28
SLAB_T = 0.06            # tread slab thickness
NOSE = 0.03              # slab overhang beyond the riser, and beyond the core on the open side
SINK = 0.04              # core top lies this far below the slab top

CUBE_VERTS = [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, -.5), (-.5, .5, -.5),
              (-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)]
CUBE_FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]

# x of the foot of riser k (k = 1..24); the 24th is the start of the landing
RISER_X = [X0 + NOSE + RUN * (k - 1) for k in range(1, RISERS + 1)]


def _core(kit, mat, parent):
    """Solid prism: stepped profile in XZ, extruded from the open side to the wall."""
    prof = [(RISER_X[0], 0.0), (X1, 0.0), (X1, RISE * RISERS - SINK)]
    for k in range(RISERS, 0, -1):
        h = RISE * k - SINK
        prof.append((RISER_X[k - 1], h))
        if k > 1:
            prof.append((RISER_X[k - 1], RISE * (k - 1) - SINK))
    y0 = Y_OPEN + NOSE
    n = len(prof)
    verts = [(x, y0, z) for x, z in prof] + [(x, Y_WALL, z) for x, z in prof]
    faces = [tuple(range(n)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return kit.mesh("core", verts, faces, mat=mat, parent=parent, bevel=0.012)


def _slabs(kit, rng, mat, parent):
    """One merged mesh: a slab per tread plus the landing slab."""
    J = lambda a: kit.jitter(rng, a)
    verts, faces = [], []
    for k in range(1, RISERS + 1):
        x_a = RISER_X[k - 1] - NOSE
        x_b = RISER_X[k] if k < RISERS else X1
        top = RISE * k
        sx, sy = x_b - x_a, Y_WALL - Y_OPEN - 0.012   # inset so jitter stays inside the footprint
        cx, cy, cz = (x_a + x_b) / 2, (Y_OPEN + Y_WALL) / 2 + J(0.004), top - SLAB_T / 2 + J(0.003)
        yaw = math.radians(J(0.4))
        c, s = math.cos(yaw), math.sin(yaw)
        base = len(verts)
        for vx, vy, vz in CUBE_VERTS:
            px, py = vx * sx, vy * sy
            verts.append((cx + px * c - py * s, cy + px * s + py * c, cz + vz * SLAB_T))
        faces += [tuple(base + i for i in f) for f in CUBE_FACES]
    return kit.mesh("treads", verts, faces, mat=mat, parent=parent, bevel=0.01)


def build(kit, mats, rng):
    root = kit.group("wall_stair")
    _core(kit, mats["stone_wall"], root)
    _slabs(kit, rng, mats["stone_wall"], root)
    return root

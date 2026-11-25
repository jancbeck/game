"""Courtyard well: round rubble drum, timber windlass frame, small shingle roof, rope and bucket.

The drum is 1.7 m across at the foot and 0.8 m high, built from four courses of separate
wedge-shaped rubble stones (a wide plinth course, two plain courses, a flat capstone ring)
around a dark shaft with rainwater standing 0.5 m below the rim. Two posts stand on the
capstones at x = +-0.70 and carry a windlass at z = 1.62 with rope turns, an iron-strapped
barrel and a crank on the +X end. A gable roof of staggered shingles (ridge along X, 2.2 m long,
eaves at z = 2.1) sits on rafters; some shingles are lost and show the dark deck. A bucket
hangs on the rope over the open shaft, a hand above the rim.

Footprint 2.2 m (X, roof and crank) by 1.7 m (Y), 2.7 m high, centered on the origin. The
open side for drawing water is -Y; place it with rot_z 0 so the roof slope faces the camera.
"""

import math

import bpy
from mathutils import Euler, Vector

from . import _sweep
from . import bucket as bucket_mod

HEIGHT = 0.80
R_IN = 0.50
POST_X = 0.70
WIND_Z = 1.62
ZR = 2.62            # roof ridge height
PITCH = math.radians(33)
SLOPE = 0.95         # eave distance from the ridge, along the slope
# (z0, height, outer radius, inner radius, mean stone length) of each course
COURSES = ((0.00, 0.14, 0.88, 0.50, 0.36),
           (0.14, 0.22, 0.81, 0.50, 0.30),
           (0.36, 0.22, 0.80, 0.50, 0.32),
           (0.58, 0.22, 0.85, 0.46, 0.38))


class _Solid:
    """Many small solids merged into one mesh."""

    def __init__(self):
        self.verts, self.faces = [], []

    def hexa(self, c):
        """Hexahedron from 4 bottom corners and the 4 corners above them."""
        b = len(self.verts)
        self.verts += [tuple(p) for p in c]
        self.faces += [(b, b + 1, b + 2, b + 3), (b + 4, b + 5, b + 6, b + 7),
                       (b, b + 1, b + 5, b + 4), (b + 1, b + 2, b + 6, b + 5),
                       (b + 2, b + 3, b + 7, b + 6), (b + 3, b, b + 4, b + 7)]

    def box(self, center, size, euler=(0, 0, 0)):
        hx, hy, hz = (s / 2 for s in size)
        m = Euler(euler).to_matrix()
        c = Vector(center)
        pts = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
               (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
        self.hexa([c + m @ Vector(p) for p in pts])

    def to_object(self, kit, name, mat, parent, bevel=0.0):
        return kit.mesh(name, self.verts, self.faces, mat=mat, parent=parent, bevel=bevel)


def _drum(kit, mats, rng, root):
    j = lambda a: kit.jitter(rng, a)  # noqa: E731
    stones = _Solid()
    for ci, (z0, h, ro, ri, mean_len) in enumerate(COURSES):
        rm = (ro + ri) / 2
        n = max(8, round(2 * math.pi * rm / mean_len))
        w = [rng.uniform(0.7, 1.4) for _ in range(n)]
        a = rng.uniform(0, 2 * math.pi)
        for k in range(n):
            da = 2 * math.pi * w[k] / sum(w)
            a0, a1 = a + 0.006, a + da - 0.006
            a += da
            hh = h + (j(0.01) if ci < 3 else j(0.006))

            def ring(z, jr):
                return [(math.cos(aa) * rr, math.sin(aa) * rr, z + j(jr[2]))
                        for aa, rr in ((a0 + j(0.02), ri + j(jr[0])), (a1 + j(0.02), ri + j(jr[0])),
                                       (a1 + j(0.02), ro + j(jr[1])), (a0 + j(0.02), ro + j(jr[1])))]

            stones.hexa(ring(z0, (0.015, 0.02, 0.004)) + ring(z0 + hh, (0.02, 0.03, 0.012)))
    stones.to_object(kit, "drum_stones", mats["stone_wall"], root, bevel=0.018)

    # core that fills the joints between the stones: an annulus a little inside them
    n = 36
    r_a, r_b, zt = 0.53, 0.76, HEIGHT - 0.02
    verts = []
    for z in (0.0, zt):
        verts += [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n), z)
                  for r in (r_a, r_b) for i in range(n)]
    faces = []
    for i in range(n):
        k = (i + 1) % n
        # layout: [bottom inner][bottom outer][top inner][top outer]
        faces += [(i, k, n + k, n + i), (2 * n + i, 3 * n + i, 3 * n + k, 2 * n + k),
                  (n + i, n + k, 3 * n + k, 3 * n + i), (i, 2 * n + i, 2 * n + k, k)]
    kit.mesh("drum_core", verts, faces, mat=mats["stone_wall"], parent=root)


def _water(kit, parent):
    mat = bpy.data.materials.get("rainwater")
    if mat is None:
        mat = bpy.data.materials.new("rainwater")
        mat.use_nodes = True
        b = mat.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.03, 0.04, 0.05, 1.0)
        b.inputs["Roughness"].default_value = 0.02
        b.inputs["Specular IOR Level"].default_value = 1.0
        b.inputs["Metallic"].default_value = 0.0
    n, z, r = 32, 0.30, 0.53
    verts = [(0, 0, z)] + [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n), z)
                           for i in range(n)]
    faces = [(0, 1 + (i + 1) % n, 1 + i) for i in range(n)]
    return kit.mesh("well_water", verts, faces, mat=mat, parent=parent)


def _moss(kit, mats, rng, root):
    for i in range(5):
        a = rng.uniform(0, 2 * math.pi)
        if i < 3:   # on the capstones
            r, z = rng.uniform(0.55, 0.78), HEIGHT + 0.004
        else:       # at the foot
            r, z = rng.uniform(0.84, 0.92), 0.01
        s = rng.uniform(0.05, 0.11)
        kit.sphere(f"moss_{i}", 1.0, (r * math.cos(a), r * math.sin(a), z),
                   scale=(s, s * rng.uniform(0.5, 0.9), 0.012), rot_deg=(0, 0, math.degrees(a)),
                   mat=mats["moss"], segments=8, parent=root)


def _frame(kit, mats, rng, root):
    wd, wo, iron = mats["wood_dark"], mats["wood_old"], mats["iron"]
    j = lambda a: kit.jitter(rng, a)  # noqa: E731
    post_top = 2.20
    for sx in (-1, 1):
        x = sx * POST_X
        kit.beam(f"post_{sx}", (x, 0, 0.72), (x + j(0.008), j(0.008), post_top), (0.14, 0.14), wd,
                 bevel=0.012, parent=root)
        # iron bearing plate on the inside face
        kit.box(f"bearing_{sx}", (0.02, 0.15, 0.15), (x - sx * 0.08, 0, WIND_Z), mat=iron, bevel=0.004,
                parent=root)
        # tie beam across the post top, along Y, with knee braces down to the post
        kit.box(f"tie_{sx}", (0.12, 1.10, 0.10), (x, 0, post_top + 0.05), mat=wd, bevel=0.01, parent=root)
        for sy in (-1, 1):
            kit.beam(f"knee_{sx}_{sy}", (x, sy * 0.07, 1.86), (x, sy * 0.46, post_top + 0.02), (0.07, 0.07), wo,
                     bevel=0.008, parent=root)
        kit.beam(f"king_{sx}", (x, 0, post_top + 0.08), (x, 0, ZR - 0.07), (0.09, 0.09), wd, bevel=0.008,
                 parent=root)
    # ridge pole
    kit.box("ridge_pole", (2.2, 0.10, 0.10), (0, 0, ZR - 0.095), mat=wd, bevel=0.01, parent=root)

    # windlass: barrel between the posts, axle through the bearings, iron bands, crank
    kit.cylinder("barrel", 0.085, 1.26, (0, 0, WIND_Z), (0, 90, 0), wo, segments=14, parent=root)
    kit.cylinder("axle", 0.032, 1.80, (0.0, 0, WIND_Z), (0, 90, 0), wd, segments=10, parent=root)
    for x in (-0.52, 0.52):
        kit.torus(f"band_{x}", 0.088, 0.008, (x, 0, WIND_Z), (0, 90, 0), iron, major_segments=20,
                  minor_segments=5, parent=root)
    cx = POST_X + 0.12
    kit.beam("crank_arm", (cx, 0, WIND_Z + 0.02), (cx, -0.05, WIND_Z - 0.30), (0.03, 0.05), iron, bevel=0.004,
             parent=root)
    kit.cylinder("crank_handle", 0.022, 0.20, (cx + 0.09, -0.05, WIND_Z - 0.30), (0, 90, 0), wd, segments=8,
                 parent=root)

    # rafters and the dark deck under the shingles
    rafter_x = (-1.0, -0.5, 0.0, 0.5, 1.0)
    for s in (-1, 1):
        n = Vector((0, s * math.sin(PITCH), math.cos(PITCH)))
        for x in rafter_x:
            a = Vector((x, 0, ZR)) - n * 0.075
            b = Vector((x, s * SLOPE * math.cos(PITCH), ZR - SLOPE * math.sin(PITCH))) - n * 0.075
            kit.beam(f"rafter_{s}_{x}", a, b, (0.06, 0.06), wo, bevel=0.006, parent=root)
        mid = Vector((0, s * SLOPE * 0.5 * math.cos(PITCH), ZR - SLOPE * 0.5 * math.sin(PITCH))) - n * 0.04
        deck = kit.box(f"deck_{s}", (2.2, SLOPE, 0.02), tuple(mid), mat=wd, parent=root)
        deck.rotation_euler = Euler((-s * PITCH, 0, 0))


def _shingles(kit, mats, rng, root):
    """Staggered shingle courses on both slopes; some lost, some slipped, all a little crooked."""
    light, dark = _Solid(), _Solid()
    for s in (-1, 1):
        n = Vector((0, s * math.sin(PITCH), math.cos(PITCH)))
        for row in range(9):
            v_low = SLOPE + 0.04 - row * 0.105          # lower edge, measured down from the ridge
            length = rng.uniform(0.19, 0.22)
            x = -1.12 - rng.uniform(0, 0.12)
            while x < 1.1:
                w = rng.uniform(0.10, 0.17)
                x0, x = x, x + w
                if rng.random() < 0.035 and 1 <= row <= 7:
                    continue                             # lost shingle
                v = v_low - length / 2 + kit.jitter(rng, 0.012)
                c = Vector((x0 + w / 2, s * v * math.cos(PITCH), ZR - v * math.sin(PITCH))) + n * 0.078
                tilt = math.radians(3.5) + math.radians(kit.jitter(rng, 1.5))
                euler = (-s * (PITCH - tilt), math.radians(kit.jitter(rng, 1.5)), math.radians(kit.jitter(rng, 2.5)))
                (dark if rng.random() < 0.3 else light).box(c, (w - 0.008, length, 0.013), euler)
    # ridge boards, one a little longer than the other
    for s in (-1, 1):
        n = Vector((0, s * math.sin(PITCH), math.cos(PITCH)))
        c = Vector((0, s * 0.055 * math.cos(PITCH), ZR - 0.055 * math.sin(PITCH))) + n * 0.083
        dark.box(c, (2.26 - (0.05 if s > 0 else 0), 0.13, 0.022), (-s * PITCH, 0, 0))
    light.to_object(kit, "shingles_a", mats["wood_old"], root, bevel=0.002)
    dark.to_object(kit, "shingles_b", mats["wood_dark"], root, bevel=0.002)
    # moss along the eave of the camera side
    for i in range(5):
        v = SLOPE * rng.uniform(0.8, 0.98)
        x = rng.uniform(-0.95, 0.95)
        kit.sphere(f"eave_moss_{i}", 1.0, (x, -v * math.cos(PITCH), ZR - v * math.sin(PITCH) + 0.09),
                   scale=(rng.uniform(0.06, 0.12), 0.05, 0.01), rot_deg=(-math.degrees(PITCH), 0, 0),
                   mat=mats["moss"], segments=8, parent=root)


def _rope(kit, mats, rng, root):
    """Rope turns on the windlass and one bucket hanging from the rope over the open shaft."""
    x0 = rng.uniform(-0.25, 0.25)
    for k in range(-3, 4):
        kit.torus(f"turn_{k}", 0.095, 0.0115, (x0 + k * 0.024, 0, WIND_Z), (0, 90, 0), mats["rope"],
                  major_segments=24, minor_segments=5, parent=root)
    # the bucket hangs a hand above the rim, bail up, a little off plumb as it swings
    hang = HEIGHT + 0.12
    sway = (rng.uniform(-5, 5), rng.uniform(-4, 4), rng.uniform(-35, 35))
    b = bucket_mod.build(kit, mats, rng, bail_deg=0)
    b.parent = root
    b.location = (x0, -0.10, hang)
    b.rotation_euler = tuple(math.radians(a) for a in sway)
    # rope: off the front of the barrel, straight down to the top of the bail
    top = (x0 + 0.01, -0.10, hang + bucket_mod.EAR_Z + 0.17 + 0.004)
    ctrl = [(x0, -0.096, WIND_Z + 0.01), (x0, -0.108, WIND_Z - 0.12), (x0 + 0.004, -0.104, (top[2] + WIND_Z) / 2),
            top]
    _sweep.rope(kit, "well_rope", ctrl, 0.0115, mats["rope"], root, lay=0.075, step=0.01, sides=5)


def build(kit, mats, rng):
    root = kit.group("well")
    _drum(kit, mats, rng, root)
    _water(kit, root)
    _moss(kit, mats, rng, root)
    _frame(kit, mats, rng, root)
    _shingles(kit, mats, rng, root)
    _rope(kit, mats, rng, root)
    return root

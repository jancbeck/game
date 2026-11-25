"""Wall-base dressing: a 4 m strip that breaks the straight seam between wall and floor.

A mound of mud drifts against the wall, with a splash stain climbing the stone above it. The
mound has bare stretches and high ones. A thin ribbon of standing water, the wet gutter, runs
along its outer edge in stretches. On and around the mound lie fallen stones, a chunk of loose
mortar with crumbs, weed and dead grass tufts, moss, leaves and a few twigs. Everything is
below 0.3 m, and the mound tapers to nothing at both ends, so strips can be repeated end to
end or overlapped by up to 0.4 m. The mud wears the colors of the courtyard floor (see
`dress` in mats/mud.py).
The seed changes the shape of the mud, the number and place of the stones, and where the
tufts grow, so repeats do not match.

Strip along X from -2 to +2, resting on Z = 0. The wall plane is at local y = +0.5, so the
strip fills y = 0 to 0.5. Place it with its +Y side to the wall, like the mounted props:
pos is the wall point moved 0.5 m out from the wall face, rot_z turns +Y toward the wall.
An X scale below 1 shortens a strip for a short wall.
"""

import math

from mathutils import Vector, noise

from . import _tube
from .grass_tuft import _blades

HALF = 2.0
DEPTH = 0.5
STEP = 0.05
BASE = 0.003            # the mud skin rests this far above the floor, so the two never z-fight


def _smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


class _Field:
    """Mud height above the floor at (x, y) and the splash stain height at x."""

    def __init__(self, rng):
        self.o = Vector((rng.uniform(-200, 200), rng.uniform(-200, 200), rng.uniform(-200, 200)))

    def _n(self, x, y, f, k=0):
        return noise.noise(Vector((x * f, y * f * 1.8, k)) + self.o)

    def end(self, x):
        return _smooth((HALF - abs(x)) / 0.45)

    def cover(self, x):
        """0 on a bare stretch of the wall foot, 1 where silt has piled up."""
        return _smooth((0.5 + 0.5 * self._n(x, 0.0, 0.45, 15) - 0.22) / 0.34)

    def edge(self, x):
        """Where the mound begins, measured from the outer limit of the strip: 0 to 0.3 m, and wider where it is bare."""
        return min(0.30, 0.22 * (1.0 - self.cover(x)) + 0.12 * (0.5 + 0.5 * self._n(x, 0.0, 2.6, 31)))

    def mud(self, x, y):
        e = self.edge(x)
        ramp = _smooth((y - e) / (DEPTH - e)) ** 1.25
        n = 0.65 * self._n(x, y, 1.3) + 0.35 * self._n(x, y, 4.0, 3)
        lump = self._n(x, y, 13.0, 7)
        h = 0.07 + 0.05 * n + 0.012 * lump
        return max(0.0, h) * ramp * self.end(x) * (0.3 + 0.7 * self.cover(x))

    def gutter(self, x):
        """Width of the wet gutter at x: 0 where it is dry."""
        wet = _smooth((0.5 + 0.5 * self._n(x, 0.0, 0.6, 21) - 0.42) / 0.2) * self.end(x)
        return (0.035 + 0.07 * (0.5 + 0.5 * self._n(x, 0.0, 1.7, 23))) * wet

    def splash(self, x):
        n = 0.6 * self._n(x, 0.0, 2.2, 9) + 0.4 * self._n(x, 0.0, 9.0, 11)
        return max(0.0, 0.16 + 0.09 * n) * self.end(x) ** 0.7


def _mud(kit, mats, rng, root, fld):
    """Mud mound plus a ragged splash stain on the wall; one mesh, texture shifted per seed."""
    nx = int(2 * HALF / STEP) + 1
    ny = int(DEPTH / STEP) + 1
    verts, faces = [], []
    for ix in range(nx):
        x = -HALF + ix * STEP
        edge = fld.edge(x)  # the mound starts this far from the wall's outer limit, so its outline is not a straight line
        for iy in range(ny):
            y = edge + (DEPTH - edge) * iy / (ny - 1)
            verts.append((x, y, BASE + fld.mud(x, y) - (0.004 if iy == ny - 1 else 0.0)))
    for ix in range(nx - 1):
        for iy in range(ny - 1):
            a = ix * ny + iy
            faces.append((a, a + ny, a + ny + 1, a + 1))
    # splash stain: a ribbon 6 mm off the wall face with a ragged top edge
    base = len(verts)
    for ix in range(nx):
        x = -HALF + ix * STEP
        verts.append((x, DEPTH - 0.006, BASE + fld.mud(x, DEPTH) * 0.5))
        verts.append((x, DEPTH - 0.006, BASE + fld.mud(x, DEPTH) + fld.splash(x)))
    for ix in range(nx - 1):
        a = base + ix * 2
        faces.append((a, a + 2, a + 3, a + 1))
    off = Vector((rng.uniform(-40, 40), rng.uniform(-40, 40), 0.0))
    verts = [tuple(Vector(v) + off) for v in verts]
    ob = kit.mesh("mud_drift", verts, faces, loc=tuple(-off), mat=mats["mud"], parent=root)
    for p in ob.data.polygons:
        p.use_smooth = True
    ob.data.attributes.new(name="dress", type="FLOAT", domain="POINT").data.foreach_set("value", [1.0] * len(verts))
    return ob


def _gutter(kit, mats, rng, root, fld):
    """The wet gutter: a ribbon of standing water just outside the mound, in stretches."""
    nx = int(2 * HALF / STEP) + 1
    verts, faces, rows = [], [], []
    for ix in range(nx):
        x = -HALF + ix * STEP
        w = fld.gutter(x)
        y0 = -0.03 - 0.03 * fld._n(x, 0.0, 3.0, 27)
        rows.append(w)
        verts += [(x, y0, BASE + 0.0015), (x, y0 - w * 0.5, BASE + 0.0015), (x, y0 - w, BASE + 0.0015)]
    for ix in range(nx - 1):
        if rows[ix] < 0.004 and rows[ix + 1] < 0.004:
            continue
        for j in range(2):
            a = ix * 3 + j
            faces.append((a, a + 1, a + 4, a + 3))
    if not faces:
        return None
    ob = kit.mesh("gutter_water", verts, faces, mat=mats["mud"], parent=root)
    ob.data.attributes.new(name="gutter", type="FLOAT", domain="POINT").data.foreach_set("value", [1.0] * len(verts))
    return ob


def _stone(kit, mats, rng, root, fld, i, x, y, r):
    sz = r * rng.uniform(0.5, 0.75)
    ob = kit.sphere(f"stone_{i}", 1.0, (x, y, 0), scale=(r, r * rng.uniform(0.7, 1.0), sz),
                    rot_deg=(rng.uniform(-8, 8), rng.uniform(-8, 8), rng.uniform(0, 180)),
                    mat=mats["stone_wall"], segments=9, parent=root)
    for v in ob.data.vertices:
        v.co *= rng.uniform(0.85, 1.12)
        v.co.z = max(v.co.z, -0.5 * sz)
    ob.location.z = BASE + fld.mud(x, y) + 0.4 * sz - 0.004
    return ob


def _stones(kit, mats, rng, root, fld):
    for i in range(rng.randint(7, 11)):
        x = rng.uniform(-1.75, 1.75)
        y = DEPTH * (1 - 0.9 * rng.random() ** 1.6)
        r = rng.choice((0.02, 0.028, 0.035, 0.045, 0.06)) * rng.uniform(0.8, 1.2)
        _stone(kit, mats, rng, root, fld, i, x, y, r)
    # one broken-off block corner with a clean fracture, lying against the wall
    x, y = rng.uniform(-1.3, 1.3), rng.uniform(0.25, 0.4)
    kit.box("block_chip", (rng.uniform(0.13, 0.19), rng.uniform(0.09, 0.12), rng.uniform(0.06, 0.09)),
            (x, y, BASE + fld.mud(x, y) + 0.03), (rng.uniform(-12, 12), rng.uniform(-12, 12), rng.uniform(0, 180)),
            mats["stone_wall"], bevel=0.012, parent=root)


def _mortar(kit, mats, rng, root, fld):
    """A chunk of fallen mortar, flat and crumbly, with crumbs scattered below it."""
    cx, cy = rng.uniform(-1.4, 1.4), rng.uniform(0.2, 0.36)
    z = BASE + fld.mud(cx, cy)
    rz = rng.uniform(0, 180)
    kit.box("mortar_chunk", (0.17, 0.10, 0.045), (cx, cy, z + 0.018), (rng.uniform(-6, 6), rng.uniform(-6, 6), rz),
            mats["stone_wall"], bevel=0.014, parent=root)
    kit.box("mortar_chunk_b", (0.09, 0.07, 0.03), (cx + 0.1 * math.cos(math.radians(rz + 90)),
                                                      cy + 0.1 * math.sin(math.radians(rz + 90)), z + 0.012),
            (0, 0, rz + rng.uniform(-40, 40)), mats["stone_wall"], bevel=0.01, parent=root)
    for i in range(rng.randint(8, 14)):
        x = cx + rng.gauss(0, 0.16)
        y = min(max(cy + rng.gauss(-0.05, 0.1), 0.02), DEPTH - 0.04)
        s = rng.uniform(0.008, 0.024)
        kit.box(f"crumb_{i}", (s, s * rng.uniform(0.6, 1.2), s * 0.6),
                (x, y, BASE + fld.mud(x, y) + s * 0.25), (0, 0, rng.uniform(0, 180)),
                mats["stone_wall"], bevel=0.003, parent=root)


def _merge(dst, src, dx, dy, dz):
    base = len(dst.verts)
    dst.verts += [(x + dx, y + dy, z + dz) for x, y, z in src.verts]
    dst.faces += [tuple(i + base for i in f) for f in src.faces]


def _tufts(kit, mats, rng, root, fld):
    green, dry = _tube.Mesh(), _tube.Mesh()
    centers = [rng.uniform(-1.5, 1.5) for _ in range(rng.randint(1, 2))]
    for i in range(rng.randint(5, 8)):
        cx = rng.choice(centers) + rng.gauss(0, 0.35) if rng.random() < 0.7 else rng.uniform(-1.7, 1.7)
        cx = min(max(cx, -1.75), 1.75)
        y = rng.uniform(0.22, 0.43)
        height = rng.uniform(0.09, 0.24)
        tmp = _tube.Mesh()
        _blades(tmp, rng, rng.randint(10, 26), height, rng.uniform(10, 40))
        _merge(green if rng.random() < 0.45 else dry, tmp, cx, y, BASE + fld.mud(cx, y))
    if dry.faces:
        dry.to_object("tufts_dry", mats["straw"], root)
    if green.faces:
        green.to_object("tufts_green", mats["moss"], root)
    # moss on the mud and the stone foot
    for i in range(rng.randint(3, 5)):
        x = rng.uniform(-1.7, 1.7)
        s = rng.uniform(0.06, 0.15)
        y = DEPTH - 0.04 - rng.uniform(0, 0.08)
        kit.sphere(f"moss_{i}", 1.0, (x, y, BASE + fld.mud(x, y) + 0.004), scale=(s, s * 0.45, 0.012),
                   rot_deg=(0, 0, rng.uniform(-8, 8)), mat=mats["moss"], segments=8, parent=root)


def _leaf(rng, cx, cy, z, size):
    a = rng.uniform(0, math.pi)
    ca, sa = math.cos(a), math.sin(a)
    outline = [(1.0, 0.0), (0.55, 0.45), (-0.2, 0.5), (-0.8, 0.2), (-1.0, 0.0), (-0.8, -0.2), (-0.2, -0.5),
               (0.55, -0.45)]
    lift = rng.uniform(0.0, 0.008)
    return [(cx + (px * ca - py * 0.55 * sa) * size, cy + (px * sa + py * 0.55 * ca) * size,
             z + lift * (px + 1) / 2) for px, py in outline]


def _litter(kit, mats, rng, root, fld):
    dry, green = _tube.Mesh(), _tube.Mesh()
    for i in range(rng.randint(9, 15)):
        x = rng.uniform(-1.8, 1.8)
        y = rng.uniform(0.05, 0.46)
        pts = _leaf(rng, x, y, BASE + fld.mud(x, y) + 0.003, rng.uniform(0.022, 0.04))
        m = dry if rng.random() < 0.7 else green
        b = len(m.verts)
        m.verts += pts
        m.faces.append(tuple(range(b, b + len(pts))))
    dry.to_object("leaves_dry", mats["straw"], root)
    if green.faces:
        green.to_object("leaves_dark", mats["moss"], root)
    for i in range(rng.randint(3, 5)):
        x, y = rng.uniform(-1.7, 1.7), rng.uniform(0.1, 0.42)
        a = rng.uniform(0, math.pi)
        ln = rng.uniform(0.12, 0.3)
        z = BASE + fld.mud(x, y) + 0.006
        d = (math.cos(a) * ln / 2, math.sin(a) * ln / 2)
        kit.beam(f"twig_{i}", (x - d[0], y - d[1], z), (x + d[0], y + d[1], z + rng.uniform(0.0, 0.02)),
                 (0.007, 0.007), mats["wood_dark"], parent=root)


def build(kit, mats, rng):
    root = kit.group("base_dressing")
    fld = _Field(rng)
    _mud(kit, mats, rng, root, fld)
    _gutter(kit, mats, rng, root, fld)
    _stones(kit, mats, rng, root, fld)
    _mortar(kit, mats, rng, root, fld)
    _tufts(kit, mats, rng, root, fld)
    _litter(kit, mats, rng, root, fld)
    return root

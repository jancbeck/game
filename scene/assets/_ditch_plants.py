"""Undergrowth for the west ditch: dead bracken, brambles, nettle stalks, grass, rushes and bulrushes.

Helper of west_ditch.py. Each kind is scattered over the zones of `_ditch_field` and merged into one
mesh per material, so the whole thicket costs a handful of objects. Everything is wet, dark and dying:
late autumn, bracken gone rust-brown, bramble canes bare with a few dead leaves, nettles reduced to
stalks.
"""

import math
import random

from mathutils import Vector, noise

from . import _ditch_field as F
from . import _tube
from .grass_tuft import _blades

# how many of each: a clump is a group of plants, a thicket is one bramble bush
BRACKEN_CLUMPS = 130
BRAMBLES = 22
NETTLE_CLUMPS = 50
GRASS_TUFTS = 340
REED_CLUMPS = 40
BULRUSHES = 24


class _Meshes:
    """One `_tube.Mesh` per material key; `finish` turns each into an object under the root."""

    def __init__(self):
        self.by_key = {}

    def __getitem__(self, key):
        if key not in self.by_key:
            self.by_key[key] = _tube.Mesh()
        return self.by_key[key]

    def finish(self, mats, root, prefix):
        for key, mesh in self.by_key.items():
            if mesh.faces:
                mesh.to_object(f"{prefix}_{key}", mats[key], root)


def _local(p):
    return Vector(F.to_local(*p))


def _on_ground(x, y, lift=-0.02):
    return Vector((x, y, F.ground(x, y) + lift))


# ---------------------------------------------------------------- scatter

def _patchiness(x, y):
    """0 to 1 field of clumps and gaps: thicket where it is high, bare earth where it is low."""
    n = noise.noise(Vector((x * 0.42, y * 0.42, 4.0))) + 0.5 * noise.noise(Vector((x * 1.3, y * 1.3, 7.0)))
    return F.smooth(-0.15, 0.55, n)


def _scatter(rng, n, picker, avoid_track=True, max_slope=0.80, patchy=True):
    """n world points (x, y, z) from `picker(rng) -> (x, y)`, skipping the track and steep ground and
    thinning out where `_patchiness` is low."""
    out, tries = [], 0
    while len(out) < n and tries < n * 60:
        tries += 1
        x, y = picker(rng)
        if avoid_track and abs((F.WALL_X - x) - F.track_e(y)) < F.TRACK_HALF + 0.03:
            continue
        if patchy and rng.random() > 0.06 + 0.94 * _patchiness(x, y):
            continue
        if F.surface_normal_z(x, y) < max_slope:
            continue
        out.append(_on_ground(x, y))
    return out


def _foot(rng):
    """The strip against the wall: silt, rubble and the first weeds."""
    return F.WALL_X - rng.uniform(0.04, 0.45), rng.uniform(-13.0, 9.0)


def _inner_bank(rng):
    y = rng.uniform(-14.0, 12.0)
    return F.centre(y) + F.half_width(y) + rng.uniform(0.2, 1.1), y


def _outer_bank(rng):
    y = rng.uniform(-16.0, 14.0)
    return F.centre(y) - F.half_width(y) - rng.uniform(0.3, 4.2), y


def _water_edge(rng):
    y = rng.uniform(-12.5, 10.5)
    side = rng.choice((-1, 1))
    return F.centre(y) + side * (F.half_width(y) + rng.uniform(-0.05, 0.40)), y


def _mixed(rng, weights):
    pickers = (_foot, _inner_bank, _outer_bank)
    return rng.choices(pickers, weights=weights)[0](rng)


# ---------------------------------------------------------------- bracken

def _frond(mesh, rng, base, az, length):
    """One bracken frond: a bare stipe, then a jagged triangular blade that arches over and droops."""
    out = Vector((math.cos(az), math.sin(az), 0.0))
    side = Vector((-out.y, out.x, 0.0))
    n = 15
    t0 = rng.uniform(0.28, 0.42)             # where the blade starts
    wmax = length * rng.uniform(0.17, 0.26)  # half width of the blade at its base
    lean = math.radians(rng.uniform(8, 22))
    bend = math.radians(rng.uniform(70, 125))
    pts, widths, pos = [], [], Vector(base)
    for k in range(n + 1):
        t = k / n
        pts.append(pos.copy())
        a = lean + bend * t ** 1.25
        pos = pos + (out * math.sin(a) + Vector((0, 0, math.cos(a)))) * (length / n)
        if t < t0:
            widths.append(0.012 * (1 - t / t0 * 0.5))
        else:
            u = (t - t0) / (1 - t0)
            w = 2 * wmax * (1 - u ** 0.85) ** 0.9
            widths.append(max(0.012, w * (1.0 if k % 2 else 0.55)))     # alternate: a serrated edge
    mesh.blade(pts, widths, side, fold=0.25, twist=rng.uniform(-0.5, 0.5))


def bracken(rng, meshes, points):
    for p in points:
        fronds = rng.randint(4, 9)
        az = rng.uniform(0, 6.28)
        scale = rng.uniform(0.75, 1.2)
        palette = rng.choice(("straw", "straw", "burlap"))
        for f in range(fronds):
            az += 2.4 + rng.uniform(-0.6, 0.6)
            base = _local(p) + Vector((rng.gauss(0, 0.06), rng.gauss(0, 0.06), 0.0))
            key = palette if rng.random() < 0.75 else "burlap"
            _frond(meshes[key], rng, base, az, scale * rng.uniform(0.55, 1.0))
        if rng.random() < 0.2:    # a green frond or two that has not died yet
            _frond(meshes["moss"], rng, _local(p), rng.uniform(0, 6.28), scale * rng.uniform(0.45, 0.75))


# ---------------------------------------------------------------- brambles

def _cane(canes, leaves_dead, leaves_green, rng, base, az, reach, peak, r0, depth=0):
    out = Vector((math.cos(az), math.sin(az), 0.0))
    side = Vector((-out.y, out.x, 0.0))
    n = 9
    pts, radii = [], []
    wander = rng.uniform(0.08, 0.2) * reach
    phase = rng.uniform(0, 6.28)
    for k in range(n + 1):
        s = k / n
        h = reach * s
        z = peak * (4 * s * (1 - s * 0.85)) ** 0.85
        lat = wander * math.sin(phase + s * 5.0) * s
        p = base + out * h + side * lat + Vector((0, 0, z))
        wx, wy = p.x + F.ORIGIN[0], p.y + F.ORIGIN[1]
        floor = F.ground(wx, wy) - F.LOWER_WARD + 0.025
        p.z = max(p.z, floor)
        pts.append(p)
        radii.append(r0 * (1 - 0.65 * s) + 0.002)
    canes.tube(pts, radii, 4)
    for k in range(3, n + 1):
        if rng.random() < 0.55:
            p = pts[k]
            a = rng.uniform(0, 6.28)
            sz = rng.uniform(0.035, 0.07)
            tgt = leaves_dead if rng.random() < 0.65 else leaves_green
            b = len(tgt.verts)
            e1 = Vector((math.cos(a), math.sin(a), -0.3)) * sz
            e2 = Vector((-math.sin(a), math.cos(a), 0.0)) * sz * 0.6
            tgt.verts += [tuple(p), tuple(p + e1 + e2), tuple(p + e1 * 1.25), tuple(p + e1 - e2)]
            tgt.faces.append((b, b + 1, b + 2, b + 3))
        if depth == 0 and k in (5, 6, 7) and rng.random() < 0.45:
            _cane(canes, leaves_dead, leaves_green, rng, pts[k], az + rng.uniform(-1.0, 1.0),
                  reach * rng.uniform(0.3, 0.55), peak * rng.uniform(0.3, 0.6), r0 * 0.55, depth=1)


def brambles(rng, meshes, points):
    for p in points:
        c = _local(p)
        radius = rng.uniform(0.7, 1.4)
        for i in range(rng.randint(12, 20)):
            az = rng.uniform(0, 6.28)
            _cane(meshes["wood_dark"], meshes["straw"], meshes["moss"], rng, c + Vector((rng.gauss(0, 0.06), rng.gauss(0, 0.06), 0)),
                  az, radius * rng.uniform(0.55, 1.05), radius * rng.uniform(0.45, 0.95), rng.uniform(0.008, 0.013))


# ---------------------------------------------------------------- nettles

def nettles(rng, meshes, points):
    for p in points:
        c = _local(p)
        for i in range(rng.randint(10, 24)):
            a = rng.uniform(0, 6.28)
            r = abs(rng.gauss(0, 0.16))
            base = c + Vector((math.cos(a) * r, math.sin(a) * r, 0.0))
            height = rng.uniform(0.45, 1.0)
            tilt = Vector((rng.gauss(0, 0.10), rng.gauss(0, 0.10), 1.0)).normalized()
            n = 6
            pts = [base + tilt * (height * k / n) for k in range(n + 1)]
            meshes["wood_dark"].tube(pts, [0.0035 * (1 - 0.6 * k / n) for k in range(n + 1)], 3)
            for k in range(2, n + 1):
                for s in (0, 1):
                    ang = rng.uniform(0, 6.28) if s == 0 else ang + math.pi
                    size = 0.075 * (1.0 - 0.45 * k / n) * rng.uniform(0.7, 1.2)
                    out = Vector((math.cos(ang), math.sin(ang), -0.35)) * size
                    cross = Vector((-math.sin(ang), math.cos(ang), 0.0)) * size * 0.45
                    q = pts[k]
                    tgt = meshes["moss"] if rng.random() < 0.7 else meshes["burlap"]
                    b = len(tgt.verts)
                    tgt.verts += [tuple(q), tuple(q + out * 0.6 + cross), tuple(q + out * 1.15), tuple(q + out * 0.6 - cross)]
                    tgt.faces.append((b, b + 1, b + 2, b + 3))


# ---------------------------------------------------------------- grass, rushes, bulrushes

def grass(rng, meshes, points):
    for p in points:
        tmp = _tube.Mesh()
        _blades(tmp, rng, rng.randint(18, 40), rng.uniform(0.22, 0.5), rng.uniform(10, 35))
        key = "straw" if rng.random() < 0.72 else "moss"
        meshes[key].append(tmp, offset=tuple(_local(p)))


def _reed(mesh, rng, base, height, bend):
    az = rng.uniform(0, 6.28)
    out = Vector((math.cos(az), math.sin(az), 0.0))
    side = Vector((-out.y, out.x, 0.0))
    n = 7
    pts, pos = [], Vector(base)
    lean = math.radians(rng.uniform(2, 10))
    for k in range(n + 1):
        t = k / n
        pts.append(pos.copy())
        a = lean + math.radians(bend) * t ** 1.8
        pos = pos + (out * math.sin(a) + Vector((0, 0, math.cos(a)))) * (height / n)
    w0 = rng.uniform(0.010, 0.017)
    mesh.blade(pts, [w0 * (1 - k / n) ** 0.7 + 0.001 for k in range(n + 1)], side, twist=rng.uniform(-1, 1))


def rushes(rng, meshes, points):
    for p in points:
        c = _local(p)
        dead = rng.random() < 0.45
        for i in range(rng.randint(10, 24)):
            r = abs(rng.gauss(0, 0.11))
            a = rng.uniform(0, 6.28)
            base = c + Vector((math.cos(a) * r, math.sin(a) * r, 0.0))
            _reed(meshes["straw" if dead or rng.random() < 0.3 else "moss"], rng, base,
                  rng.uniform(0.5, 1.15), rng.uniform(15, 70))


def bulrushes(rng, meshes, points):
    for p in points:
        c = _local(p)
        for i in range(rng.randint(2, 4)):
            base = c + Vector((rng.gauss(0, 0.12), rng.gauss(0, 0.12), 0.0))
            height = rng.uniform(1.1, 1.6)
            lean = Vector((rng.gauss(0, 0.06), rng.gauss(0, 0.06), 1.0)).normalized()
            n = 6
            pts = [base + lean * (height * k / n) + Vector((0, 0, 0)) for k in range(n + 1)]
            meshes["straw"].tube(pts, [0.006 * (1 - 0.4 * k / n) for k in range(n + 1)], 4)
            top = pts[-1]
            head = [top + lean * (-0.22 + 0.2 * k / 4) for k in range(5)]
            head_r = [0.0, 0.021, 0.024, 0.021, 0.0]
            meshes["wood_dark"].tube(head, head_r, 6)
            meshes["straw"].tube([top, top + lean * 0.14], [0.003, 0.0015], 3)
            for k in range(rng.randint(2, 3)):
                _reed(meshes["moss"], rng, base + Vector((rng.gauss(0, 0.08), rng.gauss(0, 0.08), 0.0)),
                      rng.uniform(0.6, 1.0), rng.uniform(30, 75))


# ---------------------------------------------------------------- the whole undergrowth

def build(mats, root, seed=5):
    rng = random.Random(seed)
    m = _Meshes()
    bracken(rng, m, _scatter(rng, BRACKEN_CLUMPS, lambda r: _mixed(r, (4, 2, 5))))
    brambles(rng, m, _scatter(rng, BRAMBLES, lambda r: _mixed(r, (4, 3, 5)), max_slope=0.9))
    nettles(rng, m, _scatter(rng, NETTLE_CLUMPS, lambda r: _mixed(r, (5, 3, 1))))
    grass(rng, m, _scatter(rng, GRASS_TUFTS, lambda r: _mixed(r, (4, 3, 4)), avoid_track=False))
    rushes(rng, m, _scatter(rng, REED_CLUMPS, _water_edge, avoid_track=False, max_slope=0.0))
    bulrushes(rng, m, _scatter(rng, BULRUSHES, _water_edge, avoid_track=False, max_slope=0.0))
    m.finish(mats, root, "ditch")

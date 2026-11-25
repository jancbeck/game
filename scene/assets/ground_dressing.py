"""Ground dressing for the whole courtyard: the foot of every wall, and litter on the floor.

One prop with its root at the origin of the world; all geometry is in world meters. It reads
the location's plan.json itself, so it needs no per-wall entries. Place it once, last in "props"
(the prop list is built in order, and the footprints of the props before it are kept clear):

    "ground_dressing": {"pos": [0.0, 0.0], "rot_z": 0}

Wall feet. The wall blocks of the plan are boxes. Every face that looks into the courtyard is
walked in steps of 7 cm. Where the floor in front of it is free, a run begins: it ends at a
doorway, a prop, a strip placed by `base_dressing`, or another wall. Along each run:

- a mud and silt fillet leans against the wall. It is 1 to 12 cm high and 5 to 55 cm wide,
  has bare stretches, and piles up to 20 cm in a corner where two walls meet.
- a ragged splash stain climbs the stone above it.
- a wet gutter, a thin ribbon of standing water, lies along the outer edge of the fillet in
  stretches, and widens into a pool where the ground dips.
- tufts of weed and dead grass grow in the mud, small fallen stones and gravel lie on it.

Litter. Maps of the floor from mats/cobble_wet.py (the same ones the floor shader uses) say where
straw lies, where animals stood and where setts are missing. There it scatters wisps of straw,
piles of dung, and a few loose setts at the rim of the holes.

Nothing here knows a camera. Everything stays below 25 cm, except tufts of dead grass.
"""

import math

import bpy
import numpy as np
from mathutils import Vector, noise

import location
from planlib import inside_polygon as _inside_polygon

from . import _tube
from .grass_tuft import _blades

STEP = 0.07  # meters between samples along a wall
OFFSET = 0.10  # the sample point lies this far out from the face
MIN_RUN = 0.45  # shorter runs are dropped
FRACTIONS = (0.0, 0.05, 0.12, 0.20, 0.30, 0.42, 0.55, 0.70, 0.85, 1.0)  # columns of the fillet mesh, as shares of its width
BASE = 0.003  # everything rests this far above the floor, so it never z-fights with it
KEEP_MARGIN = 0.06  # extra clearance around a prop's footprint
SOFT_LEVEL = 0.2  # behind a prop the fillet is this share of its height, and bare of tufts and stones
SKIP_PROPS = ("tree", "dead_bush", "grass_tuft", "treeline", "west_ditch", "road", "crow", "human", "watch_hood", "palas",
              "base_dressing#o")  # props outside the courtyard, or high up
HARD_PROPS = ("wall_stair", "ladder", "gate_door")  # nothing is laid where these stand
SKIP_MATERIALS = ("smoke", "embers", "fire", "rain", "haze")  # volumes and flames have no footprint


def _smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


class _Noise:
    """Perlin noise with an offset of its own, so every build differs."""

    def __init__(self, rng):
        self.o = Vector((rng.uniform(-300, 300), rng.uniform(-300, 300), rng.uniform(-300, 300)))

    def __call__(self, x, y=0.0, z=0.0):
        return noise.noise(Vector((x, y, z)) + self.o)

    def unit(self, x, y=0.0, z=0.0):
        return 0.5 + 0.5 * self(x, y, z)


# ---------------------------------------------------------------- what is where
def _maps(plan):
    from mats import cobble_wet
    return cobble_wet.ground_maps(plan)


def _lookup(maps, name, x, y):
    from mats import cobble_wet as cw
    i = min(max(int((y - cw.MAP_Y0) * cw.PPM), 0), cw.MAP_H - 1)
    j = min(max(int((x - cw.MAP_X0) * cw.PPM), 0), cw.MAP_W - 1)
    return float(maps[name][i, j])


def _prop_footprints():
    """Where the props already built touch the floor: rectangles (cx, cy, half x, half y, rotation), a little grown.

    One rectangle per mesh, from its vertices lower than 35 cm. Meshes that float above that, flames and volumes
    leave nothing. Strips of `base_dressing` come from their plan entry, since they are placed along a wall.
    Returns (hard, soft): the footprints of stairs and ladders, where nothing may be laid, and of the other props,
    where only a thin line of silt runs behind them.
    """
    hard, soft = [], []
    for root in bpy.data.objects:
        if root.type != "EMPTY" or not root.name.startswith("prop_"):
            continue
        key = root.name[len("prop_"):]
        if any(key.startswith(k) for k in SKIP_PROPS) or key.startswith("base_dressing"):
            continue
        for ob in [root] + list(root.children_recursive):
            if ob.type != "MESH" or ob.hide_render or not len(ob.data.vertices):
                continue
            if any(m and any(w in m.name for w in SKIP_MATERIALS) for m in ob.data.materials):
                continue
            co = np.empty(len(ob.data.vertices) * 3, np.float32)
            ob.data.vertices.foreach_get("co", co)
            mw = np.array(ob.matrix_world)
            world = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
            low = world[world[:, 2] < 0.35]
            if not len(low):
                continue
            x0, x1, y0, y1 = low[:, 0].min(), low[:, 0].max(), low[:, 1].min(), low[:, 1].max()
            if x1 - x0 < 14.0 and y1 - y0 < 14.0:
                rect = ((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 + KEEP_MARGIN, (y1 - y0) / 2 + KEEP_MARGIN, 0.0)
                (hard if key.split("#")[0] in HARD_PROPS else soft).append(rect)
    return hard, soft


def _strip_rects(plan):
    """Rectangles of the strips of `base_dressing` along the walls, from their plan entries."""
    rects = []
    for key, p in plan["props"].items():
        if key.startswith("_") or not key.startswith("base_dressing") or key.startswith("base_dressing#o"):
            continue
        sx = p.get("scale", 1.0)
        sx = sx[0] if isinstance(sx, (list, tuple)) else sx
        rot = math.radians(p.get("rot_z", 0.0))
        cx = p["pos"][0] - math.sin(rot) * 0.25
        cy = p["pos"][1] + math.cos(rot) * 0.25
        rects.append((cx, cy, 2.0 * sx + 0.1, 0.25 + 0.05, rot))
    return rects


def _doorway_rects(plan):
    """The gate opening and the doors at floor level."""
    rects = []
    for b in plan["blocks"].values():
        if isinstance(b, dict) and "cut_gate" in b:
            g = b["cut_gate"]
            half = g["width"] / 2 + 0.3
            cy, hy = b["center"][1], b["size"][1] / 2
            rects.append((g["x"], cy - hy, half, 1.0, 0.0))
    for key, m in plan.get("mounted", {}).items():
        if not key.startswith("_") and key.split("#")[0] == "lit_door" and m["pos"][2] < 1.0:
            rects.append((m["pos"][0], m["pos"][1], 0.9, 1.0, 0.0))
    return rects


def _in_rect(x, y, r, grow=0.0):
    cx, cy, hx, hy, rot = r
    c, s = math.cos(rot), math.sin(rot)
    dx, dy = x - cx, y - cy
    return abs(dx * c + dy * s) < hx + grow and abs(-dx * s + dy * c) < hy + grow


class _Run:
    """A stretch of wall foot: start point, unit vectors along the wall and out of it, length."""

    def __init__(self, p0, along, out, length, corner0, corner1, states):
        self.p0, self.along, self.out, self.length = p0, along, out, length
        self.corner0, self.corner1 = corner0, corner1  # the run ends at another wall there
        raw = np.array([1.0 if st == 2 else SOFT_LEVEL for st in states])  # one value per sample along the run
        k = max(1, int(0.25 / (length / max(1, len(states) - 1)))) if len(states) > 1 else 1
        pad = np.pad(raw, k, mode="edge")
        self.factor = np.convolve(pad, np.ones(2 * k + 1) / (2 * k + 1), mode="valid")
        self.up = (along[0] * out[1] - along[1] * out[0]) > 0  # (along, out) turns counter-clockwise seen from above

    def point(self, s, d):
        return (self.p0[0] + self.along[0] * s + self.out[0] * d, self.p0[1] + self.along[1] * s + self.out[1] * d)

    def free(self, s):
        """1 where the floor in front of the wall is free, SOFT_LEVEL behind a prop; smooth along the run."""
        f = self.factor
        x = min(max(s / self.length, 0.0), 1.0) * (len(f) - 1)
        i = min(int(x), len(f) - 2) if len(f) > 1 else 0
        return float(f[i] + (f[min(i + 1, len(f) - 1)] - f[i]) * (x - i)) if len(f) > 1 else float(f[0])


def _runs(plan, maps, hard, soft):
    """Stretches of wall foot, from the faces of the wall blocks that look into the courtyard.

    A run goes on over soft footprints and ends at hard ones, at the edge of the courtyard, and at other walls.
    """
    from mats import cobble_wet as cw
    rects = cw._wall_rects(plan)
    poly = [tuple(p) for p in plan["platform"]["polygon"]]

    def state(x, y, own):
        """0 where nothing can be laid, 1 behind a prop, 2 on free floor."""
        if not _inside_polygon(x, y, poly) or any(_in_rect(x, y, r) for r in hard):
            return 0
        if _lookup(maps, "yard", x, y) < 0.5 or any(_in_rect(x, y, r) for k, r in enumerate(rects) if k != own):
            return 0
        return 1 if any(_in_rect(x, y, r) for r in soft) else 2

    def walled(x, y):
        return any(_in_rect(x, y, r, 0.02) for r in rects)

    runs = []
    for k, (cx, cy, hx, hy, rot) in enumerate(rects):
        u = (math.cos(rot), math.sin(rot))
        v = (-math.sin(rot), math.cos(rot))
        for nl, along, half_n, half_a in (((0, -1), u, hy, hx), ((0, 1), u, hy, hx), ((1, 0), v, hx, hy), ((-1, 0), v, hx, hy)):
            out = (nl[0] * u[0] + nl[1] * v[0], nl[0] * u[1] + nl[1] * v[1])
            start = (cx + out[0] * half_n, cy + out[1] * half_n)
            n = max(2, int(2 * half_a / STEP))
            dt = 2 * half_a / n
            begin, states = None, []
            for i in range(n + 1):
                t = -half_a + i * dt
                px, py = start[0] + along[0] * t, start[1] + along[1] * t
                st = state(px + out[0] * OFFSET, py + out[1] * OFFSET, k)
                if st and begin is None:
                    begin, states = t, []
                if begin is not None and st:
                    states.append(st)
                if begin is not None and (not st or i == n):
                    end = t if st else t - dt
                    if end - begin >= MIN_RUN:
                        p0 = (start[0] + along[0] * begin, start[1] + along[1] * begin)
                        pe = (start[0] + along[0] * end, start[1] + along[1] * end)
                        before = (p0[0] - along[0] * 0.2 + out[0] * OFFSET, p0[1] - along[1] * 0.2 + out[1] * OFFSET)
                        after = (pe[0] + along[0] * 0.2 + out[0] * OFFSET, pe[1] + along[1] * 0.2 + out[1] * OFFSET)
                        runs.append(_Run(p0, along, out, end - begin, walled(*before), walled(*after), states))
                    begin = None
    return runs


# ---------------------------------------------------------------- the fillet
class _Foot:
    """Shape of the dressing along one run: heights, widths and where it is bare."""

    def __init__(self, run, nz):
        self.run, self.nz = run, nz
        self.seed = nz.unit(run.p0[0] * 0.37, run.p0[1] * 0.37) * 40.0

    def cover(self, s):
        """0 on a bare stretch, 1 where silt has piled up."""
        return _smooth((self.nz.unit(s * 0.42, self.seed, 1.0) - 0.28) / 0.34)

    def corner(self, s, amount):
        r = self.run
        near = 0.0
        if r.corner0:
            near = max(near, math.exp(-s / 0.55))
        if r.corner1:
            near = max(near, math.exp(-(r.length - s) / 0.55))
        return amount * near

    def width(self, s):
        w = (0.16 + 0.50 * self.nz.unit(s * 0.7, self.seed, 3.0)) * (0.3 + 0.7 * self.cover(s))
        return (w + self.corner(s, 0.6)) * self.taper(s) * (0.5 + 0.5 * self.run.free(s)) + 0.02

    def taper(self, s):
        r = self.run
        a = 1.0 if r.corner0 else _smooth(s / 0.45)
        b = 1.0 if r.corner1 else _smooth((r.length - s) / 0.45)
        return a * b

    def height(self, s, q):
        """Height above the floor at run position s and share q of the width (0 at the wall)."""
        if q >= 1.0:
            return 0.0
        top = (0.035 + 0.12 * self.nz.unit(s * 1.1, self.seed, 5.0)) * (0.25 + 0.75 * self.cover(s))
        top += self.corner(s, 0.13) * (1.0 - q)
        lumps = 0.5 + 0.5 * self.nz(s * 7.0, q * 3.0 + self.seed, 8.0)
        return self.taper(s) * self.run.free(s) * (1.0 - q) ** 1.35 * (top * (0.8 + 0.4 * lumps) + 0.006 * lumps)

    def at(self, s, d):
        """Height at distance d from the wall."""
        return self.height(s, d / self.width(s))


def _grid(run, foot, mesh, values):
    """Fillet surface of one run, appended to `mesh`; its outer edge follows the width, at floor level."""
    n = max(2, int(run.length / STEP))
    base = len(mesh.verts)
    cols = len(FRACTIONS)
    for i in range(n + 1):
        s = run.length * i / n
        w = foot.width(s)
        for q in FRACTIONS:
            x, y = run.point(s, q * w)
            mesh.verts.append((x, y, BASE + foot.height(s, q)))
            values.append(1.0)
    for i in range(n):
        for j in range(cols - 1):
            a = base + i * cols + j
            quad = (a, a + cols, a + cols + 1, a + 1)
            mesh.faces.append(quad if run.up else quad[::-1])


def _stain(run, foot, mesh, values):
    """Ragged splash stain on the wall face above the fillet: a ribbon 6 mm off the stone."""
    n = max(2, int(run.length / 0.1))
    base = len(mesh.verts)
    for i in range(n + 1):
        s = run.length * i / n
        x, y = run.point(s, 0.006)
        low = BASE + foot.height(s, 0.0) * 0.5
        rag = 0.65 + 0.2 * foot.nz(s * 2.3, foot.seed, 11.0) + 0.15 * foot.nz(s * 9.0, foot.seed, 13.0)
        top = low + (0.05 + 0.21 * foot.nz.unit(s * 1.3, foot.seed, 9.0)) * (0.3 + 0.7 * foot.cover(s)) * foot.taper(s) * rag
        mesh.verts.append((x, y, low))
        mesh.verts.append((x, y, max(low + 0.004, top)))
        values += [1.0, 1.0]
    for i in range(n):
        a = base + 2 * i
        quad = (a, a + 2, a + 3, a + 1)
        mesh.faces.append(quad[::-1] if run.up else quad)


def _gutter(run, foot, mesh, values, nz):
    """Wet gutter: standing water along the edge of the fillet, in stretches, wider where the ground dips."""
    n = max(2, int(run.length / 0.06))
    base = len(mesh.verts)
    rows = []
    for i in range(n + 1):
        s = run.length * i / n
        wet = _smooth((nz.unit(s * 0.55, foot.seed, 21.0) - 0.40) / 0.22)
        wet *= _smooth(s / 0.5) * _smooth((run.length - s) / 0.5) * _smooth((run.free(s) - 0.6) / 0.3)
        width = (0.05 + 0.09 * nz.unit(s * 1.8, foot.seed, 23.0)
                 + 0.20 * _smooth((wet - 0.6) / 0.4) * nz.unit(s * 0.5, foot.seed, 25.0)) * wet
        d0 = foot.width(s) * 0.92 + 0.04 + 0.03 * nz(s * 3.0, foot.seed, 27.0)
        rows.append((d0, width))
    for i, (d0, width) in enumerate(rows):
        s = run.length * i / n
        for d in (d0, d0 + width * 0.5, d0 + width):
            x, y = run.point(s, d)
            mesh.verts.append((x, y, BASE + 0.0015))
            values.append(1.0)
    for i in range(n):
        if rows[i][1] < 0.004 and rows[i + 1][1] < 0.004:
            continue
        for j in range(2):
            a = base + i * 3 + j
            quad = (a, a + 3, a + 4, a + 1)
            mesh.faces.append(quad if run.up else quad[::-1])


# ---------------------------------------------------------------- stones, tufts
_ICO = None


def _ico():
    """Unit icosphere (subdivision 1) as (verts, faces)."""
    global _ICO
    if _ICO is None:
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
        verts = [tuple(v.co) for v in bm.verts]
        index = {v: i for i, v in enumerate(bm.verts)}
        faces = [tuple(index[v] for v in f.verts) for f in bm.faces]
        bm.free()
        _ICO = (verts, faces)
    return _ICO


def _rock(mesh, rng, x, y, z, size, squash=(1.0, 0.8, 0.55), sink=0.35):
    """A rough stone: an icosphere with a jittered surface, a flat bottom, half sunk in the mud."""
    verts, faces = _ico()
    rz = rng.uniform(0, math.pi)
    c, s = math.cos(rz), math.sin(rz)
    base = len(mesh.verts)
    for vx, vy, vz in verts:
        j = rng.uniform(0.78, 1.18)
        px, py, pz = vx * j * size * squash[0], vy * j * size * squash[1], vz * j * size * squash[2]
        pz = max(pz, -sink * size * squash[2])
        mesh.verts.append((x + px * c - py * s, y + px * s + py * c, z + pz))
    mesh.faces.extend(tuple(base + i for i in f) for f in faces)


def _chunk(mesh, rng, x, y, z, size):
    """A broken-off lump of masonry: a box with its corners pushed about, lying flat and tilted a little."""
    w, d, h = size * rng.uniform(0.9, 1.4), size * rng.uniform(0.6, 0.9), size * rng.uniform(0.4, 0.7)
    rz = rng.uniform(0, math.pi)
    tilt = (rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2))
    c, s = math.cos(rz), math.sin(rz)
    base = len(mesh.verts)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                px = sx * w / 2 * rng.uniform(0.85, 1.1)
                py = sy * d / 2 * rng.uniform(0.85, 1.1)
                pz = sz * h / 2 * rng.uniform(0.8, 1.1) + h * 0.3 + px * tilt[0] + py * tilt[1]
                mesh.verts.append((x + px * c - py * s, y + px * s + py * c, z + pz))
    sides = (((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)),
             ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)),
             ((1, 1, 0), (0, 1, 0), (0, 1, 1), (1, 1, 1)), ((0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1)))
    for quad in sides:
        mesh.faces.append(tuple(base + cx * 4 + cy * 2 + cz for cx, cy, cz in quad))


def _merge(dst, src, dx, dy, dz):
    base = len(dst.verts)
    dst.verts += [(x + dx, y + dy, z + dz) for x, y, z in src.verts]
    dst.faces += [tuple(i + base for i in f) for f in src.faces]


def _dress_wall(run, foot, rng, parts):
    """Weeds, grass, stones, chunks of masonry and gravel along one run."""
    green, dry, stones, gravel, chunks = parts
    length = run.length
    # clusters of weed and dead grass, where silt has piled up and in the corners
    for _ in range(max(1, int(length / 0.65))):
        s = rng.uniform(0.05, length - 0.05)
        corner = (run.corner0 and s < 0.7) or (run.corner1 and length - s < 0.7)
        if run.free(s) < 0.9 or rng.random() > 0.2 + 0.8 * foot.cover(s) + (0.4 if corner else 0.0):
            continue
        w = max(foot.width(s), 0.12)
        for _ in range(rng.randint(2, 5)):
            ss = min(max(s + rng.gauss(0, 0.16), 0.02), length - 0.02)
            d = rng.uniform(0.04, max(0.06, w * 0.85))
            x, y = run.point(ss, d)
            tmp = _tube.Mesh()
            tall = rng.uniform(0.08, 0.24) if rng.random() < 0.75 else rng.uniform(0.22, 0.38)
            _blades(tmp, rng, rng.randint(7, 15), tall, rng.uniform(10, 40))
            _merge(green if rng.random() < 0.45 else dry, tmp, x, y, BASE + foot.at(ss, d))
    # fallen stones
    for _ in range(max(1, int(length / 1.3))):
        s = rng.uniform(0.05, length - 0.05)
        d = rng.uniform(0.03, 0.5)
        if run.free(s) < 0.9:
            continue
        x, y = run.point(s, d)
        _rock(stones, rng, x, y, BASE + foot.at(s, d), rng.choice((0.03, 0.04, 0.05, 0.065, 0.085)) * rng.uniform(0.85, 1.2))
    s = rng.uniform(0.3, max(0.31, length - 0.3))
    if rng.random() < length / 7.0 and run.free(s) > 0.9:
        d = rng.uniform(0.12, 0.4)
        x, y = run.point(s, d)
        _chunk(chunks, rng, x, y, BASE + foot.at(s, d), rng.uniform(0.11, 0.17))
    # gravel, mostly near the wall
    for _ in range(int(length * rng.uniform(6, 14))):
        s = rng.uniform(0.0, length)
        d = abs(rng.gauss(0.12, 0.2))
        if run.free(s) < 0.9:
            continue
        x, y = run.point(s, d)
        _rock(gravel, rng, x, y, BASE + foot.at(s, d), rng.uniform(0.008, 0.022), (1.0, 0.8, 0.6), 0.3)


# ---------------------------------------------------------------- litter
def _pick(rng, weight, count):
    """Up to `count` distinct (x, y) points of the map, in world meters, with probability proportional to `weight`."""
    from mats import cobble_wet as cw
    flat = np.clip(weight, 0.0, None).ravel().astype(np.float64)
    count = min(count, int((flat > 0).sum()))
    if count <= 0:
        return []
    flat /= flat.sum()
    idx = np.random.default_rng(rng.randrange(1 << 30)).choice(flat.size, size=count, replace=False, p=flat)
    out = []
    for k in idx:
        i, j = divmod(int(k), cw.MAP_W)
        out.append((cw.MAP_X0 + (j + rng.random()) / cw.PPM, cw.MAP_Y0 + (i + rng.random()) / cw.PPM))
    return out


def _wisp(mesh, rng, x, y, z):
    """A few straws that lie together, each a flat ribbon with its tip a little raised."""
    phi = rng.uniform(0, math.pi)
    for k in range(rng.randint(4, 9)):
        yaw = phi + rng.uniform(-0.35, 0.35) + rng.choice((0.0, math.pi))
        length = rng.uniform(0.14, 0.36)
        off = rng.uniform(-0.05, 0.05)
        px = x - math.sin(phi) * off + rng.uniform(-0.04, 0.04)
        py = y + math.cos(phi) * off + rng.uniform(-0.04, 0.04)
        width = rng.uniform(0.016, 0.03)
        lift = rng.uniform(0.0, 0.02) if rng.random() < 0.25 else 0.0
        base = len(mesh.verts)
        pts = []
        for t in range(4):
            f = t / 3
            pts.append((px + math.cos(yaw) * length * f, py + math.sin(yaw) * length * f, z + 0.002 * k + lift * f * f))
            yaw += rng.uniform(-0.12, 0.12)
        for i, (qx, qy, qz) in enumerate(pts):
            a = pts[min(i + 1, 3)]
            b = pts[max(i - 1, 0)]
            ang = math.atan2(a[1] - b[1], a[0] - b[0])
            wx, wy = -math.sin(ang) * width / 2, math.cos(ang) * width / 2
            mesh.verts += [(qx + wx, qy + wy, qz), (qx - wx, qy - wy, qz)]
        for i in range(3):
            c = base + 2 * i
            mesh.faces.append((c, c + 1, c + 3, c + 2))


def _dung(mesh, rng, x, y, z):
    """A pile of dung: four to eight lumps of different sizes in a loose heap 15 to 30 cm across, the last ones on top."""
    spread = rng.uniform(0.06, 0.12)
    count = rng.randint(5, 10)
    for k in range(count):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.0, spread) * (0.5 if k >= count - 2 else 1.0)
        size = rng.uniform(0.024, 0.052)
        _rock(mesh, rng, x + math.cos(a) * r, y + math.sin(a) * r, z + (0.022 if k >= count - 2 else 0.0), size,
              (rng.uniform(0.9, 1.3), rng.uniform(0.7, 1.0), rng.uniform(0.45, 0.7)), 0.2)


def _litter(maps, rng, parts):
    straw, pale, dung, setts = parts
    yard = np.clip(maps["yard"], 0.0, 1.0)
    dry_floor = 1.0 - 0.7 * np.clip(maps["depth"] * 40.0, 0.0, 1.0)
    for x, y in _pick(rng, yard * maps["straw"] ** 1.3 * dry_floor, 260):
        _wisp(straw if rng.random() < 0.55 else pale, rng, x, y, BASE + 0.004)
    for x, y in _pick(rng, yard * maps["dung"] ** 1.6, 32):
        _dung(dung, rng, x, y, BASE)
    rim = 4.0 * maps["earth"] * (1.0 - maps["earth"])
    for x, y in _pick(rng, yard * rim * (maps["walls"] > 0.5), 26):
        _chunk(setts, rng, x, y, BASE, rng.uniform(0.11, 0.15))


# ---------------------------------------------------------------- build
def _object(mesh, name, mat, root, attr=None, values=None, flat=False):
    if not mesh.faces:
        return None
    ob = mesh.to_object(name, mat, root)
    if flat:
        for p in ob.data.polygons:
            p.use_smooth = False
    if attr:
        a = ob.data.attributes.new(name=attr, type="FLOAT", domain="POINT")
        a.data.foreach_set("value", values)
    return ob


def build(kit, mats, rng):
    root = kit.group("ground_dressing")
    plan = location.plan()
    maps = _maps(plan)
    nz = _Noise(rng)
    hard, soft = _prop_footprints()
    runs = _runs(plan, maps, hard + _strip_rects(plan) + _doorway_rects(plan), soft)

    fillet, stain, gutter = _tube.Mesh(), _tube.Mesh(), _tube.Mesh()
    dress_f, dress_s, wet = [], [], []
    parts = tuple(_tube.Mesh() for _ in range(5))  # green, dry, stones, gravel, chunks
    for run in runs:
        foot = _Foot(run, nz)
        _grid(run, foot, fillet, dress_f)
        _stain(run, foot, stain, dress_s)
        _gutter(run, foot, gutter, wet, nz)
        _dress_wall(run, foot, rng, parts)

    _object(fillet, "wall_foot_mud", mats["mud"], root, "dress", dress_f)
    _object(stain, "wall_foot_stain", mats["mud"], root, "dress", dress_s)
    _object(gutter, "wall_foot_gutter", mats["mud"], root, "gutter", wet)
    _object(parts[0], "wall_foot_weeds", mats["moss"], root)
    _object(parts[1], "wall_foot_grass", mats["straw"], root)
    _object(parts[2], "wall_foot_stones", mats["stone_wall"], root)
    _object(parts[3], "wall_foot_gravel", mats["stone_wall"], root)
    _object(parts[4], "wall_foot_chunks", mats["stone_wall"], root, flat=True)

    straw, pale, dung, setts = _tube.Mesh(), _tube.Mesh(), _tube.Mesh(), _tube.Mesh()
    _litter(maps, rng, (straw, pale, dung, setts))
    _object(straw, "litter_straw", mats["straw"], root)
    _object(pale, "litter_straw_pale", mats["rope"], root)
    _object(dung, "litter_dung", mats["wood_old"], root)
    _object(setts, "litter_setts", mats["stone_wall"], root, flat=True)
    print(f"ground_dressing: {len(runs)} wall runs, {sum(r.length for r in runs):.1f} m")
    return root

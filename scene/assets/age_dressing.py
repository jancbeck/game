"""Age of the castle: growth where a small garrison does not weed, and ivy on the outer faces.

One prop with its root at the origin of the world; all geometry is in world meters. It reads
the location's plan.json and the merlon objects that build_scene.py made from it, so it needs no per-wall
entries. Place it once, after `ground_dressing` and before `road`:

    "age_dressing": {"pos": [0.0, 0.0], "rot_z": 0}

Wall tops. Soil and grit gather where water stands and boots do not reach:

- crenel gaps: about a third of them hold a tuft of grass, a fern or a moss cushion on the sill,
  more of them in clusters along a wall; the stump of a fallen merlon always has weeds;
- the foot of the parapet on the wall-walk: weeds and moss in clusters, kept clear in front of
  the doors onto the wall-walk and at the head of the wall stair;
- the open edge of the wall-walk on the courtyard side: a few tufts;
- two self-sown saplings: one in the corner where the east chamfer meets the east curtain, one
  growing out of a joint high on the outer face of the south-east curtain.

Ivy grows only on outer faces, from the lower ward up, as a mat of stems and leaves with a
ragged top. It is kept off the arrow slits, and on the gatehouse it is cut back to a straight
edge 2.3 m from the gate opening. The west curtain and the west face of the north-west tower are
left to `west_ditch`, which dresses them.

Repairs, worn treads and the algae of north-facing feet are in mats/stone_wall.py.
Late autumn: ferns are partly brown, the saplings are bare, ivy is evergreen.
"""

import math
import re

import bpy
from mathutils import Vector

import location
from planlib import resolve_block

from . import _tube
from .grass_tuft import _blades
from .ground_dressing import _Noise

GAP_SHARE = 0.36  # share of crenel gaps with growth on the sill
FOOT_STEP = 0.45  # meters between candidate clumps along the foot of a parapet
FOOT_SHARE = 0.30  # share of those candidates that hold a clump (clustered)
EDGE_SHARE = 0.10  # same for the open courtyard edge of the wall-walk
DOOR_CLEAR = 1.3  # no growth this close to a door onto the wall-walk
LEAF = (0.06, 0.11)  # ivy leaf length range in m
LEAF_STEP = 0.055  # meters between leaf nodes along an ivy stem

# Ivy on outer faces: face origin (x, y), along direction, outward normal, ranges along the face
# (s0, s1, height above the lower ward), whether the face has the battered plinth, and a hard cut.
IVY = [
    # south-east curtain, outer face: the east end, clear of the slits and the banner
    {"o": (8.097, -11.724), "u": (0.9135, 0.4067), "spans": [(2.65, 4.15, 6.0)], "plinth": True},
    # the curtain's lower west stage, outer face, beside its slit
    {"o": (5.216, -13.061), "u": (0.9135, 0.4067), "spans": [(-0.95, -0.35, 5.0)], "plinth": True},
    # gatehouse, outer face west of the gate: cut back 2.3 m from the opening
    {"o": (3.2, 6.6), "u": (-1.0, 0.0), "spans": [(8.2, 10.1, 6.5)], "plinth": True, "cut": 8.2},
    # north-east tower, north face
    {"o": (7.0, 7.8), "u": (-1.0, 0.0), "spans": [(0.3, 2.6, 8.5)], "plinth": True},
    # east curtain, outer face
    {"o": (13.3, -12.0), "u": (0.0, 1.0), "spans": [(1.6, 4.6, 5.5)], "plinth": True},
]
SAPLINGS = [
    # (x, y, z of the root, growth direction, height in m)
    ((12.55, -4.35, 6.0), (0.0, 0.0, 1.0), 1.5),
    ((8.097 + 0.9135 * -1.4, -11.724 + 0.4067 * -1.4, 5.15), (0.4067 * 0.9, -0.9135 * 0.9, 0.45), 1.1),
]


# ---------------------------------------------------------------- plants
def _tuft(green, dry, rng, p, scale=1.0):
    """Weeds and grass: green blades in the middle, dead ones round them."""
    tmp = _tube.Mesh()
    _blades(tmp, rng, rng.randint(14, 26), rng.uniform(0.22, 0.45) * scale, rng.uniform(15, 40))
    dry.append(tmp, 1.0, tuple(p))
    tmp = _tube.Mesh()
    _blades(tmp, rng, rng.randint(6, 14), rng.uniform(0.18, 0.34) * scale, rng.uniform(5, 25))
    green.append(tmp, 1.0, tuple(p))


def _fern(green, dry, rng, p):
    """A wall fern: six to ten arching fronds, widest a third of the way out, some turned brown."""
    n = rng.randint(6, 10)
    for k in range(n):
        az = 2 * math.pi * k / n + rng.uniform(-0.3, 0.3)
        out = Vector((math.cos(az), math.sin(az), 0.0))
        length = rng.uniform(0.30, 0.55)
        lift = math.radians(rng.uniform(35, 70))
        droop = math.radians(rng.uniform(50, 110))
        pts, widths, pos = [], [], Vector(p)
        steps = 6
        for i in range(steps + 1):
            t = i / steps
            pts.append(pos.copy())
            widths.append(0.11 * length * math.sin(math.pi * min(1.0, 0.15 + t * 0.95)) + 0.004)
            ang = lift - droop * t * t
            pos = pos + (out * math.cos(ang) + Vector((0, 0, math.sin(ang)))) * (length / steps)
        (dry if rng.random() < 0.3 else green).blade(pts, widths, Vector((-out.y, out.x, 0)), fold=0.08)


def _cushion(mesh, rng, p, size):
    """A moss cushion: a few flattened lumps."""
    from .ground_dressing import _rock
    for _ in range(rng.randint(2, 4)):
        q = (p[0] + rng.uniform(-size, size) * 0.6, p[1] + rng.uniform(-size, size) * 0.6, p[2])
        _rock(mesh, rng, q[0], q[1], q[2], size * rng.uniform(0.6, 1.0), (1.0, 0.85, 0.42), 0.4)


def _growth(parts, rng, p, kind=None):
    green, dry, moss = parts
    kind = kind or rng.choices(("tuft", "fern", "moss"), (0.55, 0.2, 0.25))[0]
    if kind == "tuft":
        _tuft(green, dry, rng, p)
        if rng.random() < 0.5:
            _cushion(moss, rng, p, rng.uniform(0.05, 0.09))
    elif kind == "fern":
        _fern(green, dry, rng, p)
    else:
        _cushion(moss, rng, p, rng.uniform(0.07, 0.13))
        if rng.random() < 0.4:
            _tuft(green, dry, rng, p, 0.6)


def _sapling(bark, rng, root, direction, height):
    """A bare self-sown sapling: a thin stem that turns upward, a few side shoots, twigs."""
    d = Vector(direction).normalized()
    pos = Vector(root)
    pts, radii = [], []
    steps = 9
    r0 = 0.012 + 0.006 * height
    for i in range(steps + 1):
        t = i / steps
        pts.append(pos.copy())
        radii.append(r0 * (1 - 0.85 * t) + 0.002)
        d = (d + Vector((rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15), 0.35))).normalized()
        pos = pos + d * (height / steps)
    bark.tube(pts, radii, 5)
    for i in range(3, steps):
        for _ in range(rng.randint(1, 2)):
            a = rng.uniform(0, 2 * math.pi)
            bd = Vector((math.cos(a), math.sin(a), rng.uniform(0.6, 1.4))).normalized()
            q, bp, br = pts[i].copy(), [], []
            blen = height * rng.uniform(0.18, 0.4) * (1.1 - i / steps)
            for k in range(5):
                bp.append(q.copy())
                br.append(radii[i] * 0.55 * (1 - k / 5) + 0.0015)
                bd = (bd + Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0.25))).normalized()
                q = q + bd * (blen / 4)
            bark.tube(bp, br, 3)


# ---------------------------------------------------------------- wall tops
def _footprints(plan, heights):
    out = []
    for b in plan["blocks"].values():
        if not isinstance(b, dict):
            continue
        b = resolve_block(b)
        h = _h(b["h"], heights)
        out.append((b["center"], (b["size"][0] / 2, b["size"][1] / 2), math.radians(b.get("rot_z", 0)), h))
    return out


def _h(v, heights):
    return heights[v] if isinstance(v, str) else float(v)


def _covered(x, y, z, prints):
    """True where a higher block stands over the point (a tower over the end of a curtain)."""
    for (cx, cy), (hw, hd), rot, top in prints:
        dx, dy = x - cx, y - cy
        lx = dx * math.cos(rot) + dy * math.sin(rot)
        ly = -dx * math.sin(rot) + dy * math.cos(rot)
        if abs(lx) < hw + 0.02 and abs(ly) < hd + 0.02 and top > z + 0.3:
            return True
    return False


def _clear_points(plan):
    """Points on the wall-walk kept clear: doors at wall-walk level and the head of the wall stair."""
    pts = []
    for key, m in plan.get("mounted", {}).items():
        if key.split("#")[0] == "lit_door" and m["pos"][2] > 1.0:
            pts.append(tuple(m["pos"]))
    st = plan["props"].get("wall_stair")
    if isinstance(st, dict):
        r = math.radians(st.get("rot_z", 0))
        x, y = st["pos"][0] + math.cos(r) * 3.6, st["pos"][1] + math.sin(r) * 3.6
        pts.append((x, y, 6.0))
    return pts


def _near(p, pts, d):
    return any((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 < d * d and abs(p[2] - q[2]) < 1.5 for q in pts)


def _crenels(parts, rng, nz, clear):
    """Growth on crenel sills between merlons, and on the stumps of fallen ones."""
    pat = re.compile(r"^merlon_(.+)_([+-][xy]|center)_(\d+)(_stump)?$")
    rows = {}
    for ob in bpy.data.objects:
        m = pat.match(ob.name)
        if not m or ob.type != "MESH":
            continue
        mw = ob.matrix_world
        co = [mw @ v.co for v in ob.data.vertices]
        c = sum(co, Vector()) / len(co)
        z0 = min(v.z for v in co)
        rows.setdefault((m.group(1), m.group(2)), []).append((int(m.group(3)), c, z0, bool(m.group(4))))
    count = 0
    for key, row in rows.items():
        row.sort()
        for (i, c, z0, stump), nxt in zip(row, row[1:] + [None]):
            if stump:
                p = Vector((c.x, c.y, z0 + 0.12))
                _growth(parts, rng, p, "tuft")
                _growth(parts, rng, p + Vector((rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), 0)), "moss")
                count += 1
                continue
            if nxt is None or nxt[0] != i + 1 or nxt[3]:
                continue
            g = (c + nxt[1]) / 2
            p = Vector((g.x, g.y, min(z0, nxt[2]) + 0.003))
            if _near(p, clear, DOOR_CLEAR):
                continue
            if rng.random() + (nz.unit(g.x * 0.35, g.y * 0.35, 3.0) - 0.5) * 0.8 < 1.0 - GAP_SHARE:
                continue
            j = Vector((rng.uniform(-0.12, 0.12), rng.uniform(-0.12, 0.12), 0))
            _growth(parts, rng, p + j)
            count += 1
    return count


def _wall_walks(parts, rng, nz, plan, prints, clear):
    """Weeds at the foot of each parapet on the wall-walk, and a few on the open edge."""
    heights, md = plan["heights"], plan["merlon"]["depth"]
    count = 0
    for name, b in plan["blocks"].items():
        if not isinstance(b, dict) or name.startswith("_"):
            continue
        b = resolve_block(b)
        edges = b.get("merlons", [])
        if "center" in edges or not edges:
            continue
        if "all" in edges:
            edges = ["+x", "-x", "+y", "-y"]
        h = _h(b["h"], heights)
        w, d = b["size"]
        rot = math.radians(b.get("rot_z", 0))
        ux, uy = Vector((math.cos(rot), math.sin(rot), 0)), Vector((-math.sin(rot), math.cos(rot), 0))
        c = Vector((*b["center"], h))
        lines = []
        for e in ("+x", "-x", "+y", "-y"):
            along, half_len, normal, half_n = (ux, w / 2, uy, d / 2) if e in ("+y", "-y") else (uy, d / 2, ux, w / 2)
            sign = 1 if e[0] == "+" else -1
            if e in edges:
                lines.append((c + normal * sign * (half_n - md - 0.1), along, half_len - md - 0.1, FOOT_SHARE))
            elif len(edges) == 1 and e == {"+x": "-x", "-x": "+x", "+y": "-y", "-y": "+y"}[edges[0]]:
                lines.append((c + normal * sign * (half_n - 0.12), along, half_len - 0.1, EDGE_SHARE))
        for base, along, half_len, share in lines:
            n = max(1, int(2 * half_len / FOOT_STEP))
            for k in range(n + 1):
                s = -half_len + 2 * half_len * k / n
                p = base + along * (s + rng.uniform(-0.1, 0.1))
                if _covered(p.x, p.y, h, prints) or _near(p, clear, DOOR_CLEAR):
                    continue
                if rng.random() * 0.6 + nz.unit(p.x * 0.3, p.y * 0.3, h) * 0.8 < 1.2 - share * 1.4:
                    continue
                _growth(parts, rng, p + Vector((0, 0, 0.003)))
                count += 1
    return count


# ---------------------------------------------------------------- ivy
def _ivy(leaves, stems, rng, nz, face, span, lw):
    """One ivy mat on an outer face between s0 and s1, up to `top` m above the lower ward."""
    o, u = Vector((*face["o"], 0)), Vector((*face["u"], 0))
    n = Vector((u.y, -u.x, 0))  # outward: the wall body is on the left of u
    s0, s1, top = span
    cut = face.get("cut")
    flare_top = lw + 2.4

    def at(s, z, off):
        flare = 0.5 * max(0.0, min(1.0, (flare_top - z) / 2.4)) if face.get("plinth") else 0.0
        return o + u * s + n * (flare + off) + Vector((0, 0, z))

    def ceiling(s):
        """Ragged top of the mat: highest in the middle of the span."""
        q = (s - s0) / max(s1 - s0, 0.1)
        shape = math.sin(math.pi * min(max(q, 0.0), 1.0)) ** 0.5
        return lw + top * (0.35 + 0.65 * shape) * (0.75 + 0.4 * nz.unit(s * 1.3, top, 5.0))

    def inside(s):
        return s0 - 0.15 <= s <= s1 + 0.15 and (cut is None or s <= cut)

    def leaf(s, z):
        if not inside(s) or z > ceiling(s) + 0.1:
            return
        size = rng.uniform(*LEAF)
        base = at(s, z, rng.uniform(0.02, 0.07))
        tip_dir = (Vector((rng.uniform(-0.5, 0.5), 0, 0)) + u * rng.uniform(-0.4, 0.4) + n * rng.uniform(0.3, 0.9)
                   + Vector((0, 0, -rng.uniform(0.2, 0.9)))).normalized()
        side = tip_dir.cross(n).normalized() if abs(tip_dir.dot(n)) < 0.95 else u
        tip = base + tip_dir * size
        mid = base + tip_dir * size * 0.45 + n * 0.01
        k = len(leaves.verts)
        leaves.verts += [tuple(base), tuple(mid + side * size * 0.45), tuple(tip), tuple(mid - side * size * 0.45)]
        leaves.faces += [(k, k + 1, k + 2), (k, k + 2, k + 3)]

    def grow(s, z, ds, dz, length, r):
        pts, radii = [], []
        steps = max(2, int(length / LEAF_STEP))
        for i in range(steps):
            if not inside(s) or z > ceiling(s):
                break
            pts.append(at(s, z, 0.015))
            radii.append(r * (1 - 0.7 * i / steps) + 0.002)
            for _ in range(rng.randint(1, 3)):
                leaf(s + rng.gauss(0, 0.06), z + rng.gauss(0, 0.05))
            ds += rng.gauss(0, 0.25)
            ds = max(-0.8, min(0.8, ds))
            norm = math.hypot(ds, dz)
            s += ds / norm * LEAF_STEP
            z += dz / norm * LEAF_STEP
        if len(pts) > 1:
            stems.tube(pts, radii, 3)
        return pts

    for _ in range(max(2, int((s1 - s0) * 2.2))):
        s = rng.uniform(s0, s1)
        main = grow(s, lw - 0.05, rng.uniform(-0.2, 0.2), 1.0, top * 1.3, 0.012)
        # side shoots climb sideways and up from the main stems
        for _ in range(int(len(main) / 9)):
            if len(main) < 3:
                break
            i = rng.randrange(1, len(main) - 1)
            q = main[i] - o
            grow(q.dot(u), main[i].z, rng.choice((-1, 1)) * rng.uniform(0.6, 1.2), rng.uniform(0.2, 0.9),
                 rng.uniform(0.3, 1.4), 0.006)
    # fill: the mat is dense near the ground and thins toward its ragged top
    area = (s1 - s0) * top
    for _ in range(int(area * 120)):
        s = rng.uniform(s0, s1)
        z = lw + (ceiling(s) - lw) * (1 - rng.random() ** 0.7)
        leaf(s, z)


# ---------------------------------------------------------------- build
def build(kit, mats, rng):
    root = kit.group("age_dressing")
    plan = location.plan()
    nz = _Noise(rng)
    prints = _footprints(plan, plan["heights"])
    clear = _clear_points(plan)

    parts = (_tube.Mesh(), _tube.Mesh(), _tube.Mesh())  # green, dry, moss cushions
    gaps = _crenels(parts, rng, nz, clear)
    walks = _wall_walks(parts, rng, nz, plan, prints, clear)
    parts[0].to_object("wall_top_weeds", mats["moss"], root)
    parts[1].to_object("wall_top_grass", mats["straw"], root)
    parts[2].to_object("wall_top_moss", mats["moss"], root)

    bark = _tube.Mesh()
    for p, d, h in SAPLINGS:
        _sapling(bark, rng, p, d, h)
    bark.to_object("wall_saplings", mats["bark"], root)

    lw = plan["heights"]["lower_ward"]
    stems = _tube.Mesh()
    tris = 0
    for i, face in enumerate(IVY):
        for j, span in enumerate(face["spans"]):
            leaves = _tube.Mesh()
            _ivy(leaves, stems, rng, nz, face, span, lw)
            tris += leaves.tris()
            if leaves.faces:
                ob = leaves.to_object(f"ivy_{i}_{j}", mats["moss"], root)
                for poly in ob.data.polygons:
                    poly.use_smooth = False
    stems.to_object("ivy_stems", mats["bark"], root)
    print(f"age_dressing: {gaps} crenel clumps, {walks} wall-walk clumps, ivy {tris} leaf tris, "
          f"{sum(m.tris() for m in parts) + bark.tris() + stems.tris()} other tris")
    return root

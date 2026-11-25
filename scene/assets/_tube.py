"""Shared geometry for vegetation props: tapered tubes, recursive branching, grass blades.

Not a prop itself (the leading underscore keeps it out of `assets.available()`).
tree.py, dead_bush.py and grass_tuft.py build one merged mesh each with these.

`Mesh` collects vertices and faces; `Grower` grows a branch tree into it.
Everything is built at real size in meters, so object scale stays 1.
"""

import math
from collections import deque

import bpy
from mathutils import Vector

GOLDEN = 2.399963  # radians


def rand_unit(rng):
    v = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1)))
    if v.length < 1e-6:
        return Vector((0, 0, 1))
    return v.normalized()


def perp_frame(t):
    """Two unit vectors perpendicular to the unit vector `t` and to each other."""
    ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
    a = t.cross(ref).normalized()
    return a, t.cross(a)


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []

    def tris(self):
        return sum(len(f) - 2 for f in self.faces)

    def tube(self, pts, radii, sides, lobe=0.0, lobe_n=3, lobe_phase=0.0, lobe_twist=0.0,
             cap_end=False):
        """Tapered tube along the polyline `pts` with one radius per point.

        `lobe` ribs the cross-section (`lobe_n` ribs, spiraling by `lobe_twist`
        radians per ring), which turns a smooth trunk into a fluted, twisted one.
        """
        n = len(pts)
        base = len(self.verts)
        angles = [2 * math.pi * k / sides for k in range(sides)]
        prev = None
        for i, c in enumerate(pts):
            t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
            if t.length < 1e-9:
                t = Vector((0, 0, 1))
            t.normalize()
            if prev is None:
                ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
                nrm = ref - t * ref.dot(t)
            else:
                nrm = prev - t * prev.dot(t)
            nrm.normalize()
            prev = nrm
            bn = t.cross(nrm)
            r = radii[i]
            for a in angles:
                rr = r
                if lobe:
                    rr = r * (1 + lobe * math.cos(lobe_n * a + lobe_phase + lobe_twist * i))
                co, si = math.cos(a) * rr, math.sin(a) * rr
                self.verts.append(tuple(c + nrm * co + bn * si))
        for i in range(n - 1):
            r0, r1 = base + i * sides, base + (i + 1) * sides
            for k in range(sides):
                k2 = (k + 1) % sides
                self.faces.append((r0 + k, r0 + k2, r1 + k2, r1 + k))
        if cap_end:
            self.faces.append(tuple(range(base + (n - 1) * sides, base + n * sides)))

    def blade(self, pts, widths, side, fold=0.25, twist=0.0):
        """Grass blade: a V-folded ribbon along `pts`, `side` is the horizontal width axis."""
        n = len(pts)
        base = len(self.verts)
        side = side.normalized()
        for i, c in enumerate(pts):
            t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
            t.normalize()
            nrm = side.cross(t).normalized()
            w = side
            if twist:
                a = twist * i / max(1, n - 1)
                w = side * math.cos(a) + nrm * math.sin(a)
                nrm = w.cross(t).normalized()
            hw = widths[i] / 2
            self.verts.append(tuple(c - w * hw))
            self.verts.append(tuple(c + nrm * (widths[i] * fold)))
            self.verts.append(tuple(c + w * hw))
        for i in range(n - 1):
            a, b = base + i * 3, base + (i + 1) * 3
            self.faces.append((a, a + 1, b + 1, b))
            self.faces.append((a + 1, a + 2, b + 2, b + 1))

    def append(self, other, scale=1.0, offset=(0.0, 0.0, 0.0)):
        """Add a copy of `other`, scaled about the origin and moved by `offset`."""
        base = len(self.verts)
        ox, oy, oz = offset
        self.verts.extend((x * scale + ox, y * scale + oy, z * scale + oz) for x, y, z in other.verts)
        self.faces.extend(tuple(i + base for i in f) for f in other.faces)

    def scale(self, s):
        self.verts = [(x * s, y * s, z * s) for x, y, z in self.verts]

    def max_z(self):
        return max(v[2] for v in self.verts)

    def to_object(self, name, mat, parent):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.verts, [], self.faces)
        me.update()
        if hasattr(me, "shade_smooth"):
            me.shade_smooth()
        else:
            for p in me.polygons:
                p.use_smooth = True
        if mat is not None:
            me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        bpy.context.collection.objects.link(ob)
        ob.parent = parent
        return ob


class Params:
    """Branching rules. List fields are indexed by branch level (clamped to the last entry)."""

    def __init__(self, **kw):
        self.seg = [0.22]            # ring spacing along a branch, m
        self.gnarl = [0.3]           # random wander per step
        self.kink = [0.1]            # chance per step of a sharp bend
        self.up = [0.0]              # per-step pull toward +Z (negative droops)
        self.spring = [0.0]          # pull back toward the branch's start direction, stops long arcs
        self.keep = 0.65             # how much of the last wander is kept (lower = more jagged)
        self.max_turn = 0.75         # most a branch may turn between two rings, radians
        self.density = [3.0]         # lateral children per meter of branch
        self.angle = [(30, 65)]      # child angle from the parent, degrees
        self.up_bias = [0.0]         # extra +Z added to a child's start direction
        self.shrink = [(0.5, 0.7)]   # child start radius / parent radius at the fork
        self.len_ratio = [(0.4, 0.75)]
        self.t_first = [0.2]         # first fork, as a fraction of the branch
        self.collar = 0.35           # swelling where a branch leaves its parent
        self.end_ratio = 0.35        # end radius / start radius when the branch forks again
        self.tip_ratio = 0.12        # same for a branch that ends in a point
        self.r_min = 0.0045          # no child thinner than this
        self.min_len = 0.12
        self.max_level = 7
        self.break_p = 0.0           # chance per branch (level >= 2) of a snapped stub
        self.floor = None            # branches never go below this z ...
        self.floor_level = 1         # ... from this level on
        self.max_branches = 6000
        self.sides = default_sides
        self.lobe = {}               # level -> (amplitude, ribs, twist per ring)
        for k, v in kw.items():
            setattr(self, k, v)

    def at(self, name, level):
        v = getattr(self, name)
        return v[min(level, len(v) - 1)]


def default_sides(r):
    if r < 0.008:
        return 3
    if r < 0.012:
        return 4
    if r < 0.03:
        return 5
    if r < 0.06:
        return 6
    if r < 0.12:
        return 8
    if r < 0.2:
        return 10
    return 12


class Grower:
    """Grows branches breadth-first, so a branch limit thins the finest twigs first."""

    def __init__(self, mesh, rng, params, fine=None, fine_r=0.02):
        """With `fine`, branches whose thickest radius is under `fine_r` go into that second mesh."""
        self.mesh, self.rng, self.P = mesh, rng, params
        self.fine, self.fine_r = fine, fine_r
        self.queue = deque()
        self.count = 0

    def add(self, start, direction, length, r0, level=0, **spec):
        spec.update(start=Vector(start), dir=Vector(direction).normalized(), length=length,
                    r0=r0, level=level)
        self.queue.append(spec)

    def run(self):
        while self.queue and self.count < self.P.max_branches:
            self._branch(self.queue.popleft())

    def _stoch_round(self, x):
        n = int(x)
        return n + (1 if self.rng.random() < x - n else 0)

    def _branch(self, s):
        P, rng = self.P, self.rng
        lv = s["level"]
        length, r0 = s["length"], s["r0"]
        broken = False
        if lv >= 2 and rng.random() < P.break_p:
            length *= rng.uniform(0.35, 0.65)
            broken = True
        steps = max(2, round(length / P.at("seg", lv)))
        step = length / steps

        # path
        d, pos = s["dir"].copy(), s["start"].copy()
        pts = [pos.copy()]
        wander = rand_unit(rng)
        sway = s.get("sway")
        for i in range(steps):
            wander = wander * P.keep + rand_unit(rng) * (1 - P.keep)
            dd = d + wander * P.at("gnarl", lv) + (s["dir"] - d) * P.at("spring", lv)
            dd.z += P.at("up", lv) - s.get("droop", 0.0) * i / steps
            if sway:
                amp, freq, ph = sway
                dd += Vector((math.cos(ph + i * freq), math.sin(ph + i * freq), 0)) * amp
            if rng.random() < P.at("kink", lv):
                dd += rand_unit(rng) * rng.uniform(0.5, 0.9)
            dd.normalize()
            turn = d.angle(dd, 0.0)
            if turn > P.max_turn:
                dd = d.slerp(dd, P.max_turn / turn)
            d = dd.normalized()
            pos = pos + d * step
            if P.floor is not None and lv >= P.floor_level and pos.z < P.floor:
                pos.z = P.floor
                d.z = abs(d.z) * 0.5
                d.normalize()
            pts.append(pos.copy())
        n = len(pts)

        def radii_for(end_ratio):
            out = []
            for i in range(n):
                t = i / steps
                r = r0 * (1 - (1 - end_ratio) * t ** 0.9)
                if lv >= 1 and P.collar:
                    r *= 1 + P.collar * max(0.0, 1 - t / 0.2)
                out.append(r)
            return out

        n_term = 0
        if broken:
            end_ratio = 0.8
        elif lv >= P.max_level or r0 * P.end_ratio * 0.85 < P.r_min:
            end_ratio = P.tip_ratio
        else:
            end_ratio = s.get("end_ratio", P.end_ratio)
            n_term = s.get("n_term", 2)
        radii = radii_for(end_ratio)
        radii = [max(r, 0.0015) for r in radii]
        if s.get("flare"):
            amp, scale = s["flare"]
            z0 = pts[0].z
            radii = [r * (1 + amp * math.exp(-max(0.0, p.z - z0) / scale)) for r, p in zip(radii, pts)]

        lobe = P.lobe.get(lv)
        kw = {}
        if lobe:
            kw = dict(lobe=lobe[0], lobe_n=lobe[1], lobe_twist=lobe[2],
                      lobe_phase=rng.uniform(0, 6.28))
        target = self.fine if self.fine is not None and max(radii) < self.fine_r else self.mesh
        target.tube(pts, radii, s.get("sides") or P.sides(max(radii)), cap_end=broken, **kw)
        self.count += 1
        if broken or lv >= P.max_level:
            return

        def point_at(t):
            f = t * steps
            i = min(int(f), n - 2)
            u = f - i
            p = pts[i].lerp(pts[i + 1], u)
            tan = (pts[i + 1] - pts[i]).normalized()
            r = radii[i] * (1 - u) + radii[i + 1] * u
            return p, tan, r

        # lateral children
        if "n_lat" in s:
            n_lat = s["n_lat"]
        else:
            n_lat = self._stoch_round(P.at("density", lv) * length)
        t0, t1 = s.get("t_range", (P.at("t_first", lv), 0.95))
        azim = rng.uniform(0, 2 * math.pi)
        for j in range(n_lat):
            t = t0 + (t1 - t0) * (j + rng.uniform(0.1, 0.9)) / n_lat
            p, tan, r_here = point_at(t)
            r_c = r_here * rng.uniform(*P.at("shrink", lv))
            if r_c < P.r_min:
                continue
            azim += GOLDEN + rng.uniform(-0.6, 0.6)
            ang = math.radians(rng.uniform(*P.at("angle", lv)))
            a, b = perp_frame(tan)
            cd = tan * math.cos(ang) + (a * math.cos(azim) + b * math.sin(azim)) * math.sin(ang)
            cd.z += P.at("up_bias", lv)
            c_len = max(P.min_len, length * rng.uniform(*P.at("len_ratio", lv)) * (1 - 0.35 * t))
            self.add(p, cd, c_len, r_c, lv + 1)

        # terminal fork: the branch carries on as two thinner ones
        if n_term:
            r_c = radii[-1] * rng.uniform(0.85, 1.0)
            if "term_shrink" in s:
                r_c = radii[-1] * rng.uniform(*s["term_shrink"])
            if r_c >= P.r_min:
                p, tan, _ = point_at(1.0)
                a, b = perp_frame(tan)
                az0 = rng.uniform(0, 2 * math.pi)
                lo, hi = s.get("term_angle", (18, 42))
                for k in range(n_term):
                    az = az0 + 2 * math.pi * k / n_term + rng.uniform(-0.4, 0.4)
                    ang = math.radians(rng.uniform(lo, hi))
                    cd = tan * math.cos(ang) + (a * math.cos(az) + b * math.sin(az)) * math.sin(ang)
                    cd.z += P.at("up_bias", lv)
                    t_len = s.get("term_len")
                    c_len = t_len * rng.uniform(0.8, 1.2) if t_len else max(
                        P.min_len, length * rng.uniform(0.5, 0.85))
                    self.add(p, cd, c_len, r_c * rng.uniform(0.9, 1.0), lv + 1)

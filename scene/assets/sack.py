"""Burlap grain sacks: clusters whose layout, count, sizes and cloth change with the seed.

Five layouts (a standing group, a pile of lying sacks, a split-open sack with grain spilled on
the floor, sacks slumping into each other like dominoes, a pair) are drawn at random. Each sack
has its own size (0.55 to 1.0 m tall), lumps and slump, one of three closures (rope-tied neck,
rolled-down open cuff with grain showing, sewn-shut crest), and a cloth: burlap, pale `straw`
cloth, or either one with a patch of the other. Every sack is one smooth mesh; the spill is a
grain mound, a stream of grain lumps and loose kernels in `straw`. The cluster is centered on the
origin and about 1 to 1.6 m across.
"""

import math

from mathutils import Euler, Vector

# (height fraction, radius factor): flat foot, belly, then the closure
PROFILES = {
    "tied": ((0.0, 0.78), (0.04, 0.95), (0.12, 1.0), (0.35, 1.02), (0.55, 0.93), (0.66, 0.68),
             (0.73, 0.30), (0.77, 0.20), (0.82, 0.30), (0.9, 0.52), (0.97, 0.58), (1.0, 0.50)),
    "cuffed": ((0.0, 0.78), (0.04, 0.95), (0.12, 1.0), (0.4, 1.02), (0.7, 0.92), (0.88, 0.8),
               (0.97, 0.74), (1.0, 0.72)),
    "sewn": ((0.0, 0.78), (0.04, 0.95), (0.12, 1.0), (0.4, 1.02), (0.7, 0.96), (0.88, 0.88),
             (0.96, 0.78), (1.0, 0.7)),
}
NECK_U = 0.77
RINGS, SEGS = 24, 20
SLIT = (7, 12, 1, 3)       # ring span and segment span of the split opening


def _profile(style, u):
    pts = PROFILES[style]
    for (u0, r0), (u1, r1) in zip(pts, pts[1:]):
        if u <= u1:
            t = 0.5 - 0.5 * math.cos(math.pi * (u - u0) / (u1 - u0))
            return r0 + (r1 - r0) * t
    return pts[-1][1]


def _smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def _sack_mesh(rng, style, h, rx, ry, bend, slit):
    p = [rng.uniform(0, 2 * math.pi) for _ in range(5)]
    frill_amp = {"tied": 0.14, "cuffed": 0.07, "sewn": 0.03}[style]
    verts, faces, rows, cxs = [], [], [], []
    for k in range(RINGS + 1):
        u = k / RINGS
        pr = _profile(style, u)
        neck = math.exp(-((u - NECK_U) / 0.09) ** 2) if style == "tied" else 0.0
        if style == "sewn":
            aspect = ry / rx * (1 - 0.75 * _smooth(0.8, 1.0, u))
        else:
            aspect = ry / rx + (1 - ry / rx) * neck      # the section turns round at the tie
        cx = bend * u * u
        frill = frill_amp * _smooth(0.78, 1.0, u)
        row = []
        for i in range(SEGS):
            a = 2 * math.pi * i / SEGS
            lump = (1 + 0.06 * math.sin(2 * a + p[0] + 5 * u) + 0.05 * math.sin(3 * a + p[1] - 7 * u)
                    + 0.025 * math.sin(5 * a + p[2] + 11 * u) + frill * math.sin(6 * a + p[3]))
            lump = 1 + (lump - 1) * (1 - 0.8 * neck)
            r = rx * pr * lump
            z = u * h + (frill > 0.05) * _smooth(0.78, 1.0, u) * rng.uniform(-0.02, 0.02)
            row.append(len(verts))
            verts.append((cx + r * math.cos(a), r * aspect * math.sin(a), z))
        rows.append(row)
        cxs.append(cx)
    for k in range(RINGS):
        for i in range(SEGS):
            if slit and slit[0] <= k < slit[1] and slit[2] <= i < slit[3]:
                continue
            n = (i + 1) % SEGS
            faces.append((rows[k][i], rows[k][n], rows[k + 1][n], rows[k + 1][i]))
    top_drop = {"tied": 0.03, "cuffed": 0.1, "sewn": 0.01}[style]
    bottom, top = len(verts), len(verts) + 1
    verts += [(0, 0, 0), (bend, 0, h - top_drop)]
    for i in range(SEGS):
        n = (i + 1) % SEGS
        faces.append((bottom, rows[0][n], rows[0][i]))
        faces.append((top, rows[-1][i], rows[-1][n]))
    return verts, faces, rows, cxs


def _smooth_shade(ob):
    for poly in ob.data.polygons:
        poly.use_smooth = True
    return ob


def _patch(kit, mat, parent, name, verts, rows, cxs, k0, k1, i0, i1):
    """A rectangle of cloth in another material, sitting 4 mm proud of the sack surface."""
    pv, idx = [], {}
    for k in range(k0, k1 + 1):
        for i in range(i0, i1 + 1):
            x, y, z = verts[rows[k][i % SEGS]]
            dx, dy = x - cxs[k], y
            d = math.hypot(dx, dy) or 1.0
            idx[(k, i)] = len(pv)
            pv.append((x + dx / d * 0.004, y + dy / d * 0.004, z))
    pf = [(idx[(k, i)], idx[(k, i + 1)], idx[(k + 1, i + 1)], idx[(k + 1, i)])
          for k in range(k0, k1) for i in range(i0, i1)]
    return _smooth_shade(kit.mesh(name, pv, pf, mat=mat, parent=parent))


class _Cluster:
    def __init__(self, kit, mats, rng, root):
        self.kit, self.mats, self.rng, self.root = kit, mats, rng, root
        self.n = 0

    def cloth(self):
        r = self.rng.random()
        if r < 0.5:
            return "burlap", None
        if r < 0.65:
            return "burlap", "straw"
        if r < 0.8:
            return "straw", "burlap"
        return "straw", None

    def sack(self, loc, yaw, size, tilt=(0, 0), bend=0.0, lift=0.0, style=None, lying=False,
             slit=False, wide=1.0):
        """One sack. `loc` is its base center, or its center when `lying`. Returns a dict with
        the group, its rotation and the placement, which the spill needs."""
        kit, mats, rng = self.kit, self.mats, self.rng
        j = lambda a: kit.jitter(rng, a)  # noqa: E731
        style = style or rng.choices(("tied", "cuffed", "sewn"), (0.65, 0, 0.35) if lying else (0.5, 0.28, 0.22))[0]
        k = 0.6 + 0.4 * size
        h = (0.9 if style != "cuffed" else 0.76) * size + j(0.02)
        rx, ry = 0.26 * k * wide + j(0.01), 0.16 * k * wide + j(0.01)
        main, patch = self.cloth()
        name = f"sack_{self.n}"
        self.n += 1
        if lying:
            tilt = (90, 0)
            d = Vector((math.sin(math.radians(yaw)), -math.cos(math.radians(yaw))))
            loc = (loc[0] - d.x * h / 2, loc[1] - d.y * h / 2)
        slit_spec = SLIT if slit else None
        verts, faces, rows, cxs = _sack_mesh(rng, style, h, rx, ry, bend, slit_spec)
        g = kit.group(name, (loc[0], loc[1], 0), parent=self.root)
        g.rotation_euler = Euler([math.radians(a) for a in (tilt[0], tilt[1], yaw)])
        rot = g.rotation_euler.to_matrix()
        g.location.z = -min((rot @ Vector(v)).z for v in verts) + lift - 0.004
        _smooth_shade(kit.mesh(f"{name}_body", verts, faces, mat=mats[main], parent=g))
        if patch and not slit:
            k0 = rng.randint(3, 7)
            i0 = rng.randint(0, SEGS - 6)
            _patch(kit, mats[patch], g, f"{name}_patch", verts, rows, cxs, k0, k0 + rng.randint(3, 5),
                   i0, i0 + rng.randint(3, 5))
        getattr(self, f"_close_{style}")(g, name, rx, ry, h, bend)
        return {"g": g, "rot": rot, "loc": (loc[0], loc[1]), "yaw": yaw, "h": h, "rx": rx, "ry": ry,
                "bend": bend, "style": style}

    def _close_tied(self, g, name, rx, ry, h, bend):
        kit, mats, rng = self.kit, self.mats, self.rng
        r_tie = rx * _profile("tied", NECK_U) + 0.004
        cx, z = bend * NECK_U ** 2, NECK_U * h
        turns = rng.choice((1, 2, 2, 3))
        minor = rng.choice((0.008, 0.011, 0.013))
        for n in range(turns):
            kit.torus(f"{name}_tie_{n}", r_tie, minor, (cx, 0, z + (n - (turns - 1) / 2) * minor * 2.4),
                      mat=mats["rope"], major_segments=14, parent=g)
        for t in range(rng.choice((1, 2))):
            ang = rng.uniform(0, 2 * math.pi)
            tail = rng.uniform(0.08, 0.2)
            kit.beam(f"{name}_cord_{t}", (cx + r_tie * math.cos(ang), r_tie * math.sin(ang), z),
                     (cx + (r_tie + 0.04) * math.cos(ang), (r_tie + 0.04) * math.sin(ang), z - tail),
                     (minor, minor), mats["rope"], parent=g)

    def _close_cuffed(self, g, name, rx, ry, h, bend):
        """Mouth rolled down into a thick cuff; golden grain shows inside."""
        kit, mats = self.kit, self.mats
        pr = _profile("cuffed", 1.0)
        cx = bend
        roll = kit.torus(f"{name}_cuff", rx * pr * 0.98, 0.032, (cx, 0, h - 0.03), mat=mats["burlap"],
                         major_segments=18, parent=g)
        roll.scale = (1, ry / rx, 1)
        _smooth_shade(roll)
        kit.sphere(f"{name}_grain", 1.0, (cx, 0, h - 0.1), scale=(rx * pr * 0.88, ry * pr * 0.88, 0.07),
                   mat=mats["straw"], segments=10, parent=g)

    def _close_sewn(self, g, name, rx, ry, h, bend):
        """Top sewn flat: a crest of cord with stitch ticks."""
        kit, mats = self.kit, self.mats
        half = rx * _profile("sewn", 1.0) * 0.85
        kit.beam(f"{name}_seam", (bend - half, 0, h + 0.003), (bend + half, 0, h + 0.003), (0.012, 0.012),
                 mats["rope"], parent=g)
        for n in range(8):
            x = bend - half + (n + 0.5) * 2 * half / 8
            kit.box(f"{name}_stitch_{n}", (0.008, 0.05, 0.008), (x, 0, h + 0.006), mat=mats["rope"],
                    parent=g)

    def spill(self, info, side=1):
        """Grain poured out of the slit: a mound on the floor, a stream of lumps, loose kernels."""
        kit, mats, rng = self.kit, self.mats, self.rng
        straw = mats["straw"]
        yaw = math.radians(info["yaw"])
        perp = Vector((math.cos(yaw), math.sin(yaw)))          # the sack's +X side
        axis = Vector((math.sin(yaw), -math.cos(yaw)))         # along the lying sack
        u = (SLIT[0] + SLIT[1]) / 2 / RINGS
        ang = math.radians((SLIT[2] + SLIT[3]) / 2 * 360 / SEGS)
        pr = _profile(info["style"], u)
        local = Vector((info["bend"] * u * u + info["rx"] * pr * math.cos(ang),
                        info["ry"] * pr * math.sin(ang), u * info["h"]))
        p0 = info["rot"] @ local + Vector((info["loc"][0], info["loc"][1], info["g"].location.z))
        gc = Vector((p0.x, p0.y)) + perp * 0.3 + axis * rng.uniform(-0.04, 0.04)

        # mound on the floor
        a_x, a_y, hgt = 0.27, 0.2, 0.12
        verts, faces, rows = [], [], []
        rhos = (0.0, 0.35, 0.65, 0.9, 1.0)
        segs = 14
        for rho in rhos:
            row = []
            for i in range(segs if rho else 1):
                t = 2 * math.pi * i / segs
                rr = rho * (1 + (0.12 * rng.uniform(-1, 1) if rho == 1.0 else 0))
                x = gc.x + perp.x * rr * a_x * math.cos(t) + axis.x * rr * a_y * math.sin(t)
                y = gc.y + perp.y * rr * a_x * math.cos(t) + axis.y * rr * a_y * math.sin(t)
                z = hgt * (1 - rr * rr) ** 0.7 + rng.uniform(0, 0.006) if rho < 1.0 else 0.0
                row.append(len(verts))
                verts.append((x, y, z))
            rows.append(row)
        for i in range(segs):
            n = (i + 1) % segs
            faces.append((rows[0][0], rows[1][i], rows[1][n]))
            for k in range(1, len(rhos) - 1):
                faces.append((rows[k][i], rows[k + 1][i], rows[k + 1][n], rows[k][n]))
        _smooth_shade(kit.mesh("grain_mound", verts, faces, mat=straw, parent=self.root))

        # grain running out of the slit, over the widest point of the sack and down to the mound
        axis_pt = info["rot"] @ Vector((info["bend"] * u * u, 0, u * info["h"])) + Vector(
            (info["loc"][0], info["loc"][1], info["g"].location.z))
        side_pt = Vector((axis_pt.x + perp.x * (info["rx"] * pr + 0.015), axis_pt.y + perp.y * (info["rx"] * pr + 0.015),
                          axis_pt.z))
        drop = Vector((side_pt.x + perp.x * 0.05, side_pt.y + perp.y * 0.05, 0.035))
        edge = Vector((gc.x - perp.x * 0.1, gc.y - perp.y * 0.1, hgt * 0.7))
        path = [p0, side_pt, drop, edge]
        n = 0
        for a, b in zip(path, path[1:]):
            steps = max(2, int((b - a).length / 0.03))
            for s in range(steps):
                pos = a.lerp(b, s / steps)
                r = rng.uniform(0.018, 0.034)
                _smooth_shade(kit.sphere(
                    f"grain_lump_{n}", r, (pos.x + rng.uniform(-0.02, 0.02), pos.y + rng.uniform(-0.02, 0.02),
                                           max(pos.z, r * 0.5)),
                    scale=(rng.uniform(0.9, 1.4), rng.uniform(0.9, 1.4), 0.7), rot_deg=(0, 0, rng.uniform(0, 180)),
                    mat=straw, segments=8, parent=self.root))
                n += 1
        # grain heaped on the mound
        for m in range(45):
            t = rng.uniform(0, 2 * math.pi)
            d = math.sqrt(rng.random()) * 0.85
            x = gc.x + perp.x * d * a_x * math.cos(t) + axis.x * d * a_y * math.sin(t)
            y = gc.y + perp.y * d * a_x * math.cos(t) + axis.y * d * a_y * math.sin(t)
            r = rng.uniform(0.012, 0.022)
            kit.sphere(f"grain_heap_{m}", r, (x, y, hgt * (1 - d * d) ** 0.7 + r * 0.3), scale=(1.3, 1, 0.6),
                       rot_deg=(0, 0, rng.uniform(0, 180)), mat=straw, segments=6, parent=self.root)

        # loose kernels: small flat flecks around the mound
        kv, kf = [], []
        for _ in range(130):
            t = rng.uniform(0, 2 * math.pi)
            d = math.sqrt(rng.random()) * 1.7
            x = gc.x + perp.x * d * a_x * math.cos(t) + axis.x * d * a_y * math.sin(t)
            y = gc.y + perp.y * d * a_x * math.cos(t) + axis.y * d * a_y * math.sin(t)
            s, a = rng.uniform(0.005, 0.011), rng.uniform(0, math.pi)
            base = len(kv)
            for sx, sy in ((-1, -0.5), (1, -0.5), (1, 0.5), (-1, 0.5)):
                kv.append((x + s * (sx * math.cos(a) - sy * math.sin(a)), y + s * (sx * math.sin(a) + sy * math.cos(a)),
                           0.004))
            kf.append((base, base + 1, base + 2, base + 3))
        kit.mesh("grain_kernels", kv, kf, mat=straw, parent=self.root)


# ---------- layouts: positions in the cluster frame, X across, Y toward the camera ----------

def _standing_group(c):
    rng, j = c.rng, (lambda a: c.kit.jitter(c.rng, a))
    side = rng.choice((-1, 1))
    c.sack((0, 0), j(30), rng.uniform(0.9, 1.1), (j(2), j(2)), j(0.05))
    c.sack((side * 0.52, 0.05 + j(0.04)), j(15), rng.uniform(0.65, 0.85), (j(3), -side * (18 + j(6))),
           -side * 0.1, wide=1.15)
    c.sack((-side * 0.44, -0.42), j(40), rng.uniform(0.6, 0.8), (j(3), j(3)), j(0.06), style="cuffed")
    if rng.random() < 0.5:
        c.sack((side * 0.25, -0.72), 90 + j(30), rng.uniform(0.6, 0.75), lying=True, bend=j(0.05))


def _pile(c):
    rng, j = c.rng, (lambda a: c.kit.jitter(c.rng, a))
    yaw = j(25)
    a = c.sack((-0.28, 0), yaw, rng.uniform(0.85, 1.0), lying=True, bend=j(0.05))
    c.sack((0.28, 0.06), yaw + j(10), rng.uniform(0.8, 0.95), lying=True, bend=j(0.05))
    c.sack((0.0, 0.02), yaw + 85 + j(20), rng.uniform(0.7, 0.85), lying=True, lift=2 * a["ry"] * 0.8)
    if rng.random() < 0.6:
        c.sack((rng.choice((-1, 1)) * 0.72, -0.2), j(30), rng.uniform(0.7, 0.9), (j(3), j(3)), j(0.05))


def _spill(c):
    rng, j = c.rng, (lambda a: c.kit.jitter(c.rng, a))
    yaw = rng.choice((0, 180)) + j(30)
    info = c.sack((0, 0), yaw, rng.uniform(0.9, 1.0), lying=True, slit=True, style="tied")
    c.spill(info)
    side = -1 if abs(yaw) < 90 else 1                  # the other side from the spill
    c.sack((side * 0.5, 0.35), j(30), rng.uniform(0.85, 1.05), (j(2), j(2)), j(0.05))
    if rng.random() < 0.5:
        c.sack((side * 0.2, -0.55), j(40), rng.uniform(0.55, 0.7), (j(3), -side * 20), -side * 0.08,
               style="cuffed")


def _domino(c):
    rng, j = c.rng, (lambda a: c.kit.jitter(c.rng, a))
    side = rng.choice((-1, 1))
    c.sack((0, 0), j(20), rng.uniform(0.95, 1.1), (j(2), -side * 4), j(0.04))
    c.sack((side * 0.5, 0.04), j(20), rng.uniform(0.85, 1.0), (j(2), -side * 15), -side * 0.08)
    c.sack((side * 0.98, 0.1), j(25), rng.uniform(0.7, 0.85), (j(3), -side * 30), -side * 0.14, wide=1.15)
    if rng.random() < 0.5:
        c.sack((side * 0.5, -0.62), side * 90 + j(20), rng.uniform(0.6, 0.8), lying=True)


def _pair(c):
    rng, j = c.rng, (lambda a: c.kit.jitter(c.rng, a))
    c.sack((0, 0), rng.uniform(60, 120), rng.uniform(0.9, 1.05), lying=True, bend=j(0.06))
    c.sack((rng.choice((-1, 1)) * 0.5, 0.25), j(40), rng.uniform(0.55, 0.7), (j(4), j(4)), j(0.06),
           style=rng.choice(("cuffed", "tied")))


_LAYOUTS = (_standing_group, _pile, _spill, _domino, _pair)


def build(kit, mats, rng):
    root = kit.group("sacks")
    rng.choice(_LAYOUTS)(_Cluster(kit, mats, rng, root))
    return root

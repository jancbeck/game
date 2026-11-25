"""Crates: three nailed plank crates and a slumped sack against a wall.

A large crate (0.92 x 0.78 x 0.80 m) with a broken front slat, a medium crate on top of
it with the lid knocked ajar and straw spilling out, and a 0.65 m cube beside them with
a rope tied around it (its flat lid is a lantern stand: plan.json puts a lantern at
z = 0.65 on it). Every plank is its own object so wear and tone vary board to board.
Nail heads and straw are merged into one mesh per crate.

Footprint about 1.7 x 1.0 m, wall side at +Y, front facing -Y.
"""

import math

import bmesh
from mathutils import Vector

from ._sweep import rope

# Layout of the stack, shared with tarp.py: (width, depth, height, (x, y), yaw in degrees, base z).
BIG = (0.92, 0.78, 0.80, (-0.38, 0.14), 6.0, 0.0)
MID = (0.56, 0.46, 0.40, (-0.42, 0.20), 29.0, 0.80)
SMALL = (0.65, 0.65, 0.65, (0.58, -0.28), -14.0, 0.0)

PT = 0.022       # plank thickness
GAP = 0.011      # gap between wall planks
BATTEN_W = 0.05
BATTEN_T = 0.016


def _prism(poly, thick, plane="xz"):
    """Closed prism from a 2D polygon (CCW): extruded along Y for 'xz', along Z for 'xy'."""
    n = len(poly)
    t0, t1 = -thick / 2, thick / 2
    if plane == "xz":
        v = [(u, t0, w) for u, w in poly] + [(u, t1, w) for u, w in poly]
    else:
        v = [(u, w, t0) for u, w in poly] + [(u, w, t1) for u, w in poly]
    f = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    f += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    return v, f


def _ragged(rng, length, width, end):
    """Outline of a board whose `end` ('r' or 'l') is snapped into jagged splinters."""
    j = lambda a: rng.uniform(-a, a)
    L, W = length, width
    pts = [(0, 0), (L - 0.02 + j(0.01), 0), (L - 0.05 + j(0.015), 0.26 * W),
           (L + 0.012, 0.44 * W), (L - 0.06 + j(0.01), 0.68 * W), (L - 0.012, W), (0, W)]
    if end == "l":
        pts = [(L - u, w) for u, w in pts][::-1]
    return pts


def _merge_boxes(kit, name, boxes, mat, parent):
    """One mesh from axis-aligned boxes given as (size, center)."""
    verts, faces = [], []
    cv = [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, -.5), (-.5, .5, -.5),
          (-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)]
    cf = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    for size, c in boxes:
        b = len(verts)
        verts += [(c[0] + x * size[0], c[1] + y * size[1], c[2] + z * size[2]) for x, y, z in cv]
        faces += [tuple(b + i for i in f) for f in cf]
    return kit.mesh(name, verts, faces, mat=mat, parent=parent)


def _smooth(ob):
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def _strands(kit, mats, rng, parent, name, count, spawn, wide=1.0):
    """Straw as flat ribbons. spawn() -> (x, y, z, yaw, length, up, droop, floor)."""
    verts, faces = [], []
    seg = 6
    for _ in range(count):
        x, y, z0, yaw, length, up, droop, floor = spawn()
        roll = rng.uniform(-0.9, 0.9)
        width = rng.uniform(0.009, 0.016) * wide
        pts = []
        for k in range(seg + 1):
            t = k / seg
            yaw_t = yaw + 0.5 * math.sin(3 * t + x * 9) * 0.3
            px = x + math.cos(yaw_t) * length * t
            py = y + math.sin(yaw_t) * length * t
            pz = max(z0 + up * t - droop * t * t, floor + 0.004)
            pts.append((px, py, pz))
        base = len(verts)
        for k, (px, py, pz) in enumerate(pts):
            a, b = pts[min(k + 1, seg)], pts[max(k - 1, 0)]
            ang = math.atan2(a[1] - b[1], a[0] - b[0])
            wx, wy, wz = -math.sin(ang) * math.cos(roll), math.cos(ang) * math.cos(roll), math.sin(roll)
            w = width / 2 * (1 - 0.7 * k / seg)
            verts.append((px + wx * w, py + wy * w, pz + wz * w))
            verts.append((px - wx * w, py - wy * w, pz - wz * w))
        for k in range(seg):
            a = base + 2 * k
            faces.append((a, a + 1, a + 3, a + 2))
    return kit.mesh(name, verts, faces, mat=mats["straw"], parent=parent)


def _rope_wrap(kit, mats, rng, parent, w, d, z, turns=2):
    """Rope around the girth of a crate, passing over its battens, knotted at the front."""
    hw, hd = w / 2, d / 2
    per = 2 * (w + d)
    step = 0.03
    n = int(per * turns / step)
    r = 0.011
    ctrl = []

    def bump(a, lo, hi):
        return BATTEN_T if lo < abs(a) < hi else 0.0

    for i in range(n + 1):
        s = (i * step) % per
        # walk the rectangle: front (-Y) left to right, right (+X), back (+Y), left (-X)
        if s < w:
            x, y = -hw + s, -(hd + r + bump(-hw + s, hw - 0.065, hw - 0.015))
        elif s < w + d:
            x, y = hw + r + bump(-hd + (s - w), hd - 0.095, hd - 0.045), -hd + (s - w)
        elif s < 2 * w + d:
            x, y = hw - (s - w - d), hd + r + bump(hw - (s - w - d), hw - 0.065, hw - 0.015)
        else:
            x, y = -(hw + r + bump(hd - (s - 2 * w - d), hd - 0.095, hd - 0.045)), hd - (s - 2 * w - d)
        face_t = (s % (w + d)) / (w + d)
        sag = 0.010 * math.sin(math.pi * (s / per * 4 % 1.0))
        zz = z + 0.040 * (i * step / (per * turns)) - sag + kit.jitter(rng, 0.0015)
        ctrl.append((x, y, zz))
    # the loop shifts in z across two turns, so start and end meet near the front center
    rope(kit, "rope_wrap", ctrl, r, mats["rope"], parent, lay=0.075, step=0.012)
    zk = ctrl[-1][2]
    ky = -(hd + 0.03)
    kit.sphere("rope_knot", 0.024, (0.0, ky, zk), scale=(1.1, 0.8, 0.9), mat=mats["rope"], segments=8,
               parent=parent)
    for side, dz in ((1, 0.26), (-1, 0.17)):
        rope(kit, "rope_end", [(0.0, ky, zk), (side * 0.03, ky - 0.012, zk - 0.05),
                               (side * 0.05, ky - 0.02, zk - dz * 0.55),
                               (side * 0.035 + side * rng.uniform(0, 0.03), ky - 0.03, zk - dz)],
             0.0085, mats["rope"], parent, lay=0.06, step=0.012)


def _crate(kit, mats, rng, root, name, w, d, h, loc, yaw, z0=0.0, lid="shut", broken=None,
           wrap=False, plates=False):
    """One crate. `lid` is 'shut' or 'ajar'; `broken` is the front row whose right half is gone."""
    J = lambda a: kit.jitter(rng, a)
    g = kit.group(name, loc=(loc[0], loc[1], z0), parent=root)
    g.rotation_euler = (0, 0, math.radians(yaw))
    wood, dark, iron = mats["wood_old"], mats["wood_dark"], mats["iron"]
    nails = []

    # interior, seen through plank gaps; its top sits below the lid
    kit.box(f"{name}_liner", (w - 0.04, d - 0.04, h - 0.05), (0, 0, (h - 0.05) / 2), mat=dark, parent=g)

    # wall planks; the lid sits on top of them
    hw = h - PT
    rows = max(3, round(hw / 0.135))
    ph = (hw - (rows - 1) * GAP) / rows
    zc = [r * (ph + GAP) + ph / 2 for r in range(rows)]
    for sgn, face in ((-1, "front"), (1, "back")):
        for r in range(rows):
            y = sgn * (d / 2 - PT / 2) + J(0.0015)
            if broken is not None and face == "front" and r == broken:
                L = w * 0.46
                v, f = _prism(_ragged(rng, L, ph, "r"), PT, "xz")
                kit.mesh(f"{name}_slat_broken", [(x - w / 2 + J(0.002), y + yy, z + zc[r] - ph / 2) for x, yy, z in v],
                         f, mat=wood, parent=g, bevel=0.003)
                continue
            kit.box(f"{name}_{face}{r}", (w + J(0.01), PT, ph + J(0.003)), (J(0.005), y, zc[r] + J(0.002)),
                    (J(0.4), J(0.55), J(0.25)), wood, 0.0035, g)
    for sgn in (-1, 1):
        for r in range(rows):
            kit.box(f"{name}_side{r}", (PT, d - 2 * PT - 0.004, ph + J(0.003)),
                    (sgn * (w / 2 - PT / 2) + J(0.0015), J(0.004), zc[r] + J(0.002)),
                    (J(0.3), J(0.4), J(0.4)), wood, 0.0035, g)

    # battens: two per face, full height; a Z-brace across the front
    bx = w / 2 - 0.04
    by = d / 2 - 0.07
    for sx in (-1, 1):
        for sgn in (-1, 1):
            kit.box(f"{name}_batten", (BATTEN_W, BATTEN_T, h + J(0.004)),
                    (sx * bx + J(0.003), sgn * (d / 2 + BATTEN_T / 2), (h) / 2 + J(0.002)),
                    (0, J(0.4), J(0.5)), dark, 0.003, g)
            kit.box(f"{name}_sbatten", (BATTEN_T, BATTEN_W, h - 0.0 + J(0.004)),
                    (sx * (w / 2 + BATTEN_T / 2), sgn * by + J(0.003), (h) / 2 + J(0.002)),
                    (J(0.4), 0, J(0.5)), dark, 0.003, g)
            for r in range(rows):
                nails.append(((0.011, 0.004, 0.011), (sx * bx, sgn * (d / 2 + BATTEN_T + 0.0005), zc[r])))
                nails.append(((0.004, 0.011, 0.011), (sx * (w / 2 + BATTEN_T + 0.0005), sgn * by, zc[r])))
    p0 = Vector((-(w / 2 - 0.07), -(d / 2 + 0.011), 0.06))
    p1 = Vector(((w / 2 - 0.07), -(d / 2 + 0.011), h - 0.06 - PT))
    kit.beam(f"{name}_brace", p0, p1, section=(0.05, 0.013), mat=dark, bevel=0.003, parent=g)
    for p in (p0, p1):
        nails.append(((0.011, 0.004, 0.011), (p.x, p.y - 0.007, p.z)))

    # lid planks across X, two cleats on top; pivots at the back edge when ajar
    lg = kit.group(f"{name}_lid", parent=g)
    oy = oz = 0.0
    if lid == "ajar":
        oy, oz = d / 2 - 0.012, h
        lg.location = (J(0.01) + 0.02, oy, oz)
        lg.rotation_euler = (math.radians(-17), 0, math.radians(9))
    nl = max(3, round(d / 0.14))
    pw = (d - GAP * (nl - 1)) / nl
    for i in range(nl):
        y = -d / 2 + i * (pw + GAP) + pw / 2
        kit.box(f"{name}_lid{i}", (w + 0.008 + J(0.006), pw + J(0.004), PT),
                (J(0.004), y - oy + J(0.002), (h - PT / 2) - oz + J(0.001)), (J(0.3), J(0.3), J(0.5)),
                wood, 0.0035, lg)
    for sx in (-1, 1):
        cx = sx * (w / 2 - 0.1)
        kit.box(f"{name}_cleat", (0.05, d - 0.03, 0.016), (cx, -oy, h + 0.008 - oz), (0, 0, J(0.5)),
                dark, 0.003, lg)
        for i in range(nl):
            y = -d / 2 + i * (pw + GAP) + pw / 2
            if lid == "shut":
                nails.append(((0.011, 0.011, 0.004), (cx, y, h + 0.016 + 0.0005)))
    if plates:
        for sx in (-1, 1):
            for sy in (-1, 1):
                kit.box(f"{name}_plate", (0.1, 0.1, 0.007),
                        (sx * (w / 2 - 0.052), sy * (d / 2 - 0.052), h + 0.0035), (0, 0, J(2)),
                        iron, 0.0015, g)
                kit.box(f"{name}_strap", (0.04, 0.007, 0.14), (sx * (w / 2 - 0.052), sy * (d / 2 + 0.0035) + sy * 0.0,
                                                                h - 0.07), (0, 0, 0), iron, 0.0015, g)
    _merge_boxes(kit, f"{name}_nails", nails, iron, g)

    # straw: a mound in the mouth of the ajar crate, strands hanging over the front
    if lid == "ajar":
        def mouth():
            return (J(w / 2 - 0.08), J(d / 2 - 0.08), h - 0.09, rng.uniform(0, 6.28),
                    rng.uniform(0.1, 0.3), rng.uniform(0.05, 0.16), rng.uniform(0.0, 0.25), -1)

        def spill():
            return (J(w / 2 - 0.1), -d / 2 + 0.03, h - 0.07, math.pi * 1.5 + J(0.7),
                    rng.uniform(0.15, 0.32), rng.uniform(-0.02, 0.04), rng.uniform(0.2, 0.75), 0.0)
        _strands(kit, mats, rng, g, f"{name}_straw_mound", 70, mouth)
        _strands(kit, mats, rng, g, f"{name}_straw_spill", 34, spill)
    if broken is not None:
        zb = zc[broken]

        def wisp():
            return (w / 2 - 0.26 + J(0.16), -(d / 2 - 0.035), zb + J(0.03), math.pi * 1.5 + J(0.8),
                    rng.uniform(0.10, 0.22), rng.uniform(0.0, 0.03), rng.uniform(0.05, 0.2), 0.0)
        _strands(kit, mats, rng, g, f"{name}_wisps", 16, wisp)
        # the other half of the slat, lying in front of the crate
        L = w * 0.5
        v, f = _prism(_ragged(rng, L, ph, "l"), PT, "xy")
        yawf = math.radians(J(20) + 18)
        c, s = math.cos(yawf), math.sin(yawf)
        pos = (w * 0.18, -(d / 2 + 0.16))
        verts = [(pos[0] + (x - L / 2) * c - (yy) * s, pos[1] + (x - L / 2) * s + yy * c, z + PT / 2 + 0.002)
                 for x, yy, z in v]
        kit.mesh(f"{name}_slat_fallen", verts, f, mat=wood, parent=g, bevel=0.003)
    if wrap:
        _rope_wrap(kit, mats, rng, g, w, d, 0.2 + J(0.02))
    return g


def _sack(kit, mats, rng, parent, loc, yaw, tilt):
    """Slumped burlap sack with a roped neck, leaning on its high side."""
    H, R = 0.6, 0.19
    ph = [rng.uniform(0, 6.28) for _ in range(3)]
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=18, v_segments=14, radius=1.0)
    for v in bm.verts:
        x, y, z = v.co
        t = (z + 1) / 2
        th = math.atan2(y, x)
        r = 1.0 + 0.07 * math.sin(3 * th + ph[0] + 5 * t) + 0.05 * math.sin(7 * th + ph[1] - 4 * t)
        # fuller at the bottom, gathered at the neck
        neck = max(0.0, (t - 0.74) / 0.26)
        r *= (1.0 - 0.8 * neck ** 0.8) * (1.0 + 0.18 * math.sin(math.pi * min(t / 0.5, 1)))
        zz = t * H
        zz = max(zz, 0.012 + 0.03 * (1 - (x * x + y * y) ** 0.5))
        v.co = (x * R * r * 1.05, y * R * r * 0.9, zz)
    verts = [tuple(v.co) for v in bm.verts]
    faces = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    ob = kit.mesh("sack", verts, faces, loc=loc, rot_deg=(tilt, 0, yaw), mat=mats["burlap"], parent=parent)
    _smooth(ob)
    t_tie = 0.80
    rr = R * (1.0 - 0.8 * max(0.0, (t_tie - 0.74) / 0.26) ** 0.8) * 0.6 * 1.05
    kit.torus("sack_tie", rr + 0.006, 0.008, (0, 0, t_tie * H + 0.01), mat=mats["rope"], parent=ob,
              major_segments=14, minor_segments=5)
    return ob


def build(kit, mats, rng):
    root = kit.group("crates")
    w, d, h, loc, yaw, z0 = BIG
    _crate(kit, mats, rng, root, "crate_big", w, d, h, loc, yaw, z0, broken=2, plates=True)
    w, d, h, loc, yaw, z0 = MID
    _crate(kit, mats, rng, root, "crate_mid", w, d, h, loc, yaw, z0, lid="ajar")
    w, d, h, loc, yaw, z0 = SMALL
    _crate(kit, mats, rng, root, "crate_small", w, d, h, loc, yaw, z0, wrap=True)
    _sack(kit, mats, rng, root, (-0.80, -0.52, 0.0), 24.0, 9.0)

    # loose straw trodden around the foot of the stack
    g = root

    tufts = [(rng.uniform(-0.9, 0.9), rng.uniform(-0.78, -0.3)) for _ in range(7)]

    def floor_straw():
        cx, cy = tufts[rng.randrange(len(tufts))]
        return (cx + J(0.12), cy + J(0.08), 0.0, rng.uniform(0, 6.28), rng.uniform(0.08, 0.2),
                0.0, 0.0, 0.0)
    J = lambda a: kit.jitter(rng, a)
    _strands(kit, mats, rng, g, "straw_floor", 36, floor_straw, wide=1.8)
    return root

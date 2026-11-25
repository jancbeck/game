"""Roof of the cookhouse lean-to: sagging frame, open battens and overlapping split shingles.

Shed space: X east, Y toward the tower wall (+Y), Z up. The roof surface is a plane that
rises toward the wall, bowed by the front header and sagging between header and wall.
`surface(x, y)` is the top of the battens; everything on the roof is built from it.

The shingles are grouped by course and by stretch of course. Each group is one object, so the
wood shader gives each its own tone and the courses read as bands from far away.
"""

import math

from . import _shed_geo as geo

X_L, X_R = -2.15, 2.30        # left edge meets the wall stair's flank; right edge overhangs the side wall
Y_F, Y_W = -2.17, 2.12        # eave edge and tower wall
Y_P = -1.95                   # front posts and header
Z_EAVE, RISE = 2.86, 0.95     # batten top at the eave edge and its rise to the wall
SLOPE = RISE / (Y_W - Y_F)
RAFTER_X = (-2.0, -1.2, -0.15, 0.95, 2.0)
BATTEN_T, RAFTER_D, HEADER_H = 0.03, 0.14, 0.16
UNDER = BATTEN_T + RAFTER_D   # batten top down to the underside of the rafters
EXPOSURE, SHINGLE_L = 0.35, 0.78

# stone chimney stack between the rafters at x = -1.2 and x = -0.15, standing against the tower
STACK_X, STACK_Y = (-0.98, -0.36), (1.30, 2.16)
# patches of old grey shingles among the brown: (x, y, radius)
PATCHES = [(1.5, -0.4, 0.45)]
# how far from the eave edge (in courses) and from the stair's flank (m) the roof is darkest and mossiest
DAMP_COURSES, DAMP_WALL = 2, 0.55
SEGMENT = 2.0                 # length of one shingle group along a course


def surface(x, y):
    z = Z_EAVE + (y - Y_F) * SLOPE
    bow = 0.05 * max(0.0, 1.0 - ((x - 0.025) / 1.975) ** 2)
    t = (y - Y_P) / (Y_W - Y_P)
    if t < 0:
        sag = bow + 0.03 * (t / ((Y_F - Y_P) / (Y_W - Y_P))) ** 2
    else:
        sag = bow * (1 - t) + 0.045 * 4 * t * (1 - t)
    bay = 0.02 * math.sin(math.pi * x) ** 2 * max(0.0, min(1.0, t * 1.5))
    return z - sag - bay + 0.01 * math.sin(x * 2.1 + y * 0.9)


def _steps(a, b, n):
    return [a + (b - a) * i / n for i in range(n + 1)]


def _in_zone(zones, x, y, scale=1.0):
    return any((x - cx) ** 2 + (y - cy) ** 2 < (r * scale) ** 2 for cx, cy, r in zones)


def frame(kit, mats, rng, root):
    """Rafters, header, wall ledger with iron straps, battens, fascia and barge boards."""
    wd, wo = mats["wood_dark"], mats["wood_old"]
    iron = mats["iron"]

    for k, x in enumerate(RAFTER_X):
        m = geo.Mesh()
        hw = 0.05 + rng.uniform(0, 0.01)
        secs = []
        for y in _steps(Y_F - 0.1, Y_W - 0.01, 10):
            zt = surface(x, y) - BATTEN_T
            secs.append([(x - hw, y, zt - RAFTER_D), (x + hw, y, zt - RAFTER_D),
                         (x + hw, y, zt), (x - hw, y, zt)])
        m.loft(secs)
        m.finish(f"rafter_{k}", wd, root, bevel=0.008)

    # header under the rafters: bowed by the roof's weight
    m = geo.Mesh()
    secs = []
    for x in _steps(-2.1, 2.1, 12):
        zt = surface(x, Y_P) - UNDER
        secs.append([(x, Y_P - 0.1, zt - HEADER_H), (x, Y_P + 0.1, zt - HEADER_H),
                     (x, Y_P + 0.1, zt), (x, Y_P - 0.1, zt)])
    m.loft(secs)
    m.finish("header", wd, root, bevel=0.012)

    # ledger bolted to the tower, with iron straps over the rafter ends
    m = geo.Mesh()
    secs = []
    for x in _steps(X_L + 0.02, X_R - 0.1, 12):
        zt = surface(x, Y_W) - UNDER
        secs.append([(x, Y_W - 0.14, zt - 0.2), (x, Y_W - 0.01, zt - 0.2),
                     (x, Y_W - 0.01, zt), (x, Y_W - 0.14, zt)])
    m.loft(secs)
    m.finish("ledger", wd, root, bevel=0.01)
    ledger_top = lambda x: surface(x, Y_W) - UNDER  # noqa: E731
    for n, x in enumerate((-1.5, -0.35, 1.3)):
        kit.box(f"ledger_strap_{n}", (0.07, 0.02, 0.3), (x, Y_W - 0.145, ledger_top(x) - 0.1), mat=iron,
                bevel=0.004, parent=root)
        for dz in (-0.08, 0.1):
            kit.cylinder(f"ledger_bolt_{n}_{dz}", 0.022, 0.03, (x, Y_W - 0.155, ledger_top(x) - 0.1 + dz),
                         (90, 0, 0), iron, segments=8, parent=root)

    # battens: one under every course, so a lost shingle shows them
    m = geo.Mesh()
    k = 0
    while True:
        y = Y_F + 0.04 + k * EXPOSURE
        if y > Y_W - 0.1:
            break
        hw = 0.026
        secs = []
        for x in _steps(X_L + 0.01, X_R - 0.02, 14):
            zt = surface(x, y) + rng.uniform(-0.002, 0.002)
            secs.append([(x, y - hw, zt - BATTEN_T), (x, y + hw, zt - BATTEN_T),
                         (x, y + hw, zt), (x, y - hw, zt)])
        m.loft(secs)
        k += 1
    m.finish("battens", wd, root)

    # fascia along the eave: a tall silvered board, the drip edge and the eave line
    m = geo.Mesh()
    secs = []
    for x in _steps(X_L + 0.02, X_R, 16):
        zt = surface(x, Y_F) + 0.035
        drop = 0.21 + 0.015 * math.sin(x * 5.0)
        secs.append([(x, Y_F - 0.05, zt - drop), (x, Y_F - 0.005, zt - drop),
                     (x, Y_F - 0.005, zt), (x, Y_F - 0.05, zt)])
    m.loft(secs)
    m.finish("fascia", wo, root, bevel=0.006)

    # barge board along the right edge
    m = geo.Mesh()
    secs = []
    for y in _steps(Y_F, Y_W - 0.05, 10):
        zt = surface(X_R, y) + 0.035
        secs.append([(X_R - 0.005, y, zt - 0.2), (X_R + 0.045, y, zt - 0.2),
                     (X_R + 0.045, y, zt), (X_R - 0.005, y, zt)])
    m.loft(secs)
    m.finish("barge_board", wo, root, bevel=0.008)

    # board where the roof meets the tower
    m = geo.Mesh()
    secs = []
    for x in _steps(X_L + 0.02, X_R - 0.02, 12):
        z0 = surface(x, Y_W - 0.2) + 0.07
        z1 = surface(x, Y_W - 0.01) + 0.1
        secs.append([(x, Y_W - 0.24, z0), (x, Y_W - 0.01, z1), (x, Y_W - 0.01, z1 + 0.03),
                     (x, Y_W - 0.24, z0 + 0.03)])
    m.loft(secs)
    m.finish("flashing", wd, root, bevel=0.006)

    # board along the stair's flank, where the stair's run-off would otherwise get under the shingles
    m = geo.Mesh()
    secs = []
    for y in _steps(Y_F + 0.02, Y_W - 0.03, 12):
        z0 = surface(X_L + 0.2, y) + 0.07
        z1 = surface(X_L + 0.01, y) + 0.12
        secs.append([(X_L + 0.24, y, z0), (X_L + 0.24, y, z0 + 0.03), (X_L + 0.01, y, z1 + 0.03),
                     (X_L + 0.01, y, z1)])
    m.loft(secs)
    m.finish("stair_flashing", wd, root, bevel=0.006)


def shingles(kit, mats, rng, root):
    """Split shingles in staggered, overlapping courses. Returns the shingle count.

    Each point of the roof is covered by two or three layers, so a lost shingle shows the one
    beneath it. Each stretch of a course is brown oak or old grey wood, with its own tone, so the courses read as bands. The
    eave courses and the strip along the stair's flank are the darkest and mossiest wood, and
    one patch is old grey shingles.
    """
    groups = {}
    seg_tones = {}
    count = 0
    k = 0
    while True:
        base_y = Y_F + k * EXPOSURE
        if base_y > Y_W - 0.2:
            break
        x = X_L + (0.0 if k % 2 == 0 else rng.uniform(0.07, 0.14))
        while x < X_R - 0.03:
            w = rng.uniform(0.15, 0.25)
            gap = rng.uniform(0.004, 0.012)
            xl, xr = x, min(x + w, X_R)
            x += w + gap
            xc = (xl + xr) / 2
            y0 = base_y + rng.uniform(0.0, 0.03) + (rng.uniform(0.02, 0.07) if k == 0 else 0.0)
            length = SHINGLE_L + rng.uniform(-0.04, 0.04)
            roll = rng.random()
            lift = 0.045 + rng.uniform(-0.006, 0.008)
            if k >= DAMP_COURSES and roll > 0.985:
                continue                                    # lost: the layer beneath shows
            if roll > 0.95:
                y0 += rng.uniform(0.03, 0.08)               # broken butt
            elif roll > 0.91 and k > 0:
                y0 -= rng.uniform(0.03, 0.07)               # slid down
                lift += 0.012
            elif roll > 0.87:
                lift += rng.uniform(0.012, 0.025)           # curled up
            yt = min(y0 + length, Y_W - 0.03)
            if yt - y0 < 0.12:
                continue
            tb = rng.uniform(0.030, 0.040) if k == 0 else rng.uniform(0.024, 0.034)
            tt = rng.uniform(0.008, 0.012)
            bl = rng.uniform(-0.012, 0.012)                  # ragged butt: left and right corners differ
            br = rng.uniform(-0.012, 0.012)
            roll_z = rng.uniform(-0.012, 0.012)

            def corner(xx, yy, dy, dz):
                f = (yy - y0) / max(yt - y0, 1e-3)
                return xx, yy + dy, surface(xx, yy + dy) + lift * (1 - f) + dz

            bottom = [corner(xl, y0, bl, -roll_z), corner(xr, y0, br, roll_z),
                      corner(xr, yt, 0, roll_z), corner(xl, yt, 0, -roll_z)]
            top = [(px, py, pz + (tb if i < 2 else tt)) for i, (px, py, pz) in enumerate(bottom)]
            if xc < X_L + DAMP_WALL:
                tone = "wood_old"
            elif k < DAMP_COURSES:
                tone = "wood_old" if rng.random() < 0.3 else "wood_dark"
            elif _in_zone(PATCHES, xc, y0 + 0.3) and rng.random() < 0.85:
                tone = "wood_dark"                          # a patch of old, grey shingles among the brown ones
            elif rng.random() < 0.06:
                tone = "wood_dark"                          # an old shingle between new ones: its own object, its own tone
                groups[(k, 100 + count, tone)] = geo.Mesh()
                groups[(k, 100 + count, tone)].prism(bottom, top)
                count += 1
                continue
            else:
                seg_key = (k, int((xc - X_L) / SEGMENT))
                if seg_key not in seg_tones:
                    seg_tones[seg_key] = "door_wood" if rng.random() < 0.6 else "wood_dark"
                tone = seg_tones[seg_key]
            groups.setdefault((k, int((xc - X_L) / SEGMENT), tone), geo.Mesh()).prism(bottom, top)
            count += 1
        k += 1
    for (k, seg, tone), m in sorted(groups.items()):
        m.finish(f"shingles_{k}_{seg}_{tone}", mats[tone], root, bevel=0.004)
    return count


def stack_flashing(kit, mats, rng, root):
    """Iron apron where the stack comes through the roof: a front and two side pieces."""
    iron = mats["iron"]
    ang = math.degrees(math.atan(SLOPE))
    x0, x1 = STACK_X
    y0 = STACK_Y[0]
    pad = 0.13
    zc = surface((x0 + x1) / 2, y0 - 0.1) + 0.065
    kit.box("stack_apron_front", (x1 - x0 + 2 * pad, 0.28, 0.012), ((x0 + x1) / 2, y0 - 0.08, zc), (ang, 0, 0),
            iron, bevel=0.003, parent=root)
    for n, (sx, s) in enumerate(((x0 - pad / 2, -1), (x1 + pad / 2, 1))):
        zs = surface(sx, y0 + 0.4) + 0.065
        kit.box(f"stack_apron_side_{n}", (pad, 0.9, 0.012), (sx, y0 + 0.4, zs), (ang, 0, 0), iron, bevel=0.003,
                parent=root)

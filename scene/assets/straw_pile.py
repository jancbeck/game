"""Trampled wet straw: a flat, irregular patch of matted clumps pressed into the mud.

The patch is 1.0 to 1.7 m across with a lobed outline and a heap only 3 to 6 cm high at the
middle. A thin mud skirt (`mud`), 10 to 14 percent wider, lies under it. Straw (`straw`) comes as
14 to 20 clumps of 24 to 34 short ribbon strands. Each clump lies in its own direction, with its
strands parallel to within about 12 degrees and flat. A few short loose strands lie along the rim,
tangent to it, so nothing points out radially. The heap center is at the origin.
"""

import math

CLUMP_STRANDS = (24, 34)


def _ribbon(rng, hfun, x, y, yaw, length, nseg, width, z_off, end_lift, verts, faces):
    pts = []
    step = length / nseg
    for k in range(nseg + 1):
        pts.append((x, y, hfun(x, y) + z_off + rng.uniform(0, 0.002) + end_lift * (k / nseg) ** 2))
        yaw += rng.uniform(-0.1, 0.1)
        x += math.cos(yaw) * step
        y += math.sin(yaw) * step
    roll = rng.uniform(-0.2, 0.2)
    base = len(verts)
    for k, (px, py, pz) in enumerate(pts):
        a, b = pts[min(k + 1, nseg)], pts[max(k - 1, 0)]
        ang = math.atan2(a[1] - b[1], a[0] - b[0])
        wx, wy, wz = -math.sin(ang) * math.cos(roll), math.cos(ang) * math.cos(roll), math.sin(roll)
        w = width / 2 * (1 - 0.5 * k / nseg)
        verts.append((px + wx * w, py + wy * w, pz + wz * w))
        verts.append((px - wx * w, py - wy * w, pz - wz * w))
    for k in range(nseg):
        c = base + 2 * k
        faces.append((c, c + 1, c + 3, c + 2))
    return pts[-1][:2]


def build(kit, mats, rng):
    root = kit.group("straw_pile")
    R = rng.uniform(0.5, 0.68)
    stretch = rng.uniform(1.0, 1.35)
    yaw0 = rng.uniform(0, math.pi)
    c0, s0 = math.cos(yaw0), math.sin(yaw0)
    H = rng.uniform(0.03, 0.06)
    ph = [rng.uniform(0, 2 * math.pi) for _ in range(6)]

    def outline(theta):
        return R * (1 + 0.18 * math.sin(2 * theta + ph[0]) + 0.12 * math.sin(3 * theta + ph[1])
                    + 0.07 * math.sin(5 * theta + ph[2]))

    def norm_dist(x, y):
        """Distance from the center as a fraction of the outline radius there (1 = on the rim)."""
        u, v = (x * c0 + y * s0) / stretch, -x * s0 + y * c0
        return math.hypot(u, v) / outline(math.atan2(v, u))

    def to_world(rho, theta):
        r = rho * outline(theta)
        u, v = r * math.cos(theta) * stretch, r * math.sin(theta)
        return u * c0 - v * s0, u * s0 + v * c0

    def hfun(x, y):
        d = norm_dist(x, y)
        if d >= 1.0:
            return 0.0
        return H * (1 - d * d) + 0.005 * math.sin(11 * x + ph[3]) * math.sin(9 * y + ph[4]) * (1 - d)

    def blob(name, mat, rhos, segs, z_of, jitter):
        verts, faces, rows = [], [], []
        for rho in rhos:
            row = []
            for i in range(segs if rho else 1):
                t = 2 * math.pi * i / segs
                rr = rho * (1 + rng.uniform(-jitter, jitter) if rho >= 0.9 else rho)
                x, y = to_world(rr, t)
                row.append(len(verts))
                verts.append((x, y, z_of(x, y, rho)))
            rows.append(row)
        for i in range(segs):
            n = (i + 1) % segs
            faces.append((rows[0][0], rows[1][i], rows[1][n]))
            for k in range(1, len(rhos) - 1):
                faces.append((rows[k][i], rows[k + 1][i], rows[k + 1][n], rows[k][n]))
        return kit.mesh(name, verts, faces, mat=mat, parent=root)

    # mud skirt a little wider than the straw, then the flat heap on top of it
    blob("mud_skirt", mats["mud"], (0.0, 0.5, 0.9, 1.08, 1.14), 28, lambda x, y, rho: 0.003, 0.06)
    blob("heap", mats["straw"], (0.0, 0.35, 0.7, 0.92, 1.0), 28,
         lambda x, y, rho: hfun(x, y) + 0.004 if rho < 1.0 else 0.004, 0.05)

    sv, sf = [], []
    clumps = rng.randint(14, 20)
    for ci in range(clumps):
        for _ in range(20):
            cx, cy = to_world(rng.uniform(0, 0.85) ** 0.7, rng.uniform(0, 2 * math.pi))
            if norm_dist(cx, cy) < 0.85:
                break
        phi = rng.uniform(0, math.pi)
        cr = rng.uniform(0.14, 0.24)
        layer = 0.006 + ci * 0.0016
        for _ in range(rng.randint(*CLUMP_STRANDS)):
            along, across = rng.uniform(-1.4, 1.4) * cr, rng.uniform(-0.7, 0.7) * cr
            x = cx + math.cos(phi) * along - math.sin(phi) * across
            y = cy + math.sin(phi) * along + math.cos(phi) * across
            yaw = phi + rng.uniform(-0.2, 0.2) + rng.choice((0, math.pi))
            length = rng.uniform(0.14, 0.34)
            for _try in range(4):
                ex, ey = x + math.cos(yaw) * length, y + math.sin(yaw) * length
                if norm_dist(x, y) < 1.0 and norm_dist(ex, ey) < 1.02:
                    break
                length *= 0.7
            else:
                continue
            lift = rng.uniform(0.008, 0.02) if rng.random() < 0.06 else 0.0
            _ribbon(rng, hfun, x, y, yaw, length, 3, rng.uniform(0.026, 0.042), layer, lift, sv, sf)

    # loose strands along the rim, tangent to it
    for _ in range(30):
        t = rng.uniform(0, 2 * math.pi)
        x, y = to_world(rng.uniform(0.98, 1.2), t)
        tangent = math.atan2(math.cos(t), -stretch * math.sin(t)) + yaw0
        _ribbon(rng, hfun, x, y, tangent + rng.uniform(-0.5, 0.5) + rng.choice((0, math.pi)),
                rng.uniform(0.1, 0.22), 3, rng.uniform(0.018, 0.028), 0.006, 0.0, sv, sf)
    kit.mesh("strands", sv, sf, mat=mats["straw"], parent=root)
    return root

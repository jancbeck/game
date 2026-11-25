"""Wooden bucket: tapered stave body, three iron hoops, iron-wire bail.

0.34 m across the rim, 0.35 m tall, upright on Z = 0. `bail_deg` swings the
bail about its ear lugs (0 = arch standing up, 90 = folded flat to the side);
by default it droops a random amount. The body is one closed mesh with a
hollow interior, so the bucket can be tipped over and still read.
"""

import math

HEIGHT = 0.35
R_BASE = 0.135
R_RIM = 0.17
WALL = 0.018
FLOOR_Z = 0.03
STAVES = 16
HOOPS = (0.045, 0.165, 0.29)
EAR_Z = 0.30


def _r(z):
    return R_BASE + (R_RIM - R_BASE) * z / HEIGHT


def _body(kit, mat, parent, rng):
    n = STAVES * 2
    verts, faces = [], []

    def ring(z, radius, drop=False):
        out = []
        for j in range(n):
            a = 2 * math.pi * j / n
            r = radius * (0.975 if j % 2 == 0 else 1.0)
            dz = -rng.uniform(0.0, 0.012) if drop else 0.0
            out.append(len(verts))
            verts.append((r * math.cos(a), r * math.sin(a), z + dz))
        return out

    ob = ring(0.0, R_BASE)
    ot = ring(HEIGHT, R_RIM, drop=True)
    it = ring(HEIGHT - 0.004, R_RIM - WALL)
    ib = ring(FLOOR_Z, R_BASE - WALL)
    cb, ci = len(verts), len(verts) + 1
    verts += [(0, 0, 0), (0, 0, FLOOR_Z)]
    for j in range(n):
        k = (j + 1) % n
        faces.append((ob[j], ob[k], ot[k], ot[j]))
        faces.append((ot[j], ot[k], it[k], it[j]))
        faces.append((it[j], it[k], ib[k], ib[j]))
        faces.append((cb, ob[k], ob[j]))
        faces.append((ci, ib[j], ib[k]))
    return kit.mesh("staves", verts, faces, mat=mat, parent=parent)


def _hoop(kit, mat, parent, z, half_h):
    """Open iron band hugging the staves, with a thin lip top and bottom."""
    n = STAVES * 2
    r = _r(z) + 0.005
    verts, faces = [], []
    lo_out, hi_out, lo_in, hi_in = [], [], [], []
    for j in range(n):
        a = 2 * math.pi * j / n
        c, s = math.cos(a), math.sin(a)
        lo_out.append(len(verts)); verts.append((r * c, r * s, z - half_h))
        hi_out.append(len(verts)); verts.append((r * c, r * s, z + half_h))
        lo_in.append(len(verts)); verts.append(((r - 0.007) * c, (r - 0.007) * s, z - half_h))
        hi_in.append(len(verts)); verts.append(((r - 0.007) * c, (r - 0.007) * s, z + half_h))
    for j in range(n):
        k = (j + 1) % n
        faces.append((lo_out[j], lo_out[k], hi_out[k], hi_out[j]))
        faces.append((hi_out[j], hi_out[k], hi_in[k], hi_in[j]))
        faces.append((lo_in[j], lo_in[k], lo_out[k], lo_out[j]))
    return kit.mesh(f"hoop_{z:.2f}", verts, faces, mat=mat, parent=parent)


def build(kit, mats, rng, bail_deg=None):
    j = lambda a: kit.jitter(rng, a)  # noqa: E731
    root = kit.group("bucket")
    iron = mats["iron"]
    _body(kit, mats["wood_old"], root, rng)

    for n, z in enumerate(HOOPS):
        _hoop(kit, iron, root, z + j(0.004), 0.012 if n else 0.014)

    # ear lugs on opposite sides of the rim
    for sx in (-1, 1):
        kit.box(f"ear_{sx}", (0.016, 0.03, 0.03), (sx * (_r(EAR_Z) + 0.012), 0, EAR_Z), mat=iron,
                bevel=0.004, parent=root)

    # bail: a flattened half-ellipse of square wire, hinged on the ears
    swing = rng.uniform(20, 75) if bail_deg is None else bail_deg
    pivot = kit.group("bail", (0, 0, EAR_Z), parent=root)
    pivot.rotation_euler = (math.radians(swing), 0, 0)
    rx, rz = _r(EAR_Z) + 0.012, 0.17
    steps = 10
    pts = [(rx * math.cos(math.pi * i / steps), 0, rz * math.sin(math.pi * i / steps))
           for i in range(steps + 1)]
    for i in range(steps):
        kit.beam(f"bail_{i}", pts[i], pts[i + 1], (0.008, 0.008), iron, parent=pivot)
    return root

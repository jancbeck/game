"""Hanging banner: soaked red cloth on an iron rod, ringed tabs, ragged hem with loose threads, drips.

Wall-mounted. The origin is the center of the wall plate (the wall is the XZ plane at
y = 0); +Y points into the wall, the rod stands 7 cm out from it and the cloth hangs in
front of the rod down to about z = -2.4.

The cloth is one subdivided sheet gathered at six tabs that loop over the rod, so the top edge
sags in scallops between the rings. Soaked cloth is heavy and hangs plumb: the folds start at
the rings, merge into broad vertical pleats lower down, and the cloth clings to the wall, so the
hem lies almost flat against the stone and the fold valleys are pressed against it. The lower
edge is a swallowtail cut into ragged teeth, with torn gashes, dangling strips and loose threads,
and a few water beads hang from the lowest points. The crown and chevron are separate thicker
patches that follow the folds.
"""

import math

import bmesh

LIGHTS = []

WIDTH, HEIGHT = 0.9, 2.4
NX, NZ = 72, 120
NOTCH = 0.34                 # depth of the swallowtail cut at x = 0
ROD_Y = -0.07                # rod axis, in front of the wall
ROD_R = 0.022
TAB_R = 0.032                # tab and ring radius around the rod
CLOTH_Y = ROD_Y - 0.030      # cloth plane at the rod
CLOTH_T = 0.008
WALL_Y = -0.024              # fold valleys press against the wall but stop short of it
CLING = 0.62                 # how far the hem has pulled in toward the wall, as a share of CLOTH_Y
RING_DX = 0.144
RINGS = [(i - 2.5) * RING_DX for i in range(6)]
TOP = -0.035                 # top edge of the cloth below the rod, before the scallop sag

# painted shapes as (points in x/z meters, convex faces by point index)
CROWN = ([(-0.21, -0.10), (0.21, -0.10), (0.115, -0.01), (-0.115, -0.01),
          (0.23, 0.20), (0.0, 0.29), (-0.23, 0.20)],
         [(0, 1, 2, 3), (1, 4, 2), (2, 5, 3), (3, 6, 0)])
CHEVRON = ([(-0.19, -0.16), (0.0, -0.31), (0.19, -0.16), (0.19, -0.24), (0.0, -0.39),
            (-0.19, -0.24)],
           [(0, 1, 4, 5), (1, 2, 3, 4)])


def _smooth(ob):
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def _step(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def _cloth_shape(rng):
    """Returns pos(x, z) -> (x, y, z) for a point on the flat cloth."""
    ph = [rng.uniform(0, 2 * math.pi) for _ in range(6)]
    k0 = 2 * math.pi / RING_DX
    k1, k2, k3 = 2 * math.pi / 0.27, 2 * math.pi / 0.43, 2 * math.pi / 0.17

    def pos(x, z):
        d = max(-z, 0.0)
        s = min(d / HEIGHT, 1.0)
        # heavy and wet: the cloth hangs plumb, only the hem drifts a little
        xs = x + 0.010 * s ** 1.5 * math.sin(ph[3])
        # pleats: fine ones from the rings, then broad ones that merge lower down and slant slowly
        drift = 0.10 * s
        w_ring = math.exp(-d / 0.32)
        w_mid = _step(0.04, 0.55, d) * (1.0 - 0.35 * _step(1.2, 2.2, d))
        w_low = _step(0.35, 1.3, d)
        f = (w_ring * 0.9 * math.cos(k0 * (xs - RINGS[0]) + math.pi)
             + w_mid * (math.cos(k1 * xs + ph[0] + drift) + 0.45 * math.cos(k3 * xs + ph[1] - 1.5 * drift))
             + w_low * 0.9 * (math.cos(k2 * xs + ph[2] - drift) + 0.4 * math.cos(2.1 * k2 * xs + ph[4])))
        fold = 0.031 * f
        # crests are rounded, valleys are tighter
        fold -= 0.010 * f * abs(f) * (w_mid + w_low)
        # gathered at the rings: belly out between them, pinned at the tabs
        gather = -0.016 * (1 - math.cos(k0 * (xs - RINGS[0]))) * math.exp(-d / 0.30)
        # clinging: the lower cloth is drawn toward the wall by its own wet weight
        base = CLOTH_Y * (1.0 - CLING * s ** 1.15)
        y = base + fold + gather
        # valleys flatten against the wall instead of passing through it
        over = WALL_Y - y
        y = WALL_Y - 0.010 * math.log1p(math.exp(over / 0.010)) if over < 0.2 else y
        return xs, y, z

    return pos


def _hem(rng):
    """Bottom edge z(x): swallowtail, frayed teeth, torn gashes, dangling strips."""
    cols = NX + 1
    # fraying: most teeth are short, a few reach far
    teeth = [rng.uniform(0.0, 1.0) ** 2.2 * 0.075 for _ in range(cols)]
    # uneven sag: the wet hem hangs lower where the weave has stretched
    p1, p2, p3 = (rng.uniform(0, 2 * math.pi) for _ in range(3))
    for _ in range(3):
        c = rng.randrange(6, cols - 6)
        depth = rng.uniform(0.12, 0.28)
        for k in range(-3, 4):
            teeth[c + k] += depth * (1 - abs(k) / 3.5) ** 1.2
    # strips that have torn loose and hang lower
    strips = []
    for _ in range(3):
        c = rng.randrange(4, cols - 8)
        strips.append((c, c + rng.randint(2, 4), rng.uniform(0.05, 0.13)))
    side = rng.choice((-1, 1))

    def z_bottom(i):
        x = -WIDTH / 2 + WIDTH * i / NX
        z = -HEIGHT + NOTCH * (1 - abs(x) / (WIDTH / 2)) ** 1.15
        z += teeth[i]
        z -= 0.018 * (1 + math.sin(11.0 * x + p1)) * (0.5 + 0.5 * math.sin(4.0 * x + p2))
        z += 0.012 * math.sin(33.0 * x + p3)
        for a, b, drop in strips:
            if a <= i <= b:
                z -= drop * (1 - 0.35 * abs(i - (a + b) / 2) / max((b - a) / 2, 1))
        if side * x > 0.32:
            z -= 0.07
        return z

    return z_bottom


def _top(x):
    """Top edge: sags in scallops between the rings."""
    return TOP - 0.03 * math.sin(math.pi * (x - RINGS[0]) / RING_DX) ** 2


def _cloth(kit, mats, rng, root, pos, z_bottom):
    verts, faces = [], []
    for j in range(NZ + 1):
        v = j / NZ
        for i in range(NX + 1):
            x = -WIDTH / 2 + WIDTH * i / NX
            z0, z1 = _top(x), z_bottom(i)
            verts.append(pos(x, z0 + (z1 - z0) * v))
    for j in range(NZ):
        for i in range(NX):
            a = j * (NX + 1) + i
            faces.append((a, a + 1, a + NX + 2, a + NX + 1))
    ob = kit.mesh("cloth", verts, faces, mat=mats["cloth_red"], parent=root)
    kit.solidify(ob, CLOTH_T).modifiers[-1].offset = 0.0
    return _smooth(ob)


def _threads(kit, mats, rng, root, pos, z_bottom):
    """Loose threads and ravelled strips hanging from the hem, as one mesh of thin ribbons."""
    verts, faces = [], []
    for _ in range(70):
        i = rng.randrange(1, NX)
        x = -WIDTH / 2 + WIDTH * (i + rng.uniform(-0.4, 0.4)) / NX
        z0 = z_bottom(i) + 0.012
        length = rng.uniform(0.035, 0.17) * (1.0 if rng.random() < 0.8 else 1.8)
        w = rng.uniform(0.003, 0.008)
        curl = rng.uniform(-0.035, 0.035)
        out = rng.uniform(-0.01, 0.025)
        n = 5
        base = len(verts)
        for k in range(n + 1):
            t = k / n
            xk, yk, zk = pos(x + curl * t * t, z0 - length * t)
            yk = min(yk - out * t * t, WALL_Y)
            ww = w * (1.0 - 0.55 * t)
            verts.append((xk - ww, yk, zk))
            verts.append((xk + ww, yk, zk))
            if k:
                a = base + 2 * (k - 1)
                faces.append((a, a + 1, a + 3, a + 2))
    return kit.mesh("threads", verts, faces, mat=mats["cloth_red"], parent=root)


def _beads(kit, mats, rng, root, pos, z_bottom):
    """Water beads clinging to the lowest teeth of the hem, and two drops in the air under them."""
    iron = mats["iron"]
    cand = sorted(range(2, NX - 1), key=z_bottom)[:60]
    picked = []
    for i in cand:
        if all(abs(i - j) > 5 for j in picked):
            picked.append(i)
        if len(picked) == 6:
            break
    for n, i in enumerate(picked):
        x = -WIDTH / 2 + WIDTH * i / NX
        xb, yb, zb = pos(x, z_bottom(i) - 0.004)
        r = rng.uniform(0.0035, 0.0055)
        kit.sphere(f"drip_{n}", r, (xb, yb, zb - r * 1.2), scale=(1.0, 1.0, 1.5), mat=iron, segments=8,
                   parent=root)
        if n < 2:
            kit.sphere(f"drop_{n}", 0.0028, (xb, yb, zb - rng.uniform(0.12, 0.22)), scale=(1.0, 1.0, 1.9),
                       mat=iron, segments=6, parent=root)


def _decal(kit, name, shape, origin, scale, pos, mat, parent):
    """Painted patch: a thicker piece of the cloth surface, raised in front of it."""
    points, polys = shape
    bm = bmesh.new()
    vs = [bm.verts.new((origin[0] + x * scale, 0.0, origin[1] + z * scale)) for x, z in points]
    for poly in polys:
        bm.faces.new([vs[i] for i in poly])
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=14, use_grid_fill=True)
    verts = []
    for v in bm.verts:
        x, y, z = pos(v.co.x, v.co.z)
        verts.append((x, y - CLOTH_T / 2 - 0.0045, z))
    faces = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    ob = kit.mesh(name, verts, faces, mat=mat, parent=parent)
    kit.solidify(ob, 0.007).modifiers[-1].offset = 0.0
    return _smooth(ob)


def _tab(kit, mats, rng, root, x, pos):
    """Cloth strip sewn on the front of the cloth, over the rod and down the back."""
    pts = []
    xc, yc, zc = pos(x, -0.16)
    pts.append((yc - CLOTH_T - 0.002, zc))
    pts.append((yc - CLOTH_T - 0.002, -0.07))
    for a in (-35, 0, 35, 70, 90, 110, 145, 180, 215):
        r = math.radians(a)
        pts.append((ROD_Y - TAB_R * math.cos(r), TAB_R * math.sin(r)))
    pts.append((ROD_Y + TAB_R, -0.085))
    hw = 0.026
    verts, faces = [], []
    for k, (y, z) in enumerate(pts):
        verts.append((x - hw, y, z))
        verts.append((x + hw, y, z))
        if k:
            a = 2 * (k - 1)
            faces.append((a, a + 1, a + 3, a + 2))
    ob = kit.mesh("tab", verts, faces, mat=mats["cloth_red"], parent=root)
    kit.solidify(ob, 0.006).modifiers[-1].offset = 0.0
    return _smooth(ob)


def build(kit, mats, rng):
    root = kit.group("banner")
    iron = mats["iron"]
    pos = _cloth_shape(rng)
    z_bottom = _hem(rng)

    _cloth(kit, mats, rng, root, pos, z_bottom)
    _threads(kit, mats, rng, root, pos, z_bottom)
    _beads(kit, mats, rng, root, pos, z_bottom)
    for x in RINGS:
        _tab(kit, mats, rng, root, x, pos)
        kit.torus("ring", TAB_R + 0.013, 0.0055, (x, ROD_Y, -0.004), rot_deg=(0, 90, rng.uniform(-8, 8)),
                  mat=iron, major_segments=20, minor_segments=5, parent=root)

    # emblem: crown over a chevron, raised patches
    _decal(kit, "crown", CROWN, (0.0, -0.85), 1.25, pos, mats["cloth_emblem"], root)
    _decal(kit, "chevron", CHEVRON, (0.0, -0.85), 1.25, pos, mats["cloth_emblem"], root)

    # rod with collars, ball finials and spikes
    kit.cylinder("rod", ROD_R, 1.14, (0, ROD_Y, 0), rot_deg=(0, 90, 0), mat=iron, segments=12, parent=root)
    for side, name in ((1, "r"), (-1, "l")):
        kit.cylinder(f"collar_{name}", 0.032, 0.025, (side * 0.545, ROD_Y, 0), rot_deg=(0, 90, 0),
                     mat=iron, segments=12, parent=root)
        kit.sphere(f"finial_{name}", 0.038, (side * 0.585, ROD_Y, 0), mat=iron, segments=10, parent=root)
        kit.cylinder(f"spike_{name}", 0.022, 0.09, (side * 0.665, ROD_Y, 0), rot_deg=(0, side * 90, 0),
                     mat=iron, segments=8, radius_top=0.0, parent=root)

    # wall mounts: a plate and an arm at the center and near each end
    for x, name in ((0.0, "c"), (0.5, "r"), (-0.5, "l")):
        kit.box(f"plate_{name}", (0.12, 0.02, 0.12), (x, -0.01, 0), mat=iron, bevel=0.004, parent=root)
        kit.beam(f"arm_{name}", (x, -0.02, 0), (x, ROD_Y, 0), section=(0.035, 0.035), mat=iron,
                 bevel=0.004, parent=root)
        for sx in (-1, 1):
            for sz in (-1, 1):
                kit.cylinder(f"bolt_{name}", 0.008, 0.008, (x + sx * 0.04, -0.022, sz * 0.04),
                             rot_deg=(90, 0, 0), mat=iron, segments=6, parent=root)
    return root

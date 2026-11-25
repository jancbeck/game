"""Cooper's barrel: 22 separate staves with a bulge and visible seams, six iron hoops.

0.61 m wide at the belly, 0.9 m tall, upright on Z = 0. Each build picks one of two states:
a lid of nailed planks with a board leaning on the side, or an open top with rainwater
and a ladle resting on the rim. The water uses a private glossy material (`rainwater`),
because the shared library has no still-water material.
"""

import math

import bpy

HEIGHT = 0.9
R_END = 0.262
R_BELLY = 0.305
STAVES = 22
LEVELS = 12
THICK = 0.024            # stave thickness
CROZE = 0.045            # the lid sits this far below the rim
GAP = 0.94               # stave width as a fraction of its slot, the rest is a dark seam
# (height of hoop center, hoop width)
HOOPS = ((0.045, 0.034), (0.145, 0.040), (0.355, 0.042), (0.545, 0.042), (0.755, 0.040),
         (0.858, 0.034))


def _radius(z):
    t = 2 * z / HEIGHT - 1
    return R_END + (R_BELLY - R_END) * (1 - t * t)


def _smooth(ob):
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def _stave(kit, mats, rng, i, parent):
    """One curved board: outer face, inner face, edges and both end caps."""
    ac = 2 * math.pi * i / STAVES
    ha = math.pi / STAVES * GAP
    top = HEIGHT + kit.jitter(rng, 0.006)
    bot = kit.jitter(rng, 0.003) if i % 3 else 0.0
    verts, faces = [], []
    for k in range(LEVELS):
        z = bot + (top - bot) * k / (LEVELS - 1)
        r = _radius(min(max(z, 0.0), HEIGHT))
        ring = []
        for rr in (r, r - THICK):
            pts = []
            for u in (-1.0, 0.0, 1.0):
                a = ac + ha * u
                pts.append((rr * math.cos(a), rr * math.sin(a), z))
            ring.append(pts)
        loop = ring[0] + ring[1][::-1]
        verts += loop
    n = 6
    for k in range(LEVELS - 1):
        for j in range(n):
            a, b = k * n + j, k * n + (j + 1) % n
            faces.append((a, b, b + n, a + n))
    faces.append(tuple(range(n - 1, -1, -1)))
    faces.append(tuple((LEVELS - 1) * n + j for j in range(n)))
    return kit.mesh(f"stave_{i}", verts, faces, mat=mats["wood_old"], parent=parent, bevel=0.0025)


def _liner(kit, mats, parent):
    """Dark surface of revolution behind the staves: shows through the seams."""
    n = 28
    verts, faces = [], []
    zs = [HEIGHT * k / 10 for k in range(11)]
    for z in zs:
        r = _radius(z) - THICK + 0.001
        verts += [(r * math.cos(2 * math.pi * j / n), r * math.sin(2 * math.pi * j / n), z)
                  for j in range(n)]
    for k in range(10):
        for j in range(n):
            a, b = k * n + j, k * n + (j + 1) % n
            faces.append((a, b, b + n, a + n))
    faces.append(tuple(range(n - 1, -1, -1)))
    return kit.mesh("liner", verts, faces, mat=mats["wood_dark"], parent=parent)


def _hoop(kit, mats, rng, n, z, width, parent):
    """Flat iron band that follows the barrel profile, a little crooked and a little proud."""
    seg = 48
    hw = width / 2
    t_in, t_out = 0.0015, 0.0085
    verts, faces = [], []
    for j in range(seg):
        a = 2 * math.pi * j / seg
        c, s = math.cos(a), math.sin(a)
        for dz, rr in ((-hw, t_in), (hw, t_in), (hw, t_out), (-hw, t_out)):
            r = _radius(min(max(z + dz, 0.0), HEIGHT)) + rr
            verts.append((r * c, r * s, z + dz))
    for j in range(seg):
        a, b = j * 4, ((j + 1) % seg) * 4
        for q in range(4):
            q2 = (q + 1) % 4
            faces.append((a + q, b + q, b + q2, a + q2))
    tilt = (kit.jitter(rng, 1.2), kit.jitter(rng, 1.2), 0)
    ob = kit.mesh(f"hoop_{n}", verts, faces, mat=mats["iron"], parent=parent, rot_deg=tilt,
                  loc=(0, 0, kit.jitter(rng, 0.004)))
    # a rivet pair where the band overlaps itself
    ang = rng.uniform(0, 2 * math.pi)
    for dz in (-hw * 0.45, hw * 0.45):
        r = _radius(z + dz) + t_out
        kit.sphere(f"rivet_{n}", 0.0065, (r * math.cos(ang), r * math.sin(ang), z + dz),
                   scale=(1, 1, 0.5), rot_deg=(0, 0, math.degrees(ang)), mat=mats["iron"],
                   segments=6, parent=ob)
    return ob


def _prism(poly, z0, z1):
    n = len(poly)
    verts = [(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))
    return verts, faces


def _lid(kit, mats, rng, parent):
    r_lid = _radius(HEIGHT - CROZE) - THICK - 0.002
    z1 = HEIGHT - CROZE
    z0 = z1 - 0.026
    edges = [-r_lid, -0.13 + kit.jitter(rng, 0.03), -0.015 + kit.jitter(rng, 0.02),
             0.115 + kit.jitter(rng, 0.03), r_lid]
    for n in range(4):
        y0, y1 = edges[n] + 0.0015, edges[n + 1] - 0.0015
        y0, y1 = max(y0, -r_lid * 0.995), min(y1, r_lid * 0.995)
        ys = [y0 + (y1 - y0) * k / 4 for k in range(5)]
        xs = lambda y: math.sqrt(max(r_lid ** 2 - y * y, 1e-6))
        poly = [(-xs(y0), y0), (xs(y0), y0)]
        poly += [(xs(y), y) for y in ys[1:-1]]
        poly += [(xs(y1), y1), (-xs(y1), y1)]
        poly += [(-xs(y), y) for y in ys[-2:0:-1]]
        lift = kit.jitter(rng, 0.002)
        verts, faces = _prism(poly, z0, z1 + lift)
        kit.mesh(f"lid_{n}", verts, faces, mat=mats["wood_old"], parent=parent, bevel=0.003)
        # nail heads where two cross battens would be
        for sx in (-0.7, 0.7):
            x = sx * xs(0.5 * (y0 + y1)) * 0.82
            kit.cylinder(f"nail_{n}", 0.006, 0.004, (x, 0.5 * (y0 + y1), z1 + lift + 0.001),
                         mat=mats["iron"], segments=6, parent=parent)
    # one cross batten, nailed on top
    kit.box("lid_strip", (0.07, 0.36, 0.014), (0.0, 0.0, z1 + 0.013), rot_deg=(0, 0, 90 + kit.jitter(rng, 8)),
            mat=mats["wood_dark"], bevel=0.003, parent=parent)


def _water(kit, mats, parent):
    mat = bpy.data.materials.get("rainwater")
    if mat is None:
        mat = bpy.data.materials.new("rainwater")
        mat.use_nodes = True
        b = mat.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.03, 0.04, 0.05, 1.0)
        b.inputs["Roughness"].default_value = 0.02
        b.inputs["Specular IOR Level"].default_value = 1.0
        b.inputs["Metallic"].default_value = 0.0
    z = HEIGHT - 0.11
    r = _radius(z) - THICK - 0.002
    n = 40
    verts = [(0, 0, z)] + [(r * math.cos(2 * math.pi * j / n), r * math.sin(2 * math.pi * j / n), z)
                           for j in range(n)]
    faces = [(0, 1 + (j + 1) % n, 1 + j) for j in range(n)]
    return kit.mesh("rainwater", verts, faces, mat=mat, parent=parent)


def _ladle(kit, mats, rng, parent):
    """Stick with a wooden bowl, resting across the rim; the bowl dips into the water."""
    y = kit.jitter(rng, 0.03)
    a = (-0.10, y, HEIGHT - 0.135)
    rim_x = math.sqrt(max(_radius(HEIGHT) ** 2 - y * y, 0))
    c = (rim_x + 0.008, y, HEIGHT + 0.012)
    slope = (c[2] - a[2]) / (c[0] - a[0])
    b = (c[0] + 0.13, y, c[2] + slope * 0.13)
    kit.beam("ladle_handle", a, b, section=(0.03, 0.02), mat=mats["wood_dark"], bevel=0.004,
             parent=parent)
    kit.sphere("ladle_bowl", 0.065, (a[0] - 0.01, y, a[2]), scale=(1, 1, 0.55), mat=mats["wood_dark"],
               segments=10, parent=parent)


def _plank_lean(kit, mats, rng, parent):
    """A weathered board stood against the barrel, resting on the hoop below the rim."""
    theta = math.radians(rng.uniform(-70, 70) - 90)      # around the barrel, camera side
    z_hoop = HOOPS[4][0]
    r_top = _radius(z_hoop) + 0.0085 + 0.012
    lean = 0.19
    foot = r_top + lean
    base = (foot * math.cos(theta), foot * math.sin(theta))
    top = (r_top * math.cos(theta), r_top * math.sin(theta))
    tilt = math.atan2(lean, z_hoop)
    g = kit.group("plank_lean", loc=(base[0], base[1], 0.0), parent=parent)
    g.rotation_euler = (tilt, 0, math.atan2(top[0] - base[0], -(top[1] - base[1])))
    kit.box("plank", (0.15, 0.022, 0.85), (0, 0, 0.425), mat=mats["wood_old"], bevel=0.003, parent=g)
    for z in (0.12, 0.66):
        kit.cylinder("plank_nail", 0.005, 0.004, (0.0, 0.012, z), rot_deg=(90, 0, 0), mat=mats["iron"],
                     segments=6, parent=g)


def build(kit, mats, rng):
    root = kit.group("barrel")
    openbarrel = rng.random() < 0.5
    for i in range(STAVES):
        _stave(kit, mats, rng, i, root)
    _liner(kit, mats, root)
    # floor, so the seams at the bottom do not show the ground
    kit.cylinder("bottom", R_END - THICK, 0.03, (0, 0, 0.02), mat=mats["wood_dark"], segments=22,
                 parent=root)
    for n, (z, w) in enumerate(HOOPS):
        _hoop(kit, mats, rng, n, z, w, root)
    if openbarrel:
        _water(kit, mats, root)
        _ladle(kit, mats, rng, root)
    else:
        _lid(kit, mats, rng, root)
        if rng.random() < 0.75:
            _plank_lean(kit, mats, rng, root)
    return root

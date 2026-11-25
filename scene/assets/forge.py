"""Smithy corner under a timber penthouse roof: stone hearth with a hood and chimney, bellows, anvil,
quench tub, tool rack.

Footprint 4.3 m wide (X, from -2.05 to 2.25) and 2.9 m deep (Y, from -1.6 to 1.3), resting on Z = 0.
The front faces -Y. The hearth is at the back, in the middle: a 0.86 m stone table with cheek
walls, a back wall and a corbelled hood that narrows into a chimney stack 3.7 m tall, so the top
clears the roof by about 1.3 m. The fire is banked for the night: a mound of grey ash with a few
coals glowing dull red through it, no flame. Left of the hearth a leather bellows on a trestle
blows through an iron tuyere, and a sack of charcoal leans in front of it. Right of the hearth, in
front, an anvil stands on an oak stump with the hammer laid on it, and a quench tub stands next to
it. A tool rack with a shelf of horseshoes is behind the anvil. A fire rake leans on the hearth.

The roof is a mono-pitch penthouse on four oak posts on stone pads: 2.85 m at the front eave,
2.25 m at the back eave, lapped boards across six rafters. The boards are cut round the stack with
an iron collar. Years of patching show: replaced boards in a darker wood, a short board, and a
tarred burlap patch held down with stones next to the stack.

Wind blows toward +X, slightly +Y: the thin smoke bends over after it leaves the stack. Only the
glowing coals emit light, and one weak, short-reach point light sits just above them.
"""

import math

import bpy

from . import _fire, _lights
from . import _se_mesh as sm

# the banked fire's glow goes through _lights.add in build(): low specular, short reach
LIGHTS = []

HEARTH_Y = 0.30
TABLE_Z = 0.86
WIND = (0.24, 0.05)
SPARK_WIND = (0.9, 0.2)
STACK_TOP = 3.70
SMOKE = dict(base=(0.0, 0.575, STACK_TOP + 0.12), rise=1.2, drift=0.8, r0=0.08, r1=0.32, density=0.45)

# penthouse roof: board top surface at the front and back eaves
ROOF_Y0, ROOF_Y1 = -1.60, 1.30
ROOF_Z0, ROOF_Z1 = 2.85, 2.25
ROOF_X0, ROOF_X1 = -2.05, 2.25
POST_X = (-1.92, 2.12)
POST_Y = (-1.38, 1.08)
RAFTER_X = (-1.92, -1.12, -0.40, 0.40, 1.28, 2.12)
STACK_HOLE = ((-0.32, 0.32), (0.36, 0.82))   # x range, y range of the opening round the stack
SLOPE = (ROOF_Z0 - ROOF_Z1) / (ROOF_Y1 - ROOF_Y0)
ALPHA = math.atan(SLOPE)


def _water_material():
    mat = bpy.data.materials.get("forge_water")
    if mat is None:
        mat = bpy.data.materials.new("forge_water")
        mat.use_nodes = True
        b = mat.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.02, 0.025, 0.03, 1.0)
        b.inputs["Roughness"].default_value = 0.03
        b.inputs["Specular IOR Level"].default_value = 1.0
    return mat


def _ash_material():
    mat = bpy.data.materials.get("forge_ash")
    if mat is None:
        mat = bpy.data.materials.new("forge_ash")
        mat.use_nodes = True
        b = mat.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.105, 0.098, 0.092, 1.0)
        b.inputs["Roughness"].default_value = 0.95
    return mat


def _roof_z(y):
    """Top of the roof boards at prop-space y."""
    return ROOF_Z0 - SLOPE * (y - ROOF_Y0)


def _roof(kit, mats, rng, root):
    """Penthouse on four posts: plates, rafters trimmed round the stack, lapped boards, patches."""
    wd, wo, iron = mats["wood_dark"], mats["wood_old"], mats["iron"]
    board_t = 0.025
    raf_h = 0.12
    cos_a = math.cos(ALPHA)

    def rafter_bottom(y):
        return _roof_z(y) - (board_t + raf_h) / cos_a

    # stone pads and posts; the plates run along X under the rafters
    for j, y in enumerate(POST_Y):
        top = rafter_bottom(y)
        kit.box(f"plate_{j}", (ROOF_X1 - ROOF_X0 - 0.1, 0.15, 0.17), (0.5 * (ROOF_X0 + ROOF_X1), y, top - 0.085),
                mat=wd, bevel=0.01, parent=root)
        for i, x in enumerate(POST_X):
            s = rng.uniform(0.34, 0.42)
            kit.box(f"post_pad_{i}_{j}", (s, s, 0.14), (x, y, 0.04), (0, 0, rng.uniform(-15, 15)),
                    mats["stone_wall"], bevel=0.025, parent=root)
            kit.beam(f"post_{i}_{j}", (x, y, 0.1), (x + rng.uniform(-0.015, 0.015), y + rng.uniform(-0.015, 0.015),
                                                     top - 0.16), (0.15, 0.15), wd, bevel=0.012, parent=root)
            d = 1 if i == 0 else -1
            z1 = top - 0.17
            kit.beam(f"post_brace_{i}_{j}", (x, y, z1 - 0.5), (x + d * 0.5, y, z1), (0.08, 0.09), wo, bevel=0.008,
                     parent=root)
    # rafters from the back plate to past the front plate; the two by the stack carry trimmers
    for i, x in enumerate(RAFTER_X):
        y0, y1 = ROOF_Y0 + 0.03, ROOF_Y1 - 0.03
        zc = lambda y: _roof_z(y) - (board_t + raf_h / 2) / cos_a
        kit.beam(f"rafter_{i}", (x, y0, zc(y0)), (x, y1, zc(y1)), (0.075, raf_h), wo, bevel=0.006, parent=root)
    for k, y in enumerate((STACK_HOLE[1][0] - 0.04, STACK_HOLE[1][1] + 0.04)):
        kit.box(f"trimmer_{k}", (0.80, 0.07, 0.11), (0, y, _roof_z(y) - (board_t + 0.06) / cos_a),
                (math.degrees(-ALPHA), 0, 0), wo, parent=root)

    # lapped boards across the slope, each course overlapping the one below it
    F = sm.frame((0, ROOF_Y0, ROOF_Z0), (1, 0, 0), (0, cos_a, -SLOPE * cos_a), (0, SLOPE * cos_a, cos_a))
    slope_len = (ROOF_Y1 - ROOF_Y0) / cos_a
    width, exposure = 0.26, 0.21
    courses = int(math.ceil(slope_len / exposure))
    parts = {"wood_old": sm.Mesh(), "wood_dark": sm.Mesh()}
    for c in range(courses):
        v = min(c * exposure, slope_len - width / 2)
        y = ROOF_Y0 + v * cos_a
        n = -board_t / 2 - 0.006 * (c % 2) + rng.uniform(-0.002, 0.002)
        in_hole = STACK_HOLE[1][0] - 0.1 < y < STACK_HOLE[1][1] + 0.05
        spans = ([(ROOF_X0, STACK_HOLE[0][0]), (STACK_HOLE[0][1], ROOF_X1)] if in_hole
                 else [(ROOF_X0, ROOF_X1)])
        for a, b in spans:
            # long courses are two boards butted at a rafter
            cuts = [a, b] if b - a < 2.6 else [a, RAFTER_X[3] if c % 2 else RAFTER_X[2], b]
            for k in range(len(cuts) - 1):
                x0, x1 = cuts[k] + 0.004, cuts[k + 1] - 0.004
                if c == 7 and k == 0 and not in_hole:
                    x1 -= 0.55                                   # a short board, the gap left open
                key = "wood_dark" if rng.random() < 0.2 else "wood_old"
                parts[key].box((x1 - x0, width, board_t), (0.5 * (x0 + x1), v + width / 2, n),
                               (rng.uniform(-1.5, 1.5), 0, rng.uniform(-0.6, 0.6)), F)
    for key, m in parts.items():
        m.finish(f"roof_boards_{key}", mats[key], root)
    kit.box("fascia", (ROOF_X1 - ROOF_X0 + 0.04, 0.03, 0.15), (0.5 * (ROOF_X0 + ROOF_X1), ROOF_Y0 - 0.01,
                                                                ROOF_Z0 - 0.09), mat=wo, bevel=0.005, parent=root)

    # iron collar round the stack where it passes through the boards
    hy = HEARTH_Y + 0.285
    zc = _roof_z(hy) + 0.02
    for k, (sx, sy, cx, cy) in enumerate(((0.62, 0.03, 0, hy - 0.2), (0.62, 0.03, 0, hy + 0.2),
                                          (0.03, 0.43, -0.3, hy), (0.03, 0.43, 0.3, hy))):
        kit.box(f"collar_{k}", (sx, sy, 0.12), (cx, cy, zc), (math.degrees(-ALPHA) if sx > 0.1 else 0, 0, 0), iron,
                parent=root)
    # tarred burlap patch beside the stack, held by stones
    Fp = sm.frame((0, ROOF_Y0, ROOF_Z0), (1, 0, 0), (0, cos_a, -SLOPE * cos_a), (0, SLOPE * cos_a, cos_a))
    vp = (hy - ROOF_Y0) / cos_a
    patch = sm.Mesh()
    patch.box((0.7, 0.6, 0.012), (-0.75, vp - 0.1, 0.012), (0, 0, 7), Fp)
    patch.finish("roof_patch", mats["burlap"], root)
    stones = sm.Mesh()
    for dx, dv in ((-1.0, -0.28), (-0.5, 0.12), (-0.95, 0.15)):
        z = rng.uniform(0.09, 0.13)
        stones.box((z, z * 0.85, z * 0.6), (dx, vp + dv, 0.02 + z * 0.3), (0, 0, rng.uniform(0, 90)), Fp)
    stones.finish("roof_patch_stones", mats["stone_wall"], root, bevel=0.015)


def _stone(kit, mats, rng, root, name, size, loc, rot=(0, 0, 0)):
    return kit.box(name, size, loc, rot, mats["stone_wall"], bevel=0.025, parent=root)


def _hearth(kit, mats, rng, root):
    wd = mats["wood_dark"]
    hy = HEARTH_Y
    _stone(kit, mats, rng, root, "table", (1.30, 0.90, TABLE_Z), (0, hy, TABLE_Z / 2))
    cheek_h = 1.38 - TABLE_Z
    for sx in (-1, 1):
        _stone(kit, mats, rng, root, f"cheek_{sx}", (0.14, 0.90, cheek_h), (sx * 0.58, hy, TABLE_Z + cheek_h / 2))
    _stone(kit, mats, rng, root, "back", (1.02, 0.28, cheek_h), (0, hy + 0.31, TABLE_Z + cheek_h / 2))
    # lintel over the opening; the hood corbels out above it
    kit.box("lintel", (1.46, 0.17, 0.16), (0, hy - 0.52, 1.46), (0, 0, 0), wd, bevel=0.012, parent=root)
    y0, y1 = hy - 0.45, hy + 0.45
    z0, z1 = 1.38, 2.35
    sx0, sx1 = 0.65, 0.25
    by0, by1 = hy + 0.12, hy + 0.45
    verts = [(-sx0, y0, z0), (sx0, y0, z0), (sx0, y1, z0), (-sx0, y1, z0),
             (-sx1, by0, z1), (sx1, by0, z1), (sx1, by1, z1), (-sx1, by1, z1)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    kit.mesh("hood", verts, faces, mat=mats["stone_wall"], parent=root, bevel=0.025)
    # stack and cap
    h = STACK_TOP - z1
    _stone(kit, mats, rng, root, "stack", (0.50, 0.33, h), (0, hy + 0.285, z1 + h / 2))
    _stone(kit, mats, rng, root, "cap", (0.64, 0.47, 0.09), (0, hy + 0.285, STACK_TOP + 0.045))
    kit.box("flue", (0.28, 0.17, 0.02), (0, hy + 0.285, STACK_TOP + 0.092), mat=mats["iron"], parent=root)
    # a few stones knocked loose from the stack top, soot-dark
    for i in range(3):
        s = rng.uniform(0.08, 0.12)
        _stone(kit, mats, rng, root, f"fallen_{i}", (s, s * 0.8, s * 0.6),
               (rng.uniform(-0.9, 0.9), rng.uniform(-0.55, -0.3), s * 0.28), (0, 0, rng.uniform(0, 90)))


def _fire_bed(kit, mats, rng, root):
    embers, char = mats["embers"], mats["wood_dark"]
    hy = HEARTH_Y
    zt = TABLE_Z
    # rim stones round the bed and a low front lip
    for i in range(7):
        a = math.radians(200 + i * 22)
        _stone(kit, mats, rng, root, f"rim_{i}", (0.1, 0.1, 0.07),
               (0.0 + 0.42 * math.cos(a), hy + 0.05 + 0.3 * math.sin(a) * 0.9 - 0.02, zt + 0.03),
               (0, 0, math.degrees(a)))
    _stone(kit, mats, rng, root, "lip", (0.86, 0.09, 0.07), (0, hy - 0.40, zt + 0.03))
    # banked bed: a mound of grey ash over the coals, a few coals glowing dull red where the ash
    # is thin, and black unburnt lumps round the edge
    ash = _ash_material()
    kit.sphere("ash_mound", 0.3, (0, hy - 0.02, zt + 0.02), scale=(1.3, 0.95, 0.36), mat=ash, segments=16,
               parent=root)
    for i in range(6):
        a = 2 * math.pi * i / 6 + rng.uniform(-0.4, 0.4)
        r = rng.uniform(0.08, 0.3)
        kit.sphere(f"ash_lump_{i}", rng.uniform(0.07, 0.11),
                   (r * math.cos(a) * 1.2, hy - 0.02 + r * math.sin(a) * 0.75, zt + 0.06),
                   scale=(1.3, 1.0, 0.5), mat=ash, segments=10, parent=root)
    for i, (dx, dy, rad) in enumerate(((-0.16, -0.2, 0.035), (0.05, -0.24, 0.03), (0.2, -0.16, 0.028),
                                      (-0.3, -0.06, 0.03), (0.09, 0.02, 0.022))):
        kit.sphere(f"glow_{i}", rad, (dx, hy - 0.02 + dy, zt + 0.065 if dy < -0.1 else zt + 0.1),
                   scale=(1.2, 1.0, 0.6), mat=embers, segments=8, parent=root)
    for i in range(6):
        a = 2 * math.pi * i / 6 + rng.uniform(-0.4, 0.4)
        r = rng.uniform(0.3, 0.42)
        kit.sphere(f"coal_{i}", rng.uniform(0.035, 0.055),
                   (r * math.cos(a) * 1.1, hy - 0.02 + r * math.sin(a) * 0.65, zt + 0.05),
                   scale=(1.2, 0.9, 0.7), mat=char, segments=8, parent=root)
    # fire rake leaning on the right cheek, the tool that banked it
    iron = mats["iron"]
    kit.beam("rake_shaft", (0.78, hy - 0.62, 0.02), (0.68, hy - 0.46, 1.36), (0.022, 0.022), iron, parent=root)
    kit.box("rake_head", (0.16, 0.02, 0.07), (0.785, hy - 0.64, 0.05), (0, 0, 8), iron, parent=root)


def _bellows(kit, mats, rng, root):
    wo, wd, iron, leather = mats["wood_old"], mats["wood_dark"], mats["iron"], mats["door_wood"]
    y = HEARTH_Y + 0.05
    hx = -0.80                  # hinge end, toward the hearth
    length, width = 0.62, 0.40
    zl = 0.74                   # top of the lower board
    # trestle
    for i, x in enumerate((-0.85, -1.32)):
        for j, sy in enumerate((-1, 1)):
            kit.beam(f"trestle_{i}_{j}", (x, y + sy * 0.19, 0.0), (x + rng.uniform(-0.02, 0.02), y + sy * 0.2, zl - 0.02),
                     (0.06, 0.06), wd, bevel=0.006, parent=root)
    kit.beam("trestle_rail_a", (-0.85, y - 0.19, 0.4), (-0.85, y + 0.19, 0.4), (0.045, 0.045), wd, parent=root)
    kit.beam("trestle_rail_b", (-1.32, y - 0.19, 0.4), (-1.32, y + 0.19, 0.4), (0.045, 0.045), wd, parent=root)
    kit.box("bellows_low", (length, width, 0.04), (hx - length / 2, y, zl - 0.02), mat=wo, bevel=0.006, parent=root)
    tilt = 15.0
    c, s = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    kit.box("bellows_top", (length, width, 0.04), (hx - length / 2 * c, y, zl + 0.05 + length / 2 * s),
            (0, tilt, 0), wo, bevel=0.006, parent=root)
    # leather: pleated side panels and the rear cap
    n = 4
    rear = hx - length
    for sy in (-1, 1):
        verts, faces = [], []
        for i in range(n):
            x = hx + (rear - hx) * i / (n - 1)
            zu = zl + 0.05 + (hx - x) * s / c * 1.0
            off = width / 2 + 0.012 + (0.025 if i % 2 else 0.0)
            verts += [(x, y + sy * off, zl + 0.0), (x, y + sy * off, zu)]
        for i in range(n - 1):
            a = 2 * i
            faces.append((a, a + 2, a + 3, a + 1) if sy > 0 else (a, a + 1, a + 3, a + 2))
        kit.mesh(f"bellows_side_{sy}", verts, faces, mat=leather, parent=root)
    zu = zl + 0.05 + length * s / c
    kit.mesh("bellows_rear", [(rear, y - width / 2, zl), (rear, y + width / 2, zl), (rear, y + width / 2, zu),
                              (rear, y - width / 2, zu)], [(0, 3, 2, 1)], mat=leather, parent=root)
    for i in range(3):
        x = hx + (rear - hx) * (i + 0.5) / 3
        zr = zl + 0.05 + (hx - x) * s / c
        kit.box(f"bellows_rib_{i}", (0.022, width + 0.05, zr - zl + 0.03), (x, y, (zl + zr) / 2), mat=wd,
                parent=root)
    # handle pole with a rope loop, and the nozzle and tuyere that reach into the cheek
    kit.beam("bellows_handle", (rear + 0.05, y, zu), (rear - 0.18, y, zu + 0.72), (0.04, 0.04), wo, bevel=0.005,
             parent=root)
    kit.torus("handle_loop", 0.05, 0.009, (rear - 0.17, y, zu + 0.62), (90, 0, 0), mats["rope"], major_segments=10,
              minor_segments=4, parent=root)
    kit.cylinder("nozzle", 0.03, 0.2, (hx + 0.08, y, zl + 0.05), (0, 90, 0), iron, segments=10,
                 radius_top=0.018, parent=root)
    kit.cylinder("tuyere", 0.026, 0.56, (-0.42, y, TABLE_Z + 0.11), (0, 90, 0), iron, segments=10, parent=root)
    kit.beam("tuyere_elbow", (hx + 0.17, y, zl + 0.05), (-0.74, y, TABLE_Z + 0.11), (0.03, 0.03), iron, parent=root)


def _anvil(kit, mats, rng, root):
    wd, iron = mats["wood_dark"], mats["iron"]
    x0, y0 = 0.75, -0.5
    sh = 0.52
    kit.cylinder("stump", 0.27, sh, (x0, y0, sh / 2), mat=wd, segments=12, radius_top=0.25, bevel=0.012, parent=root)
    kit.cylinder("stump_flare", 0.34, 0.1, (x0, y0, 0.05), mat=wd, segments=12, radius_top=0.27, parent=root)
    kit.box("anvil_base", (0.34, 0.22, 0.06), (x0, y0, sh + 0.03), (0, 0, 4), iron, bevel=0.01, parent=root)
    kit.box("anvil_waist", (0.17, 0.12, 0.17), (x0, y0, sh + 0.145), (0, 0, 4), iron, bevel=0.01, parent=root)
    kit.box("anvil_face", (0.50, 0.15, 0.08), (x0, y0, sh + 0.29), (0, 0, 4), iron, bevel=0.008, parent=root)
    kit.cylinder("anvil_horn", 0.065, 0.28, (x0 - 0.38, y0 + 0.02, sh + 0.29), (0, -90, 4), iron, segments=10,
                 radius_top=0.012, parent=root)
    kit.box("anvil_heel", (0.10, 0.14, 0.07), (x0 + 0.3, y0 - 0.02, sh + 0.285), (0, 0, 4), iron, bevel=0.008,
            parent=root)
    # the hammer laid on the face at the end of the day
    kit.beam("hammer_handle", (x0 + 0.02, y0 - 0.02, sh + 0.345), (x0 + 0.34, y0 - 0.1, sh + 0.345), (0.028, 0.03),
             mats["wood_old"], parent=root)
    kit.box("hammer_head", (0.05, 0.12, 0.05), (x0 - 0.02, y0 - 0.01, sh + 0.355), (0, 0, -14), iron, bevel=0.005,
            parent=root)


def _tub(kit, mats, rng, root):
    wd, iron = mats["wood_dark"], mats["iron"]
    x0, y0 = 1.5, -0.38
    h = 0.62
    kit.cylinder("tub", 0.27, h, (x0, y0, h / 2), mat=wd, segments=16, radius_top=0.32, bevel=0.008, parent=root)
    for i, z in enumerate((0.10, 0.34, 0.56)):
        r = 0.27 + (0.32 - 0.27) * z / h + 0.008
        kit.torus(f"tub_hoop_{i}", r, 0.014, (x0, y0, z), mat=iron, major_segments=18, minor_segments=4, parent=root)
    n = 28
    zw = h - 0.07
    rw = 0.27 + 0.05 * zw / h - 0.012
    verts = [(x0, y0, zw)] + [(x0 + rw * math.cos(2 * math.pi * j / n), y0 + rw * math.sin(2 * math.pi * j / n), zw)
                              for j in range(n)]
    faces = [(0, 1 + (j + 1) % n, 1 + j) for j in range(n)]
    kit.mesh("quench_water", verts, faces, mat=_water_material(), parent=root)
    # tongs resting across the rim
    kit.beam("tongs_a", (x0 - 0.3, y0 + 0.02, h + 0.02), (x0 + 0.42, y0 + 0.12, h + 0.04), (0.02, 0.022), iron, parent=root)
    kit.beam("tongs_b", (x0 - 0.3, y0 + 0.05, h + 0.045), (x0 + 0.42, y0 + 0.1, h + 0.06), (0.02, 0.022), iron, parent=root)


def _rack(kit, mats, rng, root):
    wo, wd, iron, rope = mats["wood_old"], mats["wood_dark"], mats["iron"], mats["rope"]
    y = 0.84
    xl, xr = 0.55, 1.75
    for i, x in enumerate((xl, xr)):
        kit.beam(f"rack_post_{i}", (x, y, 0.0), (x + rng.uniform(-0.015, 0.015), y, 1.82), (0.09, 0.09), wd,
                 bevel=0.008, parent=root)
    kit.beam("rack_rail", (xl - 0.05, y - 0.07, 1.46), (xr + 0.05, y - 0.07, 1.46), (0.06, 0.07), wo, parent=root)
    kit.beam("rack_mid", (xl, y - 0.07, 1.0), (xr, y - 0.07, 1.0), (0.05, 0.05), wo, parent=root)
    kit.box("rack_shelf", (xr - xl + 0.1, 0.3, 0.04), (0.5 * (xl + xr), y - 0.1, 0.6), (0, 0, 0), wo, bevel=0.006,
            parent=root)
    # tools on pegs: three pairs of tongs, two hammers, a rasp, a punch
    for i, x in enumerate((0.72, 0.9, 1.08)):
        kit.beam(f"tong_{i}", (x, y - 0.1, 1.44), (x + rng.uniform(-0.02, 0.02), y - 0.1, 0.82 - 0.06 * i), (0.022, 0.015),
                 iron, parent=root)
        kit.beam(f"tong_b_{i}", (x + 0.02, y - 0.11, 1.44), (x + 0.045, y - 0.11, 0.84 - 0.06 * i), (0.022, 0.015), iron,
                 parent=root)
    for i, x in enumerate((1.3, 1.47)):
        kit.beam(f"hammer_{i}", (x, y - 0.1, 1.4), (x, y - 0.1, 1.0 - 0.1 * i), (0.03, 0.025), wo, parent=root)
        kit.box(f"hammer_head_{i}", (0.1, 0.05, 0.05), (x, y - 0.1, 1.4 + 0.02), mat=iron, bevel=0.005, parent=root)
    kit.beam("rasp", (1.62, y - 0.1, 1.42), (1.64, y - 0.1, 1.02), (0.045, 0.012), iron, parent=root)
    # horseshoes stacked on the shelf, a nail pot, a wire coil
    for i in range(6):
        kit.torus(f"shoe_{i}", 0.055, 0.011, (0.8 + rng.uniform(-0.015, 0.015), y - 0.1, 0.63 + i * 0.022),
                  mat=iron, major_segments=12, minor_segments=4, parent=root)
    kit.cylinder("nail_pot", 0.07, 0.11, (1.2, y - 0.1, 0.675), mat=wd, segments=10, radius_top=0.06, parent=root)
    kit.torus("wire_coil", 0.09, 0.012, (1.5, y - 0.1, 0.63), mat=iron, major_segments=14, minor_segments=4,
              parent=root)
    for sx in (0.0, 0.1):
        kit.torus(f"coil_rope_{sx}", 0.1 - sx * 0.2, 0.01, (xr - 0.03, y - 0.14, 1.28), (90, 0, 0), rope,
                  major_segments=12, minor_segments=4, parent=root)


def _ground(kit, mats, rng, root):
    """Flagstones in front of the fire, a soot stain and a heap of charcoal at the hearth foot."""
    stone = mats["stone_wall"]
    for i in range(11):
        x = rng.uniform(-1.05, 1.5)
        y = rng.uniform(-0.95, 0.0)
        kit.box(f"flag_{i}", (rng.uniform(0.35, 0.6), rng.uniform(0.3, 0.5), 0.05), (x, y, 0.012),
                (0, 0, rng.uniform(-14, 14)), stone, bevel=0.012, parent=root)
    for i in range(9):
        a = rng.uniform(0, 2 * math.pi)
        kit.sphere(f"charcoal_{i}", rng.uniform(0.03, 0.055),
                   (-0.35 + 0.25 * math.cos(a), -0.3 + 0.12 * math.sin(a), 0.03), scale=(1.2, 1.0, 0.7),
                   mat=mats["wood_dark"], segments=8, parent=root)
    # a dropped horseshoe and a spent bar
    kit.torus("dropped_shoe", 0.055, 0.011, (0.32, -0.9, 0.012), mat=mats["iron"], major_segments=12, minor_segments=4,
              parent=root)
    kit.beam("spent_bar", (-0.2, -1.0, 0.03), (0.5, -0.85, 0.025), (0.03, 0.03), mats["iron"], parent=root)


def _charcoal_sack(kit, mats, rng, root):
    """Slumped sack of charcoal at the front left, spilling a little onto the flagstones."""
    bur = mats["burlap"]
    x, y = -1.05, -0.15
    kit.sphere("sack_belly", 0.24, (x, y, 0.2), scale=(0.95, 0.75, 0.85), mat=bur, segments=14, parent=root)
    kit.cylinder("sack_neck", 0.07, 0.12, (x + 0.03, y, 0.42), (0, 8, 0), bur, segments=8, radius_top=0.05, parent=root)
    kit.torus("sack_tie", 0.062, 0.01, (x + 0.03, y, 0.39), mat=mats["rope"], major_segments=10, minor_segments=4,
              parent=root)
    for i in range(7):
        a = rng.uniform(-1.0, 1.0) - 1.57
        r = rng.uniform(0.28, 0.5)
        kit.sphere(f"spill_{i}", rng.uniform(0.025, 0.045), (x + r * math.cos(a), y + r * math.sin(a) * 0.9, 0.025),
                   scale=(1.2, 1.0, 0.7), mat=mats["wood_dark"], segments=8, parent=root)


def build(kit, mats, rng):
    root = kit.group("forge")
    _ground(kit, mats, rng, root)
    _hearth(kit, mats, rng, root)
    _fire_bed(kit, mats, rng, root)
    _bellows(kit, mats, rng, root)
    _anvil(kit, mats, rng, root)
    _tub(kit, mats, rng, root)
    _charcoal_sack(kit, mats, rng, root)
    _rack(kit, mats, rng, root)
    _roof(kit, mats, rng, root)
    # the banked coals: a weak glow that reaches the hearth table and the floor in front, not the yard
    _lights.add(root, "forge_embers", (0.0, HEARTH_Y - 0.2, TABLE_Z + 0.25), (1.0, 0.22, 0.05), 22.0,
                radius=0.3, specular=0.25, reach=2.6)
    # guarded so a change in the shared effect signature drops the plume instead of the whole prop
    try:
        _fire.smoke(kit, mats["smoke"], root, "smoke", seed=rng.uniform(0, 50), **SMOKE)
    except TypeError:
        pass
    return root

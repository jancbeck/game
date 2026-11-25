"""Old two-wheeled handcart, tipped forward so both shafts rest on the ground.

Long axis along X, shafts toward -X, near wheel on the -Y side. The bed pitches about the
axle by TILT. Each side rail runs on as one continuous tapering shaft with a slight curve
and an iron ferrule. The 3.5 m footprint (bed plus shafts) is centered on the origin.
Inside the bed: gapped planks, loose boards, two burlap sacks, straw and a rope coil.
"""

import math

from mathutils import Vector

from ._sweep import ribbons, rope, sweep

AXLE_X = 0.44        # axle position in the root frame
AXLE_Z = 0.5         # equals the wheel radius, so the tyre touches Z = 0
TILT = -12.0         # bed pitch about Y in degrees; negative lowers the shafts
WHEEL_Y = 0.76       # wheel centers sit outside the bed sides
X0, X1 = -1.0, 1.2   # bed ends relative to the axle
FLOOR = 0.12         # top of the floor planks relative to the axle
SHAFT_END = -2.25    # shaft tip in the bed frame
RAIL_Y = 0.42


def _ring(kit, name, r_in, r_out, width, a0, a1, mat, parent, bevel=0.004, step=6.0):
    """Ring segment around the local Y axis (a wheel rim piece or tyre); a0..a1 in degrees."""
    n = max(2, int(math.ceil((a1 - a0) / step)))
    full = abs((a1 - a0) - 360.0) < 1e-6
    verts, faces = [], []
    for i in range(n + (0 if full else 1)):
        a = math.radians(a0 + (a1 - a0) * i / n)
        c, s = math.cos(a), math.sin(a)
        for r, y in ((r_in, -width / 2), (r_out, -width / 2), (r_out, width / 2), (r_in, width / 2)):
            verts.append((r * c, y, r * s))
    m = len(verts) // 4
    for i in range(n if not full else m):
        b, c = i * 4, ((i + 1) % m) * 4
        for j in range(4):
            faces.append((b + j, b + (j + 1) % 4, c + (j + 1) % 4, c + j))
    if not full:
        faces.append((0, 1, 2, 3))
        faces.append((n * 4 + 3, n * 4 + 2, n * 4 + 1, n * 4))
    return kit.mesh(name, verts, faces, mat=mat, parent=parent, bevel=bevel)


def _wheel(kit, mats, rng, root, side):
    name = "near" if side < 0 else "far"
    wo, wd, iron = mats["wood_old"], mats["wood_dark"], mats["iron"]
    g = kit.group(f"wheel_{name}", (AXLE_X, side * WHEEL_Y, AXLE_Z), parent=root)
    g.rotation_euler = (0, 0, math.radians(side * 1.5))
    phase = rng.uniform(0, 30)

    # hub: barrel-shaped, with iron bands and the axle cap
    sweep(kit, "hub", [(0, -0.10, 0), (0, 0, 0), (0, 0.10, 0)], [0.052, 0.085, 0.052], mat=wd,
          parent=g, sides=12, ref=(1, 0, 0))
    for y in (-0.06, 0.06):
        kit.cylinder("hub_band", 0.09, 0.022, (0, y, 0), (90, 0, 0), iron, segments=12, parent=g)
    kit.cylinder("axle_cap", 0.034, 0.04, (0, side * 0.115, 0), (90, 0, 0), iron, segments=8,
                 parent=g)

    # six rim segments with visible joints, twelve tapered spokes, one iron tyre with nails
    for i in range(6):
        a0 = phase + i * 60 + 0.8
        _ring(kit, f"felloe_{i}", 0.402, 0.466, 0.072, a0, a0 + 58.4, wo, g)
    for i in range(12):
        a = math.radians(phase + 30 + i * 30 + kit.jitter(rng, 1.0))
        c, s = math.cos(a), math.sin(a)
        sweep(kit, f"spoke_{i}", [(0.07 * c, 0, 0.07 * s), (0.42 * c, 0, 0.42 * s)], [0.027, 0.015],
              [0.022, 0.013], wo, g, sides=6, ref=(0, 1, 0))
    _ring(kit, "tyre", 0.466, 0.5, 0.062, 0, 360, iron, g, bevel=0.005, step=7.5)
    for i in range(12):
        a_deg = phase + 15 + i * 30
        a = math.radians(a_deg)
        kit.box(f"nail_{i}", (0.012, 0.02, 0.02), (0.5 * math.cos(a), 0.018 * (-1) ** i, 0.5 * math.sin(a)),
                (0, -a_deg, 0), iron, parent=g)


def _shaft(kit, mat, iron, bed, side, rng):
    """Rail and shaft as one member: level under the bed, then curving down toward the tip."""
    ctrl = [(1.3, side * RAIL_Y, 0.04), (0.4, side * RAIL_Y, 0.04), (X0 - 0.05, side * RAIL_Y, 0.04)]
    tip = SHAFT_END + (0.04 if side > 0 else 0.0)
    for x in (-1.5, -1.9, tip):
        t = (-1.05 - x) / 1.2
        ctrl.append((x, side * (RAIL_Y - 0.05 * t ** 1.5), 0.04 - 0.045 * t * t))
    sweep(kit, f"shaft_{'r' if side > 0 else 'l'}", ctrl, [0.05, 0.05, 0.05, 0.05, 0.047, 0.040, 0.033],
          [0.04, 0.04, 0.04, 0.04, 0.038, 0.034, 0.030], mat, bed, sides=8, step=0.04)
    end = Vector(ctrl[-1])
    back = (Vector(ctrl[-2]) - end).normalized()
    sweep(kit, f"ferrule_{'r' if side > 0 else 'l'}", [end + back * 0.07, end], 0.037, 0.034, iron, bed,
          sides=8)


def _straw(kit, mat, bed, rng, count, spread):
    """Loose stalks as thin flat ribbons lying on the bed floor and drooping over the edges."""
    blades = []
    for _ in range(count):
        cx, cy = spread[0] + rng.uniform(-spread[2], spread[2]), spread[1] + rng.uniform(-spread[3], spread[3])
        a = rng.uniform(0, math.pi)
        d = Vector((math.cos(a), math.sin(a), rng.uniform(0.0, 0.25))).normalized()
        n = Vector((-d.y, d.x, 0.0))
        ln = rng.uniform(0.18, 0.42)
        p0 = Vector((cx, cy, FLOOR + 0.005 + rng.uniform(0, 0.06))) - d * ln / 2
        rows = []
        for s in (0.0, 0.5, 1.0):
            c = p0 + d * (ln * s) + Vector((0, 0, -0.03 * s * s * rng.uniform(0.3, 1.0)))
            rows.append((c - n * 0.004, c + n * 0.004))
        blades.append(rows)
    ribbons(kit, "straw", blades, mat, bed)


def build(kit, mats, rng):
    wo, wd, iron, rp = mats["wood_old"], mats["wood_dark"], mats["iron"], mats["rope"]
    burlap, straw = mats["burlap"], mats["straw"]
    j = lambda a: kit.jitter(rng, a)  # noqa: E731
    root = kit.group("cart")
    bed = kit.group("cart_bed", (AXLE_X, 0, AXLE_Z), parent=root)
    bed.rotation_euler = (0, math.radians(TILT), 0)

    # axle: iron arms through the hubs, wooden axletree under the rails
    kit.cylinder("axle", 0.031, 1.74, (AXLE_X, 0, AXLE_Z), (90, 0, 0), iron, segments=8, parent=root)
    kit.box("axletree", (0.13, 1.0, 0.095), (0, 0, -0.045), mat=wd, bevel=0.012, parent=bed)
    for side in (-1, 1):
        kit.box(f"axle_strap_{side}", (0.17, 0.03, 0.14), (0, side * 0.45, -0.01), mat=iron,
                bevel=0.004, parent=bed)
    _wheel(kit, mats, rng, root, -1)
    _wheel(kit, mats, rng, root, 1)

    # shafts and crossbars
    for side in (-1, 1):
        _shaft(kit, wd, iron, bed, side, rng)
    kit.box("crossbar", (0.1, 0.96, 0.07), (-0.85, 0, 0.04), mat=wd, bevel=0.01, parent=bed)
    kit.beam("stretcher", (-1.7, -0.40, 0.027), (-1.7, 0.40, 0.027), (0.055, 0.05), wd, 0.01, parent=bed)
    for side in (-1, 1):
        kit.box(f"stretcher_band_{side}", (0.07, 0.03, 0.07), (-1.7, side * 0.385, 0.027), mat=iron,
                bevel=0.004, parent=bed)

    # bearers across the rails, planks on top with gaps between them
    stake_x = (-0.97, -0.3, 0.45, 1.17)
    for i, x in enumerate(stake_x):
        kit.box(f"bearer_{i}", (0.07, 1.40, 0.06), (x, 0, 0.05), mat=wd, bevel=0.008, parent=bed)
    for i in range(6):
        y = -0.5125 + 0.205 * i
        length = 2.2 - rng.uniform(0, 0.12)
        kit.box(f"floor_{i}", (length, 0.185 + j(0.004), 0.04), (0.1 - (2.2 - length) / 2 * 0 + j(0.03), y,
                FLOOR - 0.02 + j(0.004)), (0, j(0.6), j(0.8)), wo, bevel=0.008, parent=bed)

    # side boards with gaps, near top plank split and hanging
    for side in (-1, 1):
        y = side * 0.575
        for k, z in enumerate((0.20, 0.37, 0.54)):
            if side < 0 and k == 2:
                kit.box("side_near_top_a", (1.1, 0.04, 0.13), (-0.45, y, z + j(0.01)), mat=wo,
                        bevel=0.01, parent=bed)
                kit.box("side_near_top_b", (0.9, 0.04, 0.13), (0.73, y - 0.03, z - 0.08), (6, 14, 0),
                        wo, bevel=0.01, parent=bed)
                continue
            length = 2.2 - (rng.uniform(0.1, 0.35) if k == 2 else rng.uniform(0, 0.06))
            kit.box(f"side_{side}_{k}", (length, 0.04, 0.13),
                    (0.1 - (2.2 - length) / 2 * rng.choice((-1, 1)), y, z + j(0.008)),
                    (side * j(3.0), j(1.2), 0), wo, bevel=0.01, parent=bed)

    # stakes standing on the bearer ends, each with an iron strap
    for side in (-1, 1):
        for n, x in enumerate(stake_x):
            top = 0.68 - (rng.uniform(0.05, 0.12) if rng.random() < 0.3 else 0)
            kit.box(f"stake_{side}_{n}", (0.07, 0.07, top - 0.02), (x + j(0.01), side * 0.635, (top + 0.02) / 2),
                    (side * j(2.5), j(1.5), 0), wd, bevel=0.01, parent=bed)
            kit.box(f"stake_strap_{side}_{n}", (0.078, 0.078, 0.03), (x, side * 0.635, 0.1), mat=iron,
                    bevel=0.004, parent=bed)

    # front board (two planks), rear tailgate (one plank in place, one ajar) with hinge straps
    for k, z in enumerate((0.205, 0.365)):
        kit.box(f"front_{k}", (0.04, 1.16, 0.14), (X0 - 0.02, j(0.01), z + j(0.008)),
                (j(1.5), 0, j(1.5)), wo, bevel=0.01, parent=bed)
    kit.box("tail_low", (0.04, 1.16, 0.14), (X1 + 0.02, 0, 0.205), mat=wo, bevel=0.01, parent=bed)
    kit.box("tail_ajar", (0.04, 1.16, 0.14), (X1 + 0.08, 0.02, 0.33), (0, -28, 3), wo,
            bevel=0.01, parent=bed)
    for y in (-0.42, 0.42):
        kit.box(f"tail_hinge_{y}", (0.05, 0.3, 0.02), (X1 + 0.045, y, 0.205), mat=iron, bevel=0.004,
                parent=bed)

    # loose planks and shards inside, mostly toward the rear
    for i in range(5):
        length = rng.uniform(0.5, 1.0)
        kit.box(f"board_{i}", (length, rng.uniform(0.09, 0.15), 0.03),
                (rng.uniform(0.1, 0.8), rng.uniform(-0.28, 0.28), FLOOR + 0.03 + rng.uniform(0, 0.1)),
                (j(8), j(18), rng.uniform(0, 180)), wo, bevel=0.008, parent=bed)
    for i in range(2):
        kit.box(f"shard_{i}", (0.3, 0.06, 0.05), (rng.uniform(0.0, 0.8), rng.uniform(-0.25, 0.25), FLOOR + 0.2),
                (j(30), j(30), rng.uniform(0, 180)), wd, bevel=0.008, parent=bed)

    # burlap sacks: one lying against the front board, one slumped against the far side
    z = FLOOR + 0.11
    sweep(kit, "sack_lying", [(-0.88, -0.17, z), (-0.55, -0.20, z + 0.01), (-0.2, -0.17, z + 0.01),
                              (0.0, -0.14, z - 0.01), (0.1, -0.12, z - 0.02)],
          [0.07, 0.125, 0.13, 0.085, 0.03], [0.07, 0.115, 0.12, 0.075, 0.03], burlap, bed, sides=12,
          step=0.04, rng=rng, rough=0.07)
    kit.torus("sack_tie", 0.04, 0.007, (0.0, -0.14, z - 0.01), (0, 90, 0), rp, 12, 5, bed)
    sweep(kit, "sack_slumped", [(0.35, 0.34, FLOOR + 0.02), (0.36, 0.33, FLOOR + 0.17), (0.38, 0.31, FLOOR + 0.33),
                                (0.42, 0.29, FLOOR + 0.42), (0.45, 0.28, FLOOR + 0.47)],
          [0.12, 0.16, 0.15, 0.08, 0.03], [0.13, 0.17, 0.14, 0.07, 0.03], burlap, bed, sides=12,
          step=0.04, rng=rng, rough=0.08)

    # straw: a flattened mound plus stalks drooping over the rear and between the planks
    kit.sphere("straw_mound", 1.0, (0.88, -0.1, FLOOR + 0.03), scale=(0.34, 0.27, 0.07), mat=straw,
               segments=12, parent=bed)
    _straw(kit, straw, bed, rng, 70, (0.7, -0.05, 0.45, 0.4))

    # rope coil
    spiral = [(0.1 * math.cos(t) * (1 - t / 40), 0.1 * math.sin(t) * (1 - t / 40), 0.012 * t / 6.3)
              for t in [i * 0.45 for i in range(30)]]
    rope(kit, "rope_coil", [(0.62 + x, 0.2 + y, FLOOR + 0.03 + z) for x, y, z in spiral], 0.014, rp, bed,
         lay=0.07, step=0.012, sides=5)
    return root

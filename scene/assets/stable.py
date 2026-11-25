"""Timber stable lean-to for two horses, built against a curtain wall.

Footprint 3.6 m along the wall (X) by 3.0 m deep (Y), plus a hitching rail 0.7 m in front.
The wall is at local y = +1.5 and the open front faces -Y, like the shed. Place it with rot_z -90
to put the wall on the east side: the center is then 1.5 m out from the wall face, and local +X
runs south. Built at full size, so use scale 1.

The mono-pitch roof drops from 3.6 m at the wall to 2.4 m at the eave, 3.15 m of slope. It is
split cedar-style shingles on sheathing and rafters, with lost and slipped shingles, one hole,
moss on the wet eave side and a burlap patch weighted with stones. Three heavy posts carry the
front plate; the two ends are closed with weathered boards, some of them gone. Two stalls are
divided by a plank partition with open bars at the head end. Each stall has a manger and a
slatted hay rack stuffed with hay on the wall, a tie ring with a rope, and a bed of wet straw.

Hay is kept dry in a half loft over the head end: a beam on three posts 1.25 m out from the
wall, joists to a ledger on the wall, and a board floor at 2.44 m stacked with hay. The boards
stop short of the wall, so hay is pushed down through the slot straight into the racks. The oat
bin, a lidded plank chest with an iron hasp and a stone on the lid against rats, stands at the
tail end of the north stall against the end wall, out of reach of a tied horse.

The south stall holds a dark horse with its head down in the manger. Outside: a hitching rail
with a lead rope, a bucket, a pitchfork against a post, and the north stall's breast bar fallen
out of its notches. A saddle on its blanket is hung over the partition. Mud and straw are trodden
out of the stalls into an apron in front, with hoof prints, and a trail of dropped straw runs
south toward the muck heap (a separate prop, `muck_heap`).
"""

import math

from . import _se_mesh as sm
from . import _sweep, bucket, straw_pile

W = 3.6
D = 3.0
WALL_Y = D / 2
FRONT_Y = -1.30                 # front posts and plate
EAVE_Y = -1.65                  # lower roof edge
Z_EAVE, Z_WALL = 2.40, 3.60     # shingle top at the eave and at the wall
SLOPE = (Z_WALL - Z_EAVE) / (WALL_Y - EAVE_Y)
ALPHA = math.atan(SLOPE)
COS_A, SIN_A = math.cos(ALPHA), math.sin(ALPHA)
SLOPE_LEN = math.hypot(WALL_Y - EAVE_Y, Z_WALL - Z_EAVE)
UNDER = 0.195                   # shingle top down to the rafter underside
ROOF_HALF = 2.0                 # roof edge in X
POST_X = (-1.8, 0.0, 1.8)
STALL_X = (-0.9, 0.9)

# the hole where shingles are gone: u range, slope-distance range
HOLE = ((0.55, 0.95), (1.30, 1.80))


def roof_z(y):
    return Z_EAVE + SLOPE * (y - EAVE_Y)


def under_z(y):
    return roof_z(y) - UNDER


def _rafter_z(y):
    """Center line of a rafter, 0.13 m (measured square to the slope) under the shingle top."""
    return roof_z(y) - 0.13 / COS_A


def _post(kit, mats, rng, root, name, x, y, z0, z1, section=0.17, mat=None, lean=0.01):
    kit.beam(name, (x, y, z0), (x + rng.uniform(-lean, lean), y + rng.uniform(-lean, lean), z1),
             (section, section), mat or mats["wood_dark"], bevel=0.012, parent=root)


def _pad(kit, mats, rng, root, name, x, y):
    s = rng.uniform(0.38, 0.5)
    kit.box(name, (s, s * rng.uniform(0.9, 1.1), 0.16), (x, y, 0.03),
            (rng.uniform(-2, 2), rng.uniform(-2, 2), rng.uniform(-15, 15)), mats["stone_wall"],
            bevel=0.03, parent=root)


# ---- frame ---------------------------------------------------------------------------------

def _frame(kit, mats, rng, root):
    wd, wo = mats["wood_dark"], mats["wood_old"]
    plate_top = under_z(FRONT_Y)
    kit.box("front_plate", (W + 0.35, 0.16, 0.19), (0, FRONT_Y, plate_top - 0.095), mat=wd, bevel=0.012,
            parent=root)
    for i, x in enumerate(POST_X):
        _pad(kit, mats, rng, root, f"pad_{i}", x, FRONT_Y)
        _post(kit, mats, rng, root, f"front_post_{i}", x, FRONT_Y, 0.08, plate_top - 0.15)
        _post(kit, mats, rng, root, f"rear_post_{i}", x, WALL_Y - 0.11, 0.05, under_z(WALL_Y - 0.11) - 0.12,
              section=0.15)
    # knee braces between each post and the plate
    for i, (x, d) in enumerate(((-1.8, 1), (0.0, -1), (0.0, 1), (1.8, -1))):
        z1 = plate_top - 0.17
        kit.beam(f"brace_{i}", (x, FRONT_Y - 0.01, z1 - 0.52), (x + d * 0.55, FRONT_Y - 0.01, z1),
                 (0.09, 0.11), wo, bevel=0.01, parent=root)
    # plate bolted to the wall, rafters from plate to the front plate and past it
    kit.box("wall_plate", (W + 0.35, 0.13, 0.16), (0, WALL_Y - 0.065, under_z(WALL_Y) - 0.09), mat=wd,
            bevel=0.012, parent=root)
    for i in range(8):
        x = -1.85 + 3.7 * i / 7
        y0, y1 = EAVE_Y + 0.02, WALL_Y - 0.06
        kit.beam(f"rafter_{i}", (x, y0, _rafter_z(y0)), (x, y1, _rafter_z(y1)), (0.08, 0.13), wo,
                 bevel=0.008, parent=root)
    # sheathing: one slab under the shingles
    ym = (EAVE_Y + WALL_Y) / 2
    kit.box("sheathing", (2 * ROOF_HALF, SLOPE_LEN, 0.04), (0, ym, roof_z(ym) - 0.045 / COS_A),
            (math.degrees(ALPHA), 0, 0), wd, parent=root)
    # fascia along the eave, barge boards up both sides
    kit.box("fascia", (2 * ROOF_HALF + 0.06, 0.035, 0.17), (0, EAVE_Y + 0.005, Z_EAVE - 0.10), mat=wo,
            bevel=0.006, parent=root)
    for sx in (-1, 1):
        kit.beam(f"barge_{sx}", (sx * (ROOF_HALF + 0.03), EAVE_Y, Z_EAVE - 0.07),
                 (sx * (ROOF_HALF + 0.03), WALL_Y, Z_WALL - 0.07), (0.035, 0.19), wo, bevel=0.006,
                 parent=root)


# ---- roof covering -------------------------------------------------------------------------

def _roof(kit, mats, rng, root):
    F = sm.frame((0, EAVE_Y, Z_EAVE), (1, 0, 0), (0, COS_A, SIN_A), (0, -SIN_A, COS_A))
    exposure, length = 0.21, 0.42
    courses = int(math.ceil((SLOPE_LEN - 0.1) / exposure))
    parts = {}
    for i in range(courses):
        s = i * exposure
        x = -ROOF_HALF - 0.03 + rng.uniform(0, 0.1)
        while x < ROOF_HALF + 0.03:
            w, gap = rng.uniform(0.09, 0.16), rng.uniform(0.003, 0.012)
            cx = x + w / 2
            x += w + gap
            if rng.random() < 0.02:
                continue
            if HOLE[0][0] < cx < HOLE[0][1] and HOLE[1][0] < s + exposure < HOLE[1][1]:
                continue
            slip = rng.uniform(0.05, 0.12) if rng.random() < 0.05 else 0.0
            ln = min(length * rng.uniform(0.92, 1.0), SLOPE_LEN - s + 0.03)
            t = rng.uniform(0.014, 0.026)
            n = -t / 2 + 0.004 * i + rng.uniform(-0.003, 0.003)
            rot = (rng.uniform(-2.5, 2.5) + (4.0 if slip else 0.0), rng.uniform(-2.0, 2.0),
                   rng.uniform(-2.5, 2.5))
            key = (i, "wood_dark" if rng.random() < 0.18 else "wood_old")
            parts.setdefault(key, sm.Mesh()).box((w, ln, t), (cx, s - slip + ln / 2, n), rot, F)
    for (i, mk), m in sorted(parts.items()):
        m.finish(f"shingles_{i}_{mk}", mats[mk], root)

    # moss cushions: thick on the wet eave side, a few higher up
    moss = sm.Mesh()
    for _ in range(11):
        s = rng.uniform(0.05, 0.9) if rng.random() < 0.7 else rng.uniform(0.9, 2.6)
        moss.dome((rng.uniform(-1.9, 1.9), s, 0.005), (rng.uniform(0.08, 0.2), rng.uniform(0.06, 0.13),
                                                       rng.uniform(0.02, 0.04)), rng, xform=F)
    moss.finish("roof_moss", mats["moss"], root)

    # burlap patch pinned with three stones
    cx, cs = -1.05, 2.05
    sm_t = sm.Mesh()
    sm_t.box((0.85, 0.62, 0.018), (cx, cs, 0.045), (1.5, 0.0, 6.0), F)
    sm_t.finish("roof_patch", mats["burlap"], root)
    stones = sm.Mesh()
    for dx, ds in ((-0.3, -0.2), (0.28, -0.15), (0.0, 0.24)):
        sz = rng.uniform(0.1, 0.16)
        stones.box((sz, sz * 0.85, sz * 0.6), (cx + dx, cs + ds, 0.07 + sz * 0.3),
                   (rng.uniform(-10, 10), rng.uniform(-10, 10), rng.uniform(0, 90)), F)
    stones.finish("roof_patch_stones", mats["stone_wall"], root, bevel=0.02)


# ---- end walls and partition -----------------------------------------------------------------

def _end_walls(kit, mats, rng, root):
    wo = mats["wood_old"]
    for end, sx in (("n", -1), ("s", 1)):
        x = sx * 1.92
        for k in range(16):
            z0 = 0.06 + k * 0.205 + rng.uniform(-0.004, 0.004)
            z_top = z0 + 0.2
            if z_top > under_z(WALL_Y - 0.1):
                continue
            if rng.random() < (0.10 if end == "n" else 0.05) and k > 1:
                continue                                  # board gone
            y0 = FRONT_Y - 0.02 if z_top <= under_z(FRONT_Y) else (z_top + UNDER - Z_EAVE) / SLOPE + EAVE_Y
            y1 = WALL_Y - 0.1
            if rng.random() < 0.12 and k > 2:
                y0 += rng.uniform(0.3, 0.9)               # rotted off at the front end
            if y1 - y0 < 0.2:
                continue
            kit.beam(f"end_{end}_{k}", (x + rng.uniform(-0.006, 0.006), y0, z0 + 0.1),
                     (x + rng.uniform(-0.006, 0.006), y1, z0 + 0.1 + rng.uniform(-0.004, 0.004)),
                     (rng.uniform(0.026, 0.034), 0.2), wo, bevel=0.006, parent=root)


def _partition(kit, mats, rng, root):
    wo = mats["wood_old"]
    x = 0.0
    for k in range(5):
        z = 0.13 + k * 0.235
        y0, y1 = FRONT_Y + 0.06, WALL_Y - 0.17
        if k == 2:
            # a board the horses kicked loose: hangs from the rear post, front end down
            kit.beam(f"part_{k}", (x + 0.03, y1, z + 0.1), (x + 0.02, y0 + 1.1, z - 0.18), (0.04, 0.21), wo,
                     bevel=0.006, parent=root)
            continue
        kit.beam(f"part_{k}", (x + rng.uniform(-0.01, 0.01), y0, z), (x + rng.uniform(-0.01, 0.01), y1, z),
                 (0.045, 0.215), wo, bevel=0.006, parent=root)
    # open bars above the planks at the head end
    for k, z in enumerate((1.60, 1.95)):
        kit.cylinder(f"bar_{k}", 0.04, 1.2, (x, WALL_Y - 0.17 - 0.6 + 0.0, z), (90, 0, 0), wo, segments=8,
                     parent=root)


# ---- stalls --------------------------------------------------------------------------------

def _hay(kit, mats, rng, root, name, x, y, z, r, strands=90):
    """Heap of hay: a dark core wrapped in loose stalks that point every which way."""
    kit.sphere(f"{name}_core", r * 0.8, (x, y, z), scale=(1.15, 0.7, 0.6), mat=mats["straw"], segments=10,
               parent=root)
    m = sm.Mesh()
    for _ in range(strands):
        while True:
            px, py, pz = rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)
            if px * px + py * py + pz * pz <= 1.0:
                break
        m.box((0.011, 0.011, rng.uniform(0.2, 0.42)), (x + px * r * 1.1, y + py * r * 0.7, z + pz * r * 0.6),
              (rng.uniform(-75, 75), rng.uniform(-75, 75), rng.uniform(0, 180)))
    # stalks trailing out below the heap
    for _ in range(14):
        a = rng.uniform(0, 2 * math.pi)
        m.box((0.011, 0.011, rng.uniform(0.2, 0.4)), (x + math.cos(a) * r * 0.85, y + math.sin(a) * r * 0.5,
                                                    z - r * 0.5 - rng.uniform(0.0, 0.14)),
              (rng.uniform(-12, 12), rng.uniform(-12, 12), rng.uniform(0, 180)))
    m.finish(f"{name}_stalks", mats["straw"], root)


def _stall_fittings(kit, mats, rng, root, i, xs):
    wo, wd, iron, rope = mats["wood_old"], mats["wood_dark"], mats["iron"], mats["rope"]
    # manger against the wall, on two legs
    yb = WALL_Y - 0.24
    kit.box(f"manger_floor_{i}", (0.98, 0.40, 0.035), (xs, yb, 0.80), mat=wo, bevel=0.005, parent=root)
    kit.box(f"manger_front_{i}", (0.98, 0.035, 0.22), (xs, yb - 0.2, 0.90), mat=wo, bevel=0.005, parent=root)
    for sx in (-1, 1):
        kit.box(f"manger_side_{i}_{sx}", (0.035, 0.40, 0.22), (xs + sx * 0.475, yb, 0.90), mat=wo,
                bevel=0.005, parent=root)
        _post(kit, mats, rng, root, f"manger_leg_{i}_{sx}", xs + sx * 0.44, yb - 0.17, 0.0, 0.80, 0.07, wd)
    _hay(kit, mats, rng, root, f"manger_hay_{i}", xs, yb, 1.0, 0.27)

    # hay rack above: two cheeks, rails and slats, tilted toward the wall
    y0, z0, y1, z1 = 1.10, 1.50, WALL_Y - 0.08, 2.15
    for sx in (-1, 1):
        kit.beam(f"rack_cheek_{i}_{sx}", (xs + sx * 0.52, y0, z0), (xs + sx * 0.52, y1, z1), (0.045, 0.12), wo,
                 bevel=0.005, parent=root)
    kit.beam(f"rack_bottom_{i}", (xs - 0.52, y0, z0 + 0.03), (xs + 0.52, y0, z0 + 0.03), (0.04, 0.07), wo,
             parent=root)
    kit.beam(f"rack_top_{i}", (xs - 0.52, y1, z1), (xs + 0.52, y1, z1), (0.04, 0.07), wo, parent=root)
    for k in range(9):
        x = xs - 0.46 + k * 0.115
        kit.beam(f"slat_{i}_{k}", (x, y0 + 0.01, z0 + 0.02), (x + rng.uniform(-0.006, 0.006), y1 - 0.01, z1 - 0.03),
                 (0.028, 0.028), wo, parent=root)
    _hay(kit, mats, rng, root, f"rack_hay_{i}", xs, 1.28, 1.85, 0.28)

    # tie ring in the wall and a rope hanging from it
    kit.torus(f"ring_{i}", 0.035, 0.007, (xs - 0.62, WALL_Y - 0.015, 1.15), (90, 0, 0), iron,
              major_segments=12, minor_segments=4, parent=root)
    _sweep.rope(kit, f"tie_rope_{i}", [(xs - 0.62, WALL_Y - 0.04, 1.12), (xs - 0.64, WALL_Y - 0.12, 0.92),
                                      (xs - 0.55, WALL_Y - 0.2, 0.66), (xs - 0.5, WALL_Y - 0.3, 0.7)],
                0.013, rope, root, lay=0.08)


def _horse(kit, mats, rng, root, xs):
    """Dark horse in the stall, facing the wall with its head down in the manger."""
    coat, iron = mats["feather"], mats["iron"]
    sw = _sweep.sweep
    lo = -0.13                  # the body is lowered by this much against the leg length
    # barrel, withers and neck as one smooth tube; the rump is a separate round form
    sw(kit, "horse_body", [(xs, -0.80, 1.16 + lo), (xs, -0.52, 1.24 + lo), (xs, -0.10, 1.17 + lo),
                           (xs, 0.35, 1.20 + lo), (xs, 0.58, 1.36 + lo), (xs, 0.74, 1.52 + lo),
                           (xs, 0.84, 1.58 + lo)],
       [0.12, 0.32, 0.32, 0.30, 0.19, 0.13, 0.10], [0.14, 0.37, 0.37, 0.36, 0.24, 0.17, 0.12],
       coat, root, sides=16, step=0.03)
    _sweep.smooth(kit.sphere("horse_rump", 0.33, (xs, -0.60, 1.2 + lo), scale=(0.97, 1.0, 1.08), mat=coat,
                             segments=18, parent=root))
    sw(kit, "horse_head", [(xs, 0.84, 1.58 + lo), (xs, 0.97, 1.40 + lo), (xs, 1.07, 1.2 + lo)], [0.10, 0.085, 0.05],
       [0.115, 0.10, 0.055], coat, root, sides=10, step=0.03)
    _sweep.smooth(kit.sphere("horse_muzzle", 0.058, (xs, 1.075, 1.18 + lo), scale=(1.0, 1.0, 1.1), mat=coat,
                             segments=10, parent=root))
    for sx in (-1, 1):
        kit.cylinder(f"horse_ear_{sx}", 0.028, 0.13, (xs + sx * 0.055, 0.84, 1.69 + lo), (-12, sx * 8, 0), coat,
                     segments=6, radius_top=0.008, parent=root)
    for k in range(9):
        t = k / 8
        kit.box(f"horse_mane_{k}", (0.02, 0.09, 0.14), (xs + 0.03, 0.55 + 0.29 * t, 1.5 + 0.1 * t + lo),
                (rng.uniform(-10, 10), 0, 18), coat, parent=root)
    # legs: forelegs straight, hind legs with the hock bent back
    for sx in (-0.13, 0.13):
        sw(kit, "horse_foreleg", [(xs + sx, 0.38, 0.98), (xs + sx, 0.40, 0.62), (xs + sx, 0.40, 0.5),
                                  (xs + sx, 0.42, 0.12), (xs + sx, 0.43, 0.02)],
           [0.085, 0.06, 0.048, 0.036, 0.042], [0.09, 0.065, 0.05, 0.038, 0.044], coat, root, sides=8, step=0.03)
        kit.cylinder("horse_fore_hoof", 0.05, 0.07, (xs + sx, 0.43, 0.035), mat=iron, segments=8, radius_top=0.044,
                     parent=root)
        hx = xs + sx * 1.1
        sw(kit, "horse_hindleg", [(hx, -0.6, 1.0), (hx, -0.72, 0.7), (hx, -0.80, 0.5), (hx, -0.72, 0.14),
                                  (hx, -0.70, 0.02)],
           [0.13, 0.085, 0.052, 0.036, 0.042], [0.14, 0.095, 0.056, 0.038, 0.044], coat, root, sides=8, step=0.03)
        kit.cylinder("horse_hind_hoof", 0.05, 0.07, (hx, -0.70, 0.035), mat=iron, segments=8, radius_top=0.044,
                     parent=root)
    sw(kit, "horse_tail", [(xs, -0.88, 1.28), (xs, -0.99, 1.0), (xs, -1.02, 0.7), (xs, -0.99, 0.36)],
       [0.045, 0.07, 0.07, 0.04], [0.045, 0.07, 0.07, 0.04], coat, root, sides=8, step=0.03)


def _bedding(kit, mats, rng, root):
    for i, (x, y, sx, sy) in enumerate(((-0.9, -0.2, 0.95, 1.5), (0.9, -0.1, 0.95, 1.5),
                                        (-0.5, -1.55, 0.9, 0.8), (1.15, -1.7, 0.8, 0.7),
                                        (-0.05, 0.75, 0.9, 1.0))):
        pile = straw_pile.build(kit, mats, rng)
        pile.parent = root
        pile.location = (x, y, 0.0)
        pile.rotation_euler = (0, 0, rng.uniform(0, math.pi))
        pile.scale = (sx, sy, 1.0)


# ---- outside -------------------------------------------------------------------------------

def _hitching_rail(kit, mats, rng, root):
    wd, wo, rope = mats["wood_dark"], mats["wood_old"], mats["rope"]
    y = -2.35
    for i, x in enumerate((-1.05, 1.05)):
        _post(kit, mats, rng, root, f"hitch_post_{i}", x, y, 0.0, 1.2, 0.11, wd, lean=0.02)
        kit.box(f"hitch_foot_{i}", (0.34, 0.3, 0.07), (x, y, 0.02), (0, 0, rng.uniform(-20, 20)),
                mats["mud"], parent=root)
    kit.cylinder("hitch_rail", 0.045, 2.5, (0, y - 0.02, 1.02), (0, 90, 0), wo, segments=8, bevel=0.004,
                 parent=root)
    for i, x in enumerate((-1.05, 1.05)):
        kit.torus(f"hitch_lash_{i}", 0.065, 0.011, (x, y - 0.02, 1.02), (0, 90, 0), rope, major_segments=10,
                  minor_segments=4, parent=root)
    # lead rope: tied round the rail, trailing on the ground
    _sweep.rope(kit, "lead_rope", [(0.25, y - 0.06, 1.05), (0.3, y - 0.14, 0.9), (0.22, y - 0.2, 0.55),
                                  (0.32, y - 0.45, 0.2), (0.7, y - 0.55, 0.04), (0.95, y - 0.4, 0.03)],
                0.014, rope, root, lay=0.09)
    kit.torus("lead_knot", 0.05, 0.016, (0.25, y - 0.05, 1.02), (0, 90, 0), rope, major_segments=10,
              minor_segments=4, parent=root)
    b = bucket.build(kit, mats, rng, bail_deg=60)
    b.parent = root
    b.location = (-0.45, y - 0.55, 0.0)
    b.rotation_euler = (0, 0, rng.uniform(0, 6.2))


def _pitchfork(kit, mats, rng, root):
    wo, iron = mats["wood_old"], mats["iron"]
    x, y = -2.12, -1.58
    kit.beam("fork_shaft", (x - 0.03, y - 0.45, 0.02), (x, y, 1.68), (0.034, 0.034), wo, bevel=0.004, parent=root)
    top = (x, y, 1.68)
    for k, dx in enumerate((-0.07, 0.0, 0.07)):
        kit.beam(f"fork_tine_{k}", (top[0] + dx, top[1] + 0.0, top[2] - 0.12), (top[0] + dx * 1.2, top[1] + 0.03, top[2] + 0.2),
                 (0.012, 0.012), iron, parent=root)
    kit.beam("fork_neck", (top[0] - 0.07, top[1], top[2] - 0.12), (top[0] + 0.07, top[1], top[2] - 0.12),
             (0.014, 0.014), iron, parent=root)


def _breast_bar(kit, mats, rng, root):
    """Breast bar of the south stall in its notches; the north one has fallen out."""
    wo = mats["wood_old"]
    kit.cylinder("bar_in", 0.04, 1.68, (0.9, FRONT_Y - 0.13, 0.98), (0, 90, 0), wo, segments=8, parent=root)
    kit.cylinder("bar_fallen", 0.04, 1.6, (-1.1, -1.95, 0.16), (80, 86, 20), wo, segments=8, parent=root)


def _saddle(kit, mats, rng, root):
    """Saddle on a folded blanket, hung over the partition near its front end."""
    leather, burlap, iron, rope = mats["door_wood"], mats["burlap"], mats["iron"], mats["rope"]
    top = 1.36
    y = -0.55
    kit.box("blanket", (0.5, 0.62, 0.025), (0.0, y, top + 0.04), (0, 0, 0), burlap, parent=root)
    for sx in (-1, 1):
        kit.box(f"blanket_hang_{sx}", (0.025, 0.62, 0.30), (sx * 0.255, y, top - 0.12), (0, 0, sx * 4), burlap,
                parent=root)
        kit.box(f"flap_{sx}", (0.025, 0.46, 0.34), (sx * 0.2, y, top - 0.13), (0, 0, sx * 3), leather, bevel=0.005,
                parent=root)
    kit.box("seat", (0.3, 0.42, 0.045), (0.0, y, top + 0.085), (0, 0, 0), leather, bevel=0.012, parent=root)
    kit.box("pommel", (0.07, 0.07, 0.11), (0.0, y - 0.21, top + 0.15), (8, 0, 0), leather, bevel=0.012, parent=root)
    kit.box("cantle", (0.30, 0.07, 0.1), (0.0, y + 0.22, top + 0.14), (-8, 0, 0), leather, bevel=0.012, parent=root)
    for sx in (-1, 1):
        kit.box(f"leather_{sx}", (0.022, 0.035, 0.34), (sx * 0.24, y - 0.04, top - 0.34), (0, 0, 0), leather,
                parent=root)
        kit.torus(f"stirrup_{sx}", 0.055, 0.01, (sx * 0.24, y - 0.04, top - 0.58), (0, 90, 0), iron,
                  major_segments=12, minor_segments=4, parent=root)


def _bridle(kit, mats, rng, root):
    """Bridle on a peg of the rear post of the north stall."""
    iron, rope = mats["iron"], mats["rope"]
    x, y = -1.8, WALL_Y - 0.11
    kit.cylinder("peg", 0.015, 0.14, (x + 0.1, y - 0.04, 1.55), (0, 90, 0), iron, segments=8, parent=root)
    _sweep.rope(kit, "bridle_strap", [(x + 0.16, y - 0.04, 1.56), (x + 0.2, y - 0.1, 1.36),
                                      (x + 0.15, y - 0.16, 1.14), (x + 0.1, y - 0.12, 1.08)],
                0.01, rope, root, lay=0.07)
    kit.torus("bit", 0.04, 0.007, (x + 0.1, y - 0.12, 1.06), (90, 0, 0), iron, major_segments=12,
              minor_segments=4, parent=root)


def _litter(kit, mats, rng, root):
    """A broken board and a few stones round the front of the stable."""
    wo, stone = mats["wood_old"], mats["stone_wall"]
    kit.beam("board_scrap", (0.9, -2.15, 0.03), (1.65, -2.45, 0.025), (0.17, 0.025), wo, bevel=0.004,
             parent=root)
    kit.beam("board_scrap_2", (-1.8, -2.55, 0.025), (-1.3, -2.3, 0.04), (0.14, 0.025), wo, parent=root)
    for i in range(6):
        s = rng.uniform(0.08, 0.17)
        kit.box(f"stone_{i}", (s, s * 0.8, s * 0.6), (rng.uniform(-2.0, 2.0), rng.uniform(-2.9, -1.9), s * 0.25),
                (rng.uniform(-10, 10), rng.uniform(-10, 10), rng.uniform(0, 90)), stone, bevel=0.02, parent=root)


# ---- hay loft and feed ----------------------------------------------------------------------

LOFT_Y = 0.25                   # loft beam, 1.25 m out from the wall
LOFT_FLOOR = 2.44               # top of the loft boards
LOFT_SLOT = 1.22                # boards stop here; the rest up to the wall is the hay drop


def _loft(kit, mats, rng, root):
    wd, wo = mats["wood_dark"], mats["wood_old"]
    joist_top = LOFT_FLOOR - 0.025
    beam_top = joist_top - 0.12
    kit.box("loft_beam", (3.78, 0.14, 0.16), (0, LOFT_Y, beam_top - 0.08), mat=wd, bevel=0.01, parent=root)
    for i, x in enumerate((-1.84, 0.0, 1.84)):
        _post(kit, mats, rng, root, f"loft_post_{i}", x, LOFT_Y, 0.0, beam_top - 0.16, 0.13, wd, lean=0.006)
    kit.box("loft_ledger", (3.78, 0.06, 0.14), (0, WALL_Y - 0.03, beam_top + 0.02), mat=wd, parent=root)
    for i in range(8):
        x = -1.8 + 3.6 * i / 7
        kit.beam(f"loft_joist_{i}", (x, LOFT_Y - 0.1, beam_top + 0.06), (x, WALL_Y - 0.06, beam_top + 0.06),
                 (0.07, 0.12), wo, bevel=0.005, parent=root)
    boards = {"wood_old": sm.Mesh(), "wood_dark": sm.Mesh()}
    y = LOFT_Y - 0.12
    while y < LOFT_SLOT - 0.05:
        w = min(rng.uniform(0.18, 0.26), LOFT_SLOT - y)
        boards["wood_dark" if rng.random() < 0.2 else "wood_old"].box(
            (3.75 + rng.uniform(-0.06, 0.02), w - 0.008, 0.025),
            (rng.uniform(-0.02, 0.02), y + w / 2, LOFT_FLOOR - 0.0125), (0, 0, rng.uniform(-0.5, 0.5)))
        y += w + rng.uniform(0.0, 0.02)
    for key, m in boards.items():
        m.finish(f"loft_boards_{key}", mats[key], root)

    # hay stacked on the loft: lumpy loaves under the rafters, stalks over the front edge and
    # down the drop slot into the racks
    core = sm.Mesh()
    for i, x in enumerate((-1.45, -0.75, 0.0, 0.75, 1.45)):
        core.dome((x + rng.uniform(-0.08, 0.08), 0.78 + rng.uniform(-0.05, 0.05), LOFT_FLOOR),
                  (0.46, 0.52, rng.uniform(0.34, 0.42)), rng, jitter=0.15)
    core.finish("loft_hay_core", mats["straw"], root)
    stalks = sm.Mesh()
    for _ in range(260):
        x = rng.uniform(-1.8, 1.8)
        yy = rng.uniform(0.3, 1.25)
        z = LOFT_FLOOR + rng.uniform(0.05, 0.36) * (1.0 - abs(yy - 0.78) * 0.9)
        stalks.box((0.011, 0.011, rng.uniform(0.18, 0.4)), (x, yy, z),
                   (rng.uniform(-80, 80), rng.uniform(-80, 80), rng.uniform(0, 180)))
    for _ in range(70):
        x = rng.uniform(-1.8, 1.8)
        stalks.box((0.011, 0.011, rng.uniform(0.15, 0.32)), (x, LOFT_Y - 0.14 + rng.uniform(-0.03, 0.02),
                                                           LOFT_FLOOR - rng.uniform(0.02, 0.12)),
                   (rng.uniform(-25, 25), rng.uniform(-25, 25), rng.uniform(0, 180)))
    for xs in STALL_X:
        for _ in range(30):
            stalks.box((0.011, 0.011, rng.uniform(0.2, 0.4)),
                       (xs + rng.uniform(-0.45, 0.45), rng.uniform(LOFT_SLOT + 0.02, WALL_Y - 0.08),
                        LOFT_FLOOR - rng.uniform(0.0, 0.25)),
                       (rng.uniform(-30, 30), rng.uniform(-30, 30), rng.uniform(0, 180)))
    stalks.finish("loft_hay_stalks", mats["straw"], root)


def _oat_bin(kit, mats, rng, root):
    """Lidded plank chest for oats at the tail end of the north stall, against the end wall."""
    wo, wd, iron, stone = mats["wood_old"], mats["wood_dark"], mats["iron"], mats["stone_wall"]
    cx, cy = -1.60, -0.72
    sx, sy, h = 0.50, 0.95, 0.62
    for i, (dx, dy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        kit.beam(f"bin_stile_{i}", (cx + dx * (sx / 2 - 0.03), cy + dy * (sy / 2 - 0.03), 0.0),
                 (cx + dx * (sx / 2 - 0.03), cy + dy * (sy / 2 - 0.03), h - 0.03), (0.055, 0.055), wd, parent=root)
    for k in range(3):
        z = 0.06 + k * 0.19 + 0.09
        kit.box(f"bin_front_{k}", (0.025, sy, 0.185), (cx + sx / 2, cy, z), mat=wo, bevel=0.004, parent=root)
        kit.box(f"bin_back_{k}", (0.025, sy, 0.185), (cx - sx / 2, cy, z), mat=wo, bevel=0.004, parent=root)
        for e in (-1, 1):
            kit.box(f"bin_end_{k}_{e}", (sx, 0.025, 0.185), (cx, cy + e * sy / 2, z), mat=wo, bevel=0.004,
                    parent=root)
    # lid: two boards on battens, hinged at the back, a hasp at the front
    for k, dy in enumerate((-0.24, 0.24)):
        kit.box(f"bin_lid_{k}", (sx + 0.05, 0.47, 0.03), (cx, cy + dy, h + 0.015), (0, 0, rng.uniform(-1, 1)),
                wd if k else wo, bevel=0.005, parent=root)
    for k, dy in enumerate((-0.36, 0.36)):
        kit.box(f"bin_batten_{k}", (sx + 0.02, 0.06, 0.025), (cx, cy + dy, h + 0.042), mat=wo, parent=root)
    kit.box("bin_hasp", (0.012, 0.04, 0.14), (cx + sx / 2 + 0.02, cy, h - 0.05), mat=iron, parent=root)
    kit.torus("bin_staple", 0.02, 0.005, (cx + sx / 2 + 0.03, cy, h - 0.11), (0, 90, 0), iron, major_segments=8,
              minor_segments=4, parent=root)
    for k, dy in enumerate((-0.3, 0.3)):
        kit.box(f"bin_hinge_{k}", (0.12, 0.035, 0.008), (cx - sx / 2 + 0.05, cy + dy, h + 0.032), mat=iron,
                parent=root)
    s = 0.17
    kit.box("bin_stone", (s, s * 0.8, s * 0.55), (cx + 0.02, cy - 0.18, h + 0.03 + s * 0.27),
            (rng.uniform(-6, 6), rng.uniform(-6, 6), 25), stone, bevel=0.025, parent=root)
    # the measure: a wooden bowl on the lid
    kit.cylinder("bin_measure", 0.1, 0.09, (cx - 0.02, cy + 0.24, h + 0.075), mat=wo, segments=12,
                 radius_top=0.12, bevel=0.005, parent=root)


def _tracked_out(kit, mats, rng, root):
    """Mud apron trodden out of the stalls, hoof prints in it, and straw dropped toward the muck heap."""
    mud = sm.Mesh()
    for i in range(9):
        x = rng.uniform(-1.6, 1.8)
        y = rng.uniform(-2.3, -1.45)
        mud.dome((x, y, -0.01), (rng.uniform(0.35, 0.6), rng.uniform(0.25, 0.4), 0.025), rng, jitter=0.3)
    # along the barrow run to the heap: local +X is south, the heap is beyond the south end
    for i in range(6):
        t = i / 5
        mud.dome((1.3 + 1.3 * t + rng.uniform(-0.1, 0.1), -2.0 - 0.1 * t + rng.uniform(-0.15, 0.15), -0.01),
                 (rng.uniform(0.22, 0.34), rng.uniform(0.18, 0.26), 0.02), rng, jitter=0.3)
    mud.finish("trodden_mud", mats["mud"], root, smooth=True)
    prints = sm.Mesh()
    for i in range(14):
        x, y = rng.uniform(-1.3, 1.5), rng.uniform(-2.6, -1.5)
        prints.box((0.11, 0.13, 0.008), (x, y, 0.016), (0, 0, rng.uniform(0, 180)))
    prints.finish("hoof_prints", mats["feather"], root)
    straw = sm.Mesh()
    for _ in range(120):
        t = rng.random()
        if rng.random() < 0.55:
            x, y = 0.9 + 1.8 * t + rng.uniform(-0.2, 0.2), -2.0 + rng.uniform(-0.3, 0.3)
        else:
            x, y = rng.uniform(-1.6, 1.8), rng.uniform(-2.6, -1.4)
        straw.box((0.012, rng.uniform(0.12, 0.3), 0.005), (x, y, 0.02 + rng.uniform(0, 0.012)),
                  (rng.uniform(-6, 6), rng.uniform(-6, 6), rng.uniform(0, 180)))
    straw.finish("dropped_straw", mats["straw"], root)


def build(kit, mats, rng):
    root = kit.group("stable")
    _frame(kit, mats, rng, root)
    _roof(kit, mats, rng, root)
    _end_walls(kit, mats, rng, root)
    _partition(kit, mats, rng, root)
    for i, xs in enumerate(STALL_X):
        _stall_fittings(kit, mats, rng, root, i, xs)
    _horse(kit, mats, rng, root, STALL_X[1])
    _bedding(kit, mats, rng, root)
    _hitching_rail(kit, mats, rng, root)
    _pitchfork(kit, mats, rng, root)
    _breast_bar(kit, mats, rng, root)
    _saddle(kit, mats, rng, root)
    _bridle(kit, mats, rng, root)
    _litter(kit, mats, rng, root)
    _loft(kit, mats, rng, root)
    _oat_bin(kit, mats, rng, root)
    _tracked_out(kit, mats, rng, root)
    return root

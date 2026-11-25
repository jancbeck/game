"""Gate guard's watch shelter: a timber lean-to against the gatehouse, with the gate bell above it.

Footprint 2.2 m wide (X) and 1.7 m deep (Y). The back (+Y, local y = 0.85) stands against the wall
face; the root sits 0.85 m out from it. The front (-Y) is open, the west side (-X) has only a
knee-high board screen, so a guard on the bench along the boarded east side looks straight out
west at the gate arch, and the fire basket out in the open in front of him.

Frame: two back posts against the wall carry a ledger at 2.85-3.0 m, two front posts on stone
pads carry a plate at about 2.1 m, with knee braces. Four rafters run from the ledger over the
plate to an eave 2.0 m above the floor, so a 1.8 m man stands under it. The roof is boards laid
down the slope, of uneven width, with battens over a few open joints and an iron flashing strip against the wall. It is
decades old: grey weathered boards, two newer replacements, moss along the eave, ragged board
ends, a split board on the east side held by a nailed-on batten.

Inside: the bench (seat at 0.45 m) on the east side, a duckboard in front of it so the guard's
feet stay out of the mud, the guard's wool cloak and belt on a peg board on the wall
(cloak_peg.build), a spear leaning in the back west corner and a water pail.

Gate bell: a bronze bell about 0.3 m across hangs from a forged wall bracket above the roof, just
west of the banner. Its clapper rope runs down through a grommeted hole in the roof boards and ends in
a knot at shoulder height, an arm's length from the bench.

Nothing here burns and nothing here lights.
"""

import math

import bpy

from . import bucket, cloak_peg

LIGHTS = []

HALF_W = 1.1            # half the width along X
BACK_Y = 0.85           # wall face
POST_X = 1.0            # posts at +-POST_X
FRONT_Y = -0.62         # front posts
EAVE_Y = -0.95          # roof boards end here
LEDGER_TOP = 3.0        # rafters bear on the ledger here, at the wall
PLATE_TOP = 2.20        # and on the front plate here
RAFTER_H = 0.12
BOARD_T = 0.025

BENCH_X, BENCH_Z = 0.82, 0.45
BELL_X, BELL_Y = 0.10, 0.30          # bell and rope: clear of the banner, rope within reach of the bench
BELL_Z = 3.50                        # mouth of the bell


def _slope():
    return (LEDGER_TOP - PLATE_TOP) / ((BACK_Y - 0.05) - FRONT_Y)


def roof_z(y):
    """Top of the roof boards at y."""
    return PLATE_TOP + RAFTER_H + BOARD_T + _slope() * (y - FRONT_Y)


def _bronze():
    mat = bpy.data.materials.get("bell_bronze")
    if mat is not None:
        return mat
    mat = bpy.data.materials.new("bell_bronze")
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 18.0
    noise.inputs["Detail"].default_value = 6.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.035, 0.045, 0.032, 1.0)    # dull green-black patina
    ramp.color_ramp.elements[1].color = (0.11, 0.075, 0.038, 1.0)     # worn bronze
    ramp.color_ramp.elements[0].position = 0.42
    ramp.color_ramp.elements[1].position = 0.62
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Metallic"].default_value = 0.75
    b.inputs["Roughness"].default_value = 0.5
    return mat


def _lathe(kit, name, profile, loc, mat, parent, segments=20):
    """Surface of revolution about Z through `profile` [(r, z), ...], closed at r = 0 ends."""
    verts, faces = [], []
    rings = []
    for r, z in profile:
        if r == 0:
            verts.append((0.0, 0.0, z))
            rings.append([len(verts) - 1])
            continue
        ring = []
        for k in range(segments):
            a = 2 * math.pi * k / segments
            verts.append((r * math.cos(a), r * math.sin(a), z))
            ring.append(len(verts) - 1)
        rings.append(ring)
    for ra, rb in zip(rings, rings[1:]):
        if len(ra) == 1:
            faces += [(ra[0], rb[(k + 1) % segments], rb[k]) for k in range(segments)]
        elif len(rb) == 1:
            faces += [(ra[k], ra[(k + 1) % segments], rb[0]) for k in range(segments)]
        else:
            faces += [(ra[k], ra[(k + 1) % segments], rb[(k + 1) % segments], rb[k]) for k in range(segments)]
    ob = kit.mesh(name, verts, faces, loc=loc, mat=mat, parent=parent)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def _frame(kit, mats, rng, root):
    wood, stone, iron = mats["wood_old"], mats["stone_wall"], mats["iron"]
    s = _slope()
    # stone pads keep the front posts and the west stud out of the wet
    for name, (x, y) in (("pad_w", (-POST_X, FRONT_Y)), ("pad_e", (POST_X, FRONT_Y)), ("pad_stud", (-POST_X, -0.05))):
        kit.box(name, (0.28 + kit.jitter(rng, 0.03), 0.26 + kit.jitter(rng, 0.03), 0.12), (x, y, 0.05),
                (0, 0, kit.jitter(rng, 8)), stone, bevel=0.02, parent=root)
    for side in (-1, 1):
        x = side * POST_X
        kit.beam(f"post_front_{side}", (x, FRONT_Y, 0.11), (x + kit.jitter(rng, 0.015), FRONT_Y, PLATE_TOP - 0.16),
                 (0.14, 0.14), wood, bevel=0.01, parent=root)
        kit.beam(f"post_back_{side}", (x, BACK_Y - 0.07, 0.0), (x, BACK_Y - 0.07, LEDGER_TOP - 0.16), (0.12, 0.12),
                 wood, bevel=0.01, parent=root)
        # knee brace from the post up to the plate
        kit.beam(f"knee_{side}", (x, FRONT_Y, PLATE_TOP - 0.62), (x - side * 0.42, FRONT_Y, PLATE_TOP - 0.17),
                 (0.08, 0.09), wood, bevel=0.006, parent=root)
        # girts on the east side carry the boards; one at the west carries the screen
        for n, z in enumerate((0.35, 1.55) if side > 0 else (0.55,)):
            kit.beam(f"girt_{side}_{n}", (x, FRONT_Y + 0.07, z), (x, BACK_Y - 0.13, z), (0.07, 0.09), wood,
                     bevel=0.005, parent=root)
    kit.beam("stud_w", (-POST_X, -0.05, 0.11), (-POST_X, -0.05, 1.02), (0.09, 0.09), wood, bevel=0.006, parent=root)
    kit.beam("plate", (-HALF_W - 0.04, FRONT_Y, PLATE_TOP - 0.08), (HALF_W + 0.04, FRONT_Y, PLATE_TOP - 0.08),
             (0.15, 0.16), wood, bevel=0.01, parent=root)
    kit.beam("ledger", (-HALF_W - 0.04, BACK_Y - 0.07, LEDGER_TOP - 0.08), (HALF_W + 0.04, BACK_Y - 0.07, LEDGER_TOP - 0.08),
             (0.12, 0.16), wood, bevel=0.01, parent=root)
    # the ledger hangs on two iron straps let into the wall joints
    for x in (-0.55, 0.55):
        kit.box(f"ledger_strap_{x:+.1f}", (0.05, 0.16, 0.012), (x, BACK_Y - 0.08, LEDGER_TOP + 0.005), mat=iron,
                parent=root)
    # rafters from the ledger over the plate to the eave, tails cut unevenly
    for i, x in enumerate((-1.05, -0.35, 0.35, 1.05)):
        y1 = EAVE_Y + 0.04 + kit.jitter(rng, 0.03)
        z = lambda y: PLATE_TOP + RAFTER_H / 2 + s * (y - FRONT_Y)
        kit.beam(f"rafter_{i}", (x, BACK_Y - 0.02, z(BACK_Y - 0.02)), (x, y1, z(y1)), (0.075, RAFTER_H), wood,
                 bevel=0.006, parent=root)


def _roof(kit, mats, rng, root):
    wood, new_wood, iron, moss = mats["wood_old"], mats["door_wood"], mats["iron"], mats["moss"]
    s = _slope()
    tilt = math.degrees(math.atan(s))
    x, i = -HALF_W - 0.05, 0
    while x < HALF_W + 0.05:
        w = rng.uniform(0.15, 0.31)
        cx = x + w / 2
        y1 = EAVE_Y - rng.uniform(-0.03, 0.08)
        y0 = BACK_Y - 0.01
        zc = lambda y: roof_z(y) - BOARD_T / 2
        mat = new_wood if i in (3, 8) else wood
        kit.beam(f"board_{i}", (cx, y0, zc(y0)), (cx, y1, zc(y1)), (w - 0.006, BOARD_T), mat, bevel=0.003,
                 roll_deg=kit.jitter(rng, 3.0), parent=root)
        if i % 3 == 1 and x + w < HALF_W:      # a batten over some joints, where boards have shrunk apart
            jx = x + w
            kit.beam(f"batten_{i}", (jx, y0, zc(y0) + 0.022), (jx, EAVE_Y + 0.1, zc(EAVE_Y + 0.1) + 0.022),
                     (0.045, 0.02), wood, bevel=0.003, roll_deg=kit.jitter(rng, 3.0), parent=root)
        x += w
        i += 1
    # moss creeping up from the eave, where the boards stay wet longest
    for k in range(6):
        mx = rng.uniform(-HALF_W, HALF_W)
        my = EAVE_Y + rng.uniform(0.03, 0.2)
        kit.sphere(f"moss_{k}", rng.uniform(0.05, 0.08), (mx, my, roof_z(my) + 0.012), scale=(1.8, 0.8, 0.08),
                   rot_deg=(tilt, 0, rng.uniform(0, 180)), mat=moss, segments=8, parent=root)
    # flashing: a bent iron strip over the joint between roof and wall
    kit.box("flashing", (2 * HALF_W + 0.1, 0.14, 0.012), (0, BACK_Y - 0.07, roof_z(BACK_Y - 0.07) + 0.03),
            (tilt, 0, 0), iron, parent=root)
    kit.box("flashing_up", (2 * HALF_W + 0.1, 0.012, 0.12), (0, BACK_Y - 0.008, roof_z(BACK_Y) + 0.08), mat=iron,
            parent=root)


def _sides(kit, mats, rng, root):
    wood, new_wood = mats["wood_old"], mats["door_wood"]
    x = POST_X + 0.075
    # east side: vertical boards from the front post to the wall, up under the roof
    y, i = FRONT_Y - 0.06, 0
    while y < BACK_Y - 0.02:
        w = rng.uniform(0.16, 0.24)
        w = min(w, BACK_Y - 0.01 - y)
        cy = y + w / 2
        top = roof_z(cy) - BOARD_T - RAFTER_H - 0.02
        bottom = 0.06 + rng.uniform(0.0, 0.06)        # rotted short at the foot
        kit.box(f"side_e_{i}", (0.022, w - 0.008, top - bottom), (x, cy, (top + bottom) / 2),
                (0, 0, kit.jitter(rng, 0.6)), new_wood if i == 4 else wood, bevel=0.003, parent=root)
        y += w
        i += 1
    # a split board held by a short batten nailed across it
    kit.box("side_e_mend", (0.02, 0.36, 0.07), (x + 0.02, 0.05, 1.05), (12, 0, 0), wood, bevel=0.004, parent=root)
    # west side: a knee-high screen of three planks, front corner left open toward the gate
    for n, z in enumerate((0.22, 0.47, 0.72)):
        kit.box(f"screen_w_{n}", (0.025, BACK_Y + 0.03, 0.22), (-POST_X - 0.06, (BACK_Y - 0.07) / 2, z),
                (kit.jitter(rng, 1.0), 0, 0), wood, bevel=0.003, parent=root)


def _bench_and_floor(kit, mats, rng, root):
    wood, dark = mats["wood_old"], mats["wood_dark"]
    y0, y1 = -0.45, 0.62
    kit.box("bench_seat", (0.32, y1 - y0, 0.055), (BENCH_X, (y0 + y1) / 2, BENCH_Z - 0.028), (0, 0, 0.8), wood,
            bevel=0.008, parent=root)
    for n, y in enumerate((y0 + 0.14, y1 - 0.14)):
        for side in (-1, 1):
            kit.beam(f"bench_leg_{n}_{side}", (BENCH_X + side * 0.09, y, BENCH_Z - 0.05),
                     (BENCH_X + side * 0.14, y + kit.jitter(rng, 0.02), 0.0), (0.05, 0.05), dark, bevel=0.004,
                     parent=root)
    kit.beam("bench_stretcher", (BENCH_X, y0 + 0.14, 0.18), (BENCH_X, y1 - 0.14, 0.18), (0.04, 0.05), dark,
             bevel=0.004, parent=root)
    # duckboard: slats across two bearers, sunk a little into the mud
    for side in (-1, 1):
        kit.beam(f"duck_bearer_{side}", (0.33 + side * 0.22, -0.55, 0.025), (0.33 + side * 0.22, 0.62, 0.025),
                 (0.05, 0.05), dark, bevel=0.004, parent=root)
    y, n = -0.55, 0
    while y < 0.6:
        kit.box(f"duck_slat_{n}", (0.6, 0.085, 0.022), (0.33 + kit.jitter(rng, 0.02), y + 0.04, 0.06),
                (0, kit.jitter(rng, 1.5), kit.jitter(rng, 2.5)), wood, bevel=0.003, parent=root)
        y += 0.115
        n += 1


def _kit(kit, mats, rng, root):
    """The guard's things: cloak and belt on the wall, spear in the corner, water pail."""
    peg = cloak_peg.build(kit, mats, rng)
    peg.parent = root
    peg.location = (0.05, BACK_Y, 0.0)
    # spear leaning in the back west corner, out of the rain
    wood, iron = mats["wood_old"], mats["iron"]
    foot, top = (-0.86, 0.5, 0.02), (-0.95, BACK_Y - 0.05, 2.38)
    kit.beam("spear_shaft", foot, top, (0.032, 0.032), wood, bevel=0.008, parent=root)
    d = [t - f for f, t in zip(foot, top)]
    ln = math.sqrt(sum(c * c for c in d))
    u = [c / ln for c in d]
    head0 = [t + 0.0 * c for t, c in zip(top, u)]
    tip = [t + 0.30 * c for t, c in zip(top, u)]
    kit.beam("spear_socket", [t - 0.08 * c for t, c in zip(top, u)], head0, (0.036, 0.036), iron, bevel=0.006,
             parent=root)
    blade = kit.sphere("spear_blade", 0.15, [(a + b) / 2 for a, b in zip(head0, tip)], scale=(0.17, 0.05, 1.0),
                       mat=iron, segments=10, parent=root)
    blade.rotation_mode = "QUATERNION"
    from mathutils import Vector
    blade.rotation_quaternion = Vector(u).to_track_quat("Z", "Y")
    kit.cylinder("spear_butt", 0.02, 0.07, (foot[0] - 0.03 * u[0], foot[1] - 0.03 * u[1], 0.04), mat=iron,
                 segments=8, radius_top=0.017, parent=root)
    # water pail by the front of the shelter, for the fire and the guard
    pail = bucket.build(kit, mats, rng)
    pail.parent = root
    pail.location = (-0.35, -0.38, 0.0)
    pail.rotation_euler = (0, 0, math.radians(rng.uniform(0, 360)))


def _bell(kit, mats, rng, root):
    """Forged wall bracket above the roof, the bell hung from it and its rope down to the bench."""
    iron, rope = mats["iron"], mats["rope"]
    x, wall = BELL_X, BACK_Y
    arm_z = BELL_Z + 0.42
    kit.box("bell_plate", (0.10, 0.025, 0.62), (x, wall - 0.012, arm_z - 0.24), mat=iron, bevel=0.004, parent=root)
    kit.beam("bell_arm", (x, wall - 0.02, arm_z), (x, BELL_Y - 0.06, arm_z), (0.04, 0.04), iron, bevel=0.004,
             parent=root)
    kit.beam("bell_stay", (x, wall - 0.02, arm_z - 0.5), (x, BELL_Y + 0.14, arm_z - 0.01), (0.03, 0.03), iron,
             bevel=0.003, parent=root)
    kit.sphere("bell_arm_end", 0.03, (x, BELL_Y - 0.07, arm_z), mat=iron, segments=8, parent=root)
    # strap hanger and the bell's crown loop
    kit.box("bell_hanger", (0.03, 0.012, 0.12), (x, BELL_Y, arm_z - 0.07), mat=iron, parent=root)
    kit.torus("bell_crown", 0.035, 0.011, (x, BELL_Y, BELL_Z + 0.31), rot_deg=(90, 0, 90), mat=_bronze(),
              major_segments=12, minor_segments=5, parent=root)
    profile = [(0.155, 0.0), (0.150, 0.025), (0.128, 0.06), (0.104, 0.12), (0.094, 0.18), (0.088, 0.23),
               (0.072, 0.272), (0.04, 0.285), (0.0, 0.288)]
    bell = _lathe(kit, "bell", profile, (x, BELL_Y, BELL_Z), _bronze(), root)
    kit.solidify(bell, 0.014)
    bell.rotation_euler = (math.radians(kit.jitter(rng, 2.0)), math.radians(kit.jitter(rng, 2.0)), 0)
    # clapper hanging just out of the mouth, and the rope tied to it
    kit.beam("bell_clapper_rod", (x, BELL_Y, BELL_Z + 0.26), (x, BELL_Y, BELL_Z - 0.02), (0.014, 0.014), iron,
             parent=root)
    kit.sphere("bell_clapper", 0.032, (x, BELL_Y, BELL_Z + 0.02), scale=(1, 1, 1.3), mat=iron, segments=10,
               parent=root)
    rz = roof_z(BELL_Y)
    kit.cylinder("bell_rope_up", 0.008, BELL_Z - 0.05 - rz, (x, BELL_Y, (BELL_Z - 0.05 + rz) / 2), mat=rope,
                 segments=6, parent=root)
    # the rope runs through a hole in the boards, lined with a ring of hide against chafing
    kit.torus("rope_grommet", 0.03, 0.012, (x, BELL_Y, rz + 0.005), rot_deg=(math.degrees(math.atan(_slope())), 0, 0),
              mat=mats["burlap"], major_segments=12, minor_segments=5, parent=root)
    low = 1.05
    kit.cylinder("bell_rope", 0.009, rz - low, (x, BELL_Y + 0.01, (rz + low) / 2), rot_deg=(0.6, 0, 0), mat=rope,
                 segments=6, parent=root)
    kit.sphere("bell_rope_knot", 0.026, (x, BELL_Y + 0.015, low - 0.01), scale=(1, 1, 1.4), mat=rope, segments=8,
               parent=root)


def build(kit, mats, rng):
    root = kit.group("watch_shelter")
    _frame(kit, mats, rng, root)
    _roof(kit, mats, rng, root)
    _sides(kit, mats, rng, root)
    _bench_and_floor(kit, mats, rng, root)
    _kit(kit, mats, rng, root)
    _bell(kit, mats, rng, root)
    return root

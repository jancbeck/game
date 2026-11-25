"""Gallows: a boarded timber scaffold with two posts, a crossbeam and a noose.

Footprint: deck 3.4 m (x) by 2.4 m (y), top at z = 1.6. The beam runs along X and the front
faces -Y, toward the camera. A seven-step stair leaves the -X end and descends 1.75 m to the
west, with one handrail on its back side, so that seen from the front it crosses neither the
platform nor the frame.

The deck stands on a skirt of upright planks with two ledgers and a plank missing in front. Two
square posts rise from the floor through the deck, a little behind its middle, and carry a
4 m crossbeam. Each post has one knee brace under the beam and one strut down to the back of
the deck. The trapdoor leaf sits under the noose, hinged on the -X edge, with a bolt housing
and a lever beside it.

The noose is a laid hemp rope (5 cm thick) wrapped four times round the crossbeam. It hangs
in front of the beam to a hangman's knot (a coil of wraps) and an open loop that is wide enough
for a head. Nobody is on duty here at dusk, so nothing burns on the scaffold.
"""

import math

from ._sweep import rope

HX, HY = 1.7, 1.2          # deck half extents
DECK_TOP = 1.6
LEG = 0.22                 # square corner post section
POST_X, POST_Y, POST_W, POST_TOP = 1.4, 0.30, 0.30, 4.40
BEAM_Y, BEAM_Z, BEAM_L = POST_Y, 4.55, 3.9
BEAM_HY, BEAM_HZ = 0.15, 0.17      # crossbeam half section (y, z)
NOOSE_X = 0.07
ROPE_R = 0.025             # 5 cm rope

N_BOARDS = 12
TRAP_X0, TRAP_X1 = -0.5, 0.5       # trapdoor leaf, hinged on the -X edge
TRAP_BOARDS = (5, 6, 7, 8)         # deck boards (by index) that form the leaf
TRAP_GAP = 0.027                   # open seam round the leaf

STAIR_STEPS = 7
STAIR_RISE = DECK_TOP / STAIR_STEPS
STAIR_RUN = 0.25
STAIR_Y = -0.5             # stair centerline
STAIR_W = 1.0

LIGHTS = []   # nobody is on duty here: no flame at the gallows


def _stair_top(s):
    """Height of the stringer's upper edge at distance s west of the deck edge."""
    return 6.5 * STAIR_RISE - 0.03 - STAIR_RISE / STAIR_RUN * s


def build(kit, mats, rng):
    wd, wo, rp, iron = mats["wood_dark"], mats["wood_old"], mats["rope"], mats["iron"]
    root = kit.group("gallows")
    J = lambda a: kit.jitter(rng, a)  # noqa: E731

    def timber(name, size, loc, rot=(0, 0, 0), mat=None, bevel=0.015):
        return kit.box(name, size, loc, (rot[0] + J(0.3), rot[1] + J(0.3), rot[2] + J(0.4)),
                       mat or wd, bevel, root)

    # --- deck frame and skirt ------------------------------------------------------------
    cx, cy = HX - 0.05, HY - 0.05
    for sx in (-1, 1):
        for sy in (-1, 1):
            kit.box(f"corner_{sx:+d}{sy:+d}", (LEG, LEG, 1.54), (sx * cx + J(0.005), sy * cy + J(0.005), 0.77),
                    (J(0.4), J(0.4), J(1.0)), wd, 0.015, root)
    for sy in (-1, 1):
        timber(f"rim_y{sy:+d}", (2 * HX + 0.06, 0.16, 0.18), (0, sy * (HY + 0.0), 1.46), bevel=0.012)
    for sx in (-1, 1):
        timber(f"rim_x{sx:+d}", (0.16, 2 * HY, 0.18), (sx * HX, 0, 1.46), bevel=0.012)

    def plank_run(tag, along_x, fixed, length, gap_at=()):
        n = int(round(length / 0.18))
        pitch = length / n
        for i in range(n):
            if i in gap_at:
                continue
            t = -length / 2 + pitch * (i + 0.5)
            z0 = rng.choice((0.0, 0.0, 0.04, 0.09, 0.15))
            z1 = 1.50 + J(0.015)
            size = (pitch - 0.012 + J(0.004), 0.04, z1 - z0) if along_x else (0.04, pitch - 0.012 + J(0.004), z1 - z0)
            loc = (t, fixed, (z0 + z1) / 2) if along_x else (fixed, t, (z0 + z1) / 2)
            kit.box(f"skirt_{tag}_{i:02d}", size, loc, (J(0.4), J(0.4), J(0.5)), wd, 0.008, root)

    plank_run("front", True, -HY - 0.01, 2 * HX - 0.2, gap_at=(5,))
    plank_run("back", True, HY + 0.01, 2 * HX - 0.2)
    plank_run("west", False, -HX - 0.01, 2 * HY - 0.2)
    plank_run("east", False, HX + 0.01, 2 * HY - 0.2)
    for z in (0.30, 1.22):
        timber(f"ledger_front_{z}", (2 * HX - 0.1, 0.035, 0.07), (0, -HY - 0.05, z), mat=wo, bevel=0.006)
        timber(f"ledger_east_{z}", (0.035, 2 * HY - 0.1, 0.07), (HX + 0.05, 0, z), mat=wo, bevel=0.006)

    # --- deck boards and trapdoor ----------------------------------------------------------
    for i in range(N_BOARDS):
        y = -HY + 0.1 + i * 0.2 + J(0.005)
        w = 0.186 + J(0.006)
        length = 2 * HX - rng.uniform(0.0, 0.07)
        if i in TRAP_BOARDS:
            # the board is cut into a left piece, the hinged leaf and a right piece
            x_l, x_r = TRAP_X0 - TRAP_GAP, TRAP_X1 + TRAP_GAP
            kit.box(f"board_{i:02d}_l", (x_l + HX, w, 0.07), ((x_l - HX) / 2, y, DECK_TOP - 0.035 + J(0.004)),
                    (J(0.5), J(0.4), J(0.35)), wo, 0.01, root)
            kit.box(f"board_{i:02d}_r", (HX - x_r, w, 0.07), ((x_r + HX) / 2, y, DECK_TOP - 0.035 + J(0.004)),
                    (J(0.5), J(0.4), J(0.35)), wo, 0.01, root)
            inset = 0.013 if i in (TRAP_BOARDS[0], TRAP_BOARDS[-1]) else 0.0
            ly = y + inset * (1 if i == TRAP_BOARDS[0] else -1 if i == TRAP_BOARDS[-1] else 0)
            kit.box(f"leaf_{i:02d}", (TRAP_X1 - TRAP_X0 - 0.01, w - inset * 2, 0.066),
                    ((TRAP_X0 + TRAP_X1) / 2, ly, DECK_TOP - 0.037),
                    (J(0.3), J(0.3), J(0.3)), wd, 0.008, root)
            continue
        kit.box(f"board_{i:02d}", (length, w, 0.07), (J(0.03), y, DECK_TOP - 0.035 + J(0.006)),
                (J(0.5), J(0.4), J(0.35)), wo, 0.01, root)

    y_of = lambda i: -HY + 0.1 + i * 0.2  # noqa: E731
    ty0 = y_of(TRAP_BOARDS[0]) - 0.093 + 0.013
    ty1 = y_of(TRAP_BOARDS[-1]) + 0.093 - 0.013
    tcy, tcx = (ty0 + ty1) / 2, (TRAP_X0 + TRAP_X1) / 2
    # dark frame timbers under the seams make the outline read
    for sy, ye in ((-1, ty0), (1, ty1)):
        timber(f"trap_frame_y{sy:+d}", (TRAP_X1 - TRAP_X0 + 0.16, 0.08, 0.1), (tcx, ye + sy * TRAP_GAP / 2, 1.48))
    for sx, xe in ((-1, TRAP_X0), (1, TRAP_X1)):
        timber(f"trap_frame_x{sx:+d}", (0.08, ty1 - ty0 + 0.16, 0.1), (xe + sx * TRAP_GAP / 2, tcy, 1.48))
    # hinges on the -X edge, bolt housing on the +X edge, hasp bar toward the lever
    for hy in (ty0 + 0.12, ty1 - 0.12):
        kit.box(f"hinge_strap_{hy:+.2f}", (0.34, 0.05, 0.012), (TRAP_X0 + 0.12, hy, DECK_TOP + 0.002),
                mat=iron, bevel=0.003, parent=root)
        kit.cylinder(f"hinge_pin_{hy:+.2f}", 0.017, 0.07, (TRAP_X0 - 0.04, hy, DECK_TOP - 0.004),
                     (90, 0, 0), iron, 8, parent=root)
        for dx in (0.0, 0.14, 0.28):
            kit.cylinder(f"hinge_rivet_{hy:+.2f}_{dx}", 0.011, 0.01, (TRAP_X0 - 0.02 + dx, hy, DECK_TOP + 0.012),
                         mat=iron, segments=6, parent=root)
    kit.box("bolt_housing", (0.10, 0.16, 0.045), (TRAP_X1 + 0.06, tcy, DECK_TOP + 0.022), mat=iron,
            bevel=0.004, parent=root)
    lev_x = TRAP_X1 + 0.42
    kit.box("hasp_bar", (lev_x - TRAP_X1 - 0.08, 0.03, 0.012), ((lev_x + TRAP_X1 + 0.08) / 2, tcy, DECK_TOP + 0.006),
            mat=iron, bevel=0.003, parent=root)

    # lever: base plate, two cheeks with a pivot bolt, a tapered handle leaning toward the trap
    kit.box("lever_plate", (0.22, 0.16, 0.014), (lev_x, tcy, DECK_TOP + 0.007), mat=iron, bevel=0.003, parent=root)
    for sy in (-1, 1):
        kit.box(f"lever_cheek_{sy:+d}", (0.14, 0.014, 0.13), (lev_x, tcy + sy * 0.035, DECK_TOP + 0.07),
                mat=iron, bevel=0.003, parent=root)
    kit.cylinder("lever_pivot", 0.014, 0.1, (lev_x, tcy, DECK_TOP + 0.09), (90, 0, 0), iron, 8, parent=root)
    top = (lev_x - 0.34, tcy, DECK_TOP + 0.96)
    kit.beam("lever_handle", (lev_x + 0.01, tcy, DECK_TOP + 0.09), top, (0.055, 0.045), wd, 0.008, parent=root)
    kit.box("lever_cap", (0.075, 0.065, 0.05), (top[0], top[1], top[2] + 0.015), (0, -24, 0), iron, 0.006, root)

    # --- stair on the -X end ---------------------------------------------------------------
    for i in range(1, STAIR_STEPS):
        xc = -HX - (6.5 - i) * STAIR_RUN
        kit.box(f"tread_{i}", (STAIR_RUN - 0.015, STAIR_W, 0.05),
                (xc + J(0.01), STAIR_Y + J(0.01), i * STAIR_RISE - 0.025 + J(0.005)),
                (J(0.5), J(1.0), J(0.4)), wo, 0.008, root)

    slope = STAIR_RISE / STAIR_RUN
    thick = 0.30
    s_far, s_near = 6 * STAIR_RUN + 0.02, -0.1
    s_foot = (_stair_top(0.0) - thick) / slope
    profile = [(s_far, 0.0), (s_far, max(_stair_top(s_far), 0.03)), (s_near, _stair_top(s_near)),
               (s_near, _stair_top(s_near) - thick), (s_foot, 0.0)]
    n = len(profile)
    side_y = (STAIR_Y - STAIR_W / 2 - 0.06, STAIR_Y + STAIR_W / 2 + 0.06)
    for sy in side_y:
        verts = [(-HX - s, sy - 0.04, z) for s, z in profile] + [(-HX - s, sy + 0.04, z) for s, z in profile]
        faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
        kit.mesh(f"stringer_{sy:+.2f}", verts, faces, mat=wd, parent=root, bevel=0.01)

    # one handrail on the back side of the stair: a tall post at the deck edge, a short one at the foot
    ry = side_y[1]
    s_bot = 6 * STAIR_RUN - 0.1
    rail_hi = (-HX - 0.02, ry, 2.42)
    rail_lo = (-HX - s_bot, ry, _stair_top(s_bot) + 0.84)
    kit.beam("rail", rail_hi, rail_lo, (0.07, 0.07), wd, 0.01, parent=root)
    kit.box("rail_post_top", (0.12, 0.12, 2.4), (-HX - 0.02, ry, 1.2), (J(0.4), J(0.4), 0), wd, 0.01, root)
    kit.box("rail_post_foot", (0.1, 0.1, rail_lo[2]), (-HX - s_bot, ry, rail_lo[2] / 2), (J(0.4), J(0.4), 0), wd,
            0.01, root)

    # --- posts, crossbeam, braces, iron ----------------------------------------------------
    kit.box("beam", (BEAM_L, 0.30, 0.34), (0, BEAM_Y, BEAM_Z), (J(0.3), J(0.3), 0.0), wo, 0.02, root)
    for sx in (-1, 1):
        kit.box(f"post_{sx:+d}", (POST_W, POST_W, POST_TOP), (sx * POST_X + J(0.006), POST_Y, POST_TOP / 2),
                (J(0.3), J(0.3), J(1.0)), wo, 0.02, root)
        # knee brace under the beam, toward the middle
        kit.beam(f"knee_{sx:+d}", (sx * (POST_X - POST_W / 2), POST_Y, 3.40), (sx * 0.58, POST_Y, BEAM_Z - 0.12),
                 (0.15, 0.14), wo, 0.012, parent=root)
        # strut from the post down to the back of the deck
        kit.beam(f"strut_{sx:+d}", (sx * POST_X, POST_Y + POST_W / 2 - 0.03, 3.0), (sx * POST_X, HY - 0.15, DECK_TOP + 0.05),
                 (0.13, 0.14), wo, 0.012, parent=root)

        # iron: a strap on the front and back of the beam-to-post joint, bolts at both knee ends,
        # bands round the post
        for sy in (-1, 1):
            yf = POST_Y + sy * (POST_W / 2 + 0.008)
            kit.box(f"joint_strap_{sx:+d}{sy:+d}", (POST_W + 0.02, 0.016, 0.62), (sx * POST_X, yf, BEAM_Z - 0.04),
                    mat=iron, bevel=0.004, parent=root)
            for bx in (-0.09, 0.09):
                for bz in (-0.26, 0.2):
                    kit.cylinder(f"joint_bolt_{sx:+d}{sy:+d}_{bx}_{bz}", 0.019, 0.02,
                                 (sx * POST_X + bx, yf + sy * 0.012, BEAM_Z - 0.04 + bz),
                                 (90, 0, 0), iron, 8, parent=root)
            for ex, ez in ((sx * (POST_X - POST_W / 2 - 0.01), 3.46), (sx * 0.64, BEAM_Z - 0.2)):
                kit.cylinder(f"knee_bolt_{sx:+d}{sy:+d}_{ez:.2f}", 0.017, 0.016,
                             (ex, POST_Y + sy * 0.075, ez), (90, 0, 0), iron, 8, parent=root)
        for bz in (2.1, 3.1):
            kit.box(f"post_band_{sx:+d}_{bz}", (POST_W + 0.024, POST_W + 0.024, 0.06), (sx * POST_X, POST_Y, bz),
                    mat=iron, bevel=0.005, parent=root)

    # --- noose: laid hemp rope --------------------------------------------------------------
    nx = NOOSE_X
    a, b = BEAM_HY + ROPE_R + 0.001, BEAM_HZ + ROPE_R + 0.001
    sup = lambda c, e=0.2: math.copysign(abs(c) ** e, c)  # noqa: E731  rounded-rectangle profile
    turns, per, pitch = 4.0, 22, 0.052
    wrap = []
    for i in range(int(turns * per) + 1):
        t = math.pi - 2 * math.pi * (turns - i / per)
        wrap.append((nx - pitch * (turns - i / per), BEAM_Y + a * sup(math.cos(t)), BEAM_Z + b * sup(math.sin(t))))
    y_h = BEAM_Y - a                        # the rope hangs in front of the beam
    x_h = wrap[-1][0]
    psi = math.radians(28)                  # loop plane turned a little toward the camera
    e1, e2 = (math.cos(psi), math.sin(psi)), (-math.sin(psi), math.cos(psi))
    z_k = 3.14                              # knot center
    z_top, A, Bz = z_k - 0.09, 0.15, 0.22
    off = 0.026
    sway = lambda z: 0.012 * math.sin((BEAM_Z - z) * 2.1) + 0.010 * (BEAM_Z - z)  # noqa: E731

    def at(lx, z, ln=0.0):
        return (x_h + e1[0] * lx + e2[0] * ln + sway(z), y_h + e1[1] * lx + e2[1] * ln, z)

    path = [wrap[-1]]
    for z in (4.30, 4.05, 3.80, 3.55, 3.34):
        path.append(at(0.0, z))
    path += [at(0.0, z_k + 0.12), at(-off, z_k + 0.05), at(-off, z_top)]
    for i in range(1, 24):                  # down the left side, round the bottom, up the right
        th = math.pi * i / 24
        path.append(at(-(A * math.sin(th) + off * math.cos(th / 2) ** 2), z_top - Bz + Bz * math.cos(th)))
    path.append(at(0.0, z_top - 2 * Bz))
    for i in range(1, 24):
        th = math.pi + math.pi * i / 24
        path.append(at(-A * math.sin(th) + off * math.cos(th / 2) ** 2, z_top - Bz + Bz * math.cos(th)))
    path += [at(off, z_top), at(off + 0.003, z_k + 0.08), at(off + 0.014, z_k + 0.135), at(off + 0.024, z_k + 0.16)]

    rope(kit, "noose_wraps", wrap, ROPE_R, rp, root, lay=0.12, step=0.014, sides=5,
         origin=(nx, BEAM_Y, BEAM_Z))
    rope(kit, "noose_rope", path, ROPE_R, rp, root, lay=0.12, step=0.013, sides=6,
         origin=(x_h, y_h, 0.0))

    # hangman's knot: seven wraps of thinner line round the doubled rope
    coil = []
    for i in range(7 * 20 + 1):
        t = 2 * math.pi * i / 20
        coil.append(at(0.066 * math.cos(t), z_k + 0.085 - 0.17 * i / (7 * 20), 0.044 * math.sin(t)))
    rope(kit, "noose_knot", coil, 0.0145, rp, root, lay=0.05, step=0.01, sides=5,
         origin=at(0.0, z_k))
    return root

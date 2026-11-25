"""Hand-made things along the west ditch: stones fallen from the wall, a broken post-and-rail fence on the
inner bank and sharpened stakes on the outer bank.

Helper of west_ditch.py. Positions are world (x, y); heights come from `_ditch_field.ground`.
"""

import math

from mathutils import Vector

from . import _ditch_field as F

LANTERN_Y = 0.4         # world y of the lantern post on the fence line
LANTERN_POST = 1.35     # height of that post above the ground


def _at(x, y, lift=0.0):
    """Local position on the ground at world (x, y)."""
    return Vector(F.to_local(x, y, F.ground(x, y) + lift))


def _rod(kit, name, p0, p1, r0, r1, mat, root, segments=7):
    """Round timber from p0 (radius r0) to p1 (radius r1)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    ob = kit.cylinder(name, r0, d.length, tuple((p0 + p1) / 2), mat=mat, segments=segments, radius_top=r1,
                      parent=root)
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = d.to_track_quat("Z", "Y")
    return ob


# ---------------------------------------------------------------- fallen stones

def _stone(kit, mats, rng, root, name, x, y, size, sink=0.35, tilt=14.0):
    """A squared block, tilted and sunk into the mud; `size` is its longest edge."""
    a = size
    b = size * rng.uniform(0.45, 0.8)
    c = size * rng.uniform(0.35, 0.65)
    p = _at(x, y)
    return kit.box(name, (a, b, c), (p.x, p.y, p.z + c * (0.5 - sink)),
                   (rng.uniform(-tilt, tilt), rng.uniform(-tilt, tilt), rng.uniform(0, 180)),
                   mats["stone_wall"], bevel=min(0.03, size * 0.12), parent=root)


def stones(kit, mats, rng, root):
    # two merlons thrown off the parapet, half sunk, with the chips they shed
    for i, (y, e) in enumerate(((-6.1, 0.95), (1.4, 1.9))):
        x = F.WALL_X - e
        p = _at(x, y)
        kit.box(f"fallen_merlon_{i}", (0.75, 0.60, 0.75 if i == 0 else 0.5), (p.x, p.y, p.z + 0.14),
                (rng.uniform(25, 45), rng.uniform(-12, 12), rng.uniform(0, 180)),
                mats["stone_wall"], bevel=0.05, parent=root)
        for k in range(rng.randint(3, 5)):
            _stone(kit, mats, rng, root, f"merlon_chip_{i}_{k}", x + rng.gauss(0, 0.5), y + rng.gauss(0, 0.5),
                   rng.uniform(0.14, 0.28), sink=0.4, tilt=25)
    # ashlars and smaller rubble along the foot and on the track edge
    for i in range(9):
        y = rng.uniform(-12.5, 8.0)
        x = F.WALL_X - rng.uniform(0.3, 1.9)
        _stone(kit, mats, rng, root, f"ashlar_{i}", x, y, rng.uniform(0.28, 0.5), sink=rng.uniform(0.25, 0.5), tilt=18)
    for i in range(34):
        y = rng.uniform(-13.0, 9.0)
        x = F.WALL_X - rng.uniform(0.15, 2.2)
        _stone(kit, mats, rng, root, f"rubble_{i}", x, y, rng.uniform(0.05, 0.16), sink=rng.uniform(0.2, 0.5), tilt=30)
    # stones along the waterline, tops just out of the water
    for i in range(9):
        y = rng.uniform(-12.0, 9.5)
        side = rng.choice((-1, 1))
        x = F.centre(y) + side * (F.half_width(y) + rng.uniform(-0.15, 0.2))
        _stone(kit, mats, rng, root, f"bank_stone_{i}", x, y, rng.uniform(0.2, 0.5), sink=0.55, tilt=20)


# ---------------------------------------------------------------- broken fence on the inner bank

def fence(kit, mats, rng, root):
    """Round posts every 2 m with two rails; many rails are gone, some posts lean or have rotted to stumps."""
    posts = []
    y = -12.0
    while y < 8.5:
        y += rng.uniform(1.7, 2.3)
        if abs(y - LANTERN_Y) < 0.9:
            continue                                              # the lantern post stands here
        x = F.centre(y) + F.half_width(y) + 0.92 + rng.uniform(-0.08, 0.08)
        roll = rng.random()
        if roll < 0.12:       # rotted off at the ground: only the stump
            height, lean = rng.uniform(0.18, 0.35), rng.uniform(0, 12)
        elif roll < 0.35:     # leaning toward the ditch
            height, lean = rng.uniform(0.85, 1.2), rng.uniform(10, 24)
        else:
            height, lean = rng.uniform(0.9, 1.25), rng.uniform(0, 7)
        az = math.radians(rng.uniform(0, 360))
        if roll >= 0.12 and roll < 0.35:
            az = math.radians(180 + rng.uniform(-30, 30))     # toward the ditch (west)
        a = math.radians(lean)
        axis = Vector((math.sin(a) * math.cos(az), math.sin(a) * math.sin(az), math.cos(a)))
        base = _at(x, y, -0.20)
        top = base + axis * (height + 0.20)
        _rod(kit, f"fence_post_{len(posts)}", base, top, 0.06, 0.05, mats["wood_dark"], root)
        posts.append((base + axis * 0.20, top, height))
    for i, ((b0, t0, h0), (b1, t1, h1)) in enumerate(zip(posts, posts[1:])):
        if h0 < 0.5 or h1 < 0.5:
            continue
        for frac, tag in ((0.80, "hi"), (0.40, "lo")):
            p0, p1 = b0.lerp(t0, frac), b1.lerp(t1, frac)
            roll = rng.random()
            if roll < 0.40:
                continue                                          # rail gone
            if roll < 0.62:                                       # hangs from one post, free end dropped
                end = p0.lerp(p1, rng.uniform(0.35, 0.6))
                end.z -= rng.uniform(0.35, 0.6)
                p1 = end
            kit.beam(f"fence_rail_{tag}_{i}", tuple(p0), tuple(p1), section=(0.09, 0.05), mat=mats["wood_old"],
                     bevel=0.008, parent=root)
    # a post and a length of rail that have fallen into the ditch
    y = -3.4
    p = _at(F.centre(y) + F.half_width(y) + 0.30, y, 0.05)
    _rod(kit, "fallen_post", p, p + Vector((-0.9, 0.5, -0.06)), 0.06, 0.05, mats["wood_dark"], root)


# ---------------------------------------------------------------- stakes on the outer bank

def stakes(kit, mats, rng, root):
    """Sharpened stakes set in the crest of the spoil bank, leaning out at the open ground; some are snapped."""
    for g, y in enumerate((-11.5, -6.8, -1.6, 4.2, 9.5)):
        x0 = F.centre(y) - F.half_width(y) - rng.uniform(0.9, 1.3)
        for i in range(rng.randint(4, 7)):
            yy = y + (i - 3) * rng.uniform(0.3, 0.45)
            xx = x0 + rng.uniform(-0.2, 0.2)
            base = _at(xx, yy, -0.28)
            length = rng.uniform(1.4, 1.9)
            if rng.random() < 0.25:
                length *= rng.uniform(0.35, 0.6)                  # snapped
            tilt = math.radians(rng.uniform(42, 62))
            az = math.radians(180 + rng.uniform(-18, 18))         # leaning west, away from the castle
            axis = Vector((math.sin(tilt) * math.cos(az), math.sin(tilt) * math.sin(az), math.cos(tilt)))
            _rod(kit, f"stake_{g}_{i}", base, base + axis * length, 0.05, 0.012 if length > 1.0 else 0.04,
                 mats["wood_dark"], root, segments=6)


# ---------------------------------------------------------------- lantern post

def lantern_post(kit, mats, rng, root):
    """A heavy post on the fence line with a capboard on top for a standing lantern. Returns the local point
    where the lantern's base goes."""
    x = F.track_x(LANTERN_Y) - 0.70
    base = _at(x, LANTERN_Y, -0.25)
    top = base + Vector((0, 0, LANTERN_POST + 0.25))
    _rod(kit, "lantern_post", base, top, 0.09, 0.075, mats["wood_dark"], root, segments=8)
    kit.box("lantern_capboard", (0.27, 0.27, 0.05), (top.x, top.y, top.z + 0.02), (0, 0, rng.uniform(-10, 10)),
            mats["wood_old"], bevel=0.008, parent=root)
    return Vector((top.x, top.y, top.z + 0.045))


# ---------------------------------------------------------------- litter

def litter(kit, mats, rng, root):
    """A windfall log along the track, broken boards half sunk in the mud and a few sticks."""
    p0 = _at(F.WALL_X - 0.75, 5.0, 0.13)
    p1 = _at(F.WALL_X - 1.15, 7.4, 0.12)
    _rod(kit, "windfall_log", p0, p1, 0.15, 0.11, mats["bark"], root, segments=8)
    for i, (y, e, ang) in enumerate(((-0.4, 1.1, 14), (-9.4, 0.9, -30), (3.4, 1.75, 70), (-13.0, 1.3, 5), (7.9, 1.0, -20),
                                     (-4.8, 2.1, 100))):
        x = F.WALL_X - e
        p = _at(x, y)
        ln = rng.uniform(0.8, 1.7)
        a = math.radians(ang)
        kit.box(f"board_{i}", (ln, rng.uniform(0.14, 0.22), 0.03), (p.x, p.y, p.z + 0.015),
                (rng.uniform(-6, 6), rng.uniform(-6, 6), ang), mats["wood_old"], bevel=0.006, parent=root)
        if i % 2 == 0:       # a rusted nail-bar lies across it
            kit.beam(f"board_nail_{i}", (p.x, p.y, p.z + 0.04), (p.x + math.cos(a + 1.5) * 0.35, p.y + math.sin(a + 1.5) * 0.35, p.z + 0.045),
                     section=(0.03, 0.02), mat=mats["iron"], parent=root)
    for i in range(14):
        y = rng.uniform(-12.5, 8.5)
        x = F.WALL_X - rng.uniform(0.2, 2.4)
        p = _at(x, y, 0.02)
        a = rng.uniform(0, 6.28)
        ln = rng.uniform(0.25, 0.7)
        kit.beam(f"stick_{i}", (p.x - math.cos(a) * ln / 2, p.y - math.sin(a) * ln / 2, p.z),
                 (p.x + math.cos(a) * ln / 2, p.y + math.sin(a) * ln / 2, p.z + rng.uniform(0.0, 0.05)),
                 section=(0.015, 0.015), mat=mats["wood_dark"], parent=root)

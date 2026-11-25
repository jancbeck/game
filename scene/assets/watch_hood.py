"""Timber watch hood on a tower roof: a lean-to that keeps the rain off the lookout.

A working tower's roof platform has a sentry on it, and in this weather he stands under a hood
rather than in the open. It faces north, so he looks over the parapet down the bridge and the
road. Four posts on sole plates (no fixing into the roof's paving), a plank roof that falls to the
south so the water runs off behind him, the weather side (west) boarded, a bench along the back.
Nothing burns: a lookout at night keeps his eyes dark.

Origin at the floor center of the hood, on the roof platform. Footprint 1.9 m (X) by 1.5 m (Y);
the eave is 2.25 m above the floor at the open north side and 1.95 m at the back.
"""

import math

LIGHTS = []

W, D = 1.9, 1.5
H_FRONT, H_BACK = 2.25, 1.95
POST = 0.12


def build(kit, mats, rng):
    root = kit.group("watch_hood")
    wood, dark, iron = mats["wood_old"], mats["wood_dark"], mats["iron"]
    hx, hy = W / 2 - POST / 2, D / 2 - POST / 2

    def top(y):
        """Underside of the roof at local y."""
        return H_BACK + (H_FRONT - H_BACK) * (y + D / 2) / D

    # sole plates and posts
    for side in (-1, 1):
        kit.box(f"sole_{side}", (0.16, D + 0.2, 0.1), (side * hx, 0, 0.05), mat=dark, bevel=0.01, parent=root)
    for sx in (-1, 1):
        for sy in (-1, 1):
            h = top(sy * hy) - 0.1
            kit.box(f"post_{sx}_{sy}", (POST, POST, h), (sx * hx, sy * hy, 0.1 + h / 2),
                    (kit.jitter(rng, 0.8), kit.jitter(rng, 0.8), 0), mat=dark, bevel=0.01, parent=root)
    # plates along the front and back, rafters down the slope
    for sy in (-1, 1):
        z = top(sy * hy)
        kit.box(f"plate_{sy}", (W + 0.1, 0.13, 0.13), (0, sy * hy, z - 0.065), mat=dark, bevel=0.01, parent=root)
    slope = math.degrees(math.atan2(H_FRONT - H_BACK, D))
    length = math.hypot(D + 0.35, H_FRONT - H_BACK)
    for i, x in enumerate((-hx, -hx / 3, hx / 3, hx)):
        kit.box(f"rafter_{i}", (0.08, length, 0.11), (x, 0.02, (H_FRONT + H_BACK) / 2 + 0.055), (slope, 0, 0),
                mat=dark, bevel=0.008, parent=root)
    # roof planks laid down the slope, uneven widths, one newer
    x = -W / 2 - 0.12
    k = 0
    while x < W / 2 + 0.12:
        w = rng.uniform(0.17, 0.26)
        mat = mats["door_wood"] if k == 3 else wood
        kit.box(f"roof_{k}", (w - 0.01, length + 0.05, 0.035),
                (x + w / 2, 0.02 + kit.jitter(rng, 0.03), (H_FRONT + H_BACK) / 2 + 0.13),
                (slope + kit.jitter(rng, 0.6), 0, kit.jitter(rng, 0.8)), mat=mat, bevel=0.004, parent=root)
        x += w
        k += 1
    # boarded west side and half the back, against the wind and rain from the north-west
    y = -hy + 0.06
    k = 0
    while y < hy - 0.06:
        w = rng.uniform(0.18, 0.24)
        h = top(y + w / 2) - 0.25
        kit.box(f"side_board_{k}", (0.03, w - 0.012, h), (-hx - 0.075, y + w / 2, 0.15 + h / 2), mat=wood,
                bevel=0.004, parent=root)
        y += w
        k += 1
    for k in range(4):
        h = H_BACK - 0.35
        kit.box(f"back_board_{k}", (0.22, 0.03, h), (-hx + 0.17 + k * 0.23, -hy - 0.075, 0.15 + h / 2), mat=wood,
                bevel=0.004, parent=root)
    # bench along the back, a horn on a nail for calling the gate
    kit.box("bench", (1.3, 0.3, 0.05), (0.1, -hy + 0.2, 0.45), mat=wood, bevel=0.005, parent=root)
    for sx in (-1, 1):
        kit.box(f"bench_leg_{sx}", (0.06, 0.24, 0.43), (0.1 + sx * 0.55, -hy + 0.2, 0.215), mat=dark, bevel=0.004,
                parent=root)
    kit.cylinder("horn", 0.04, 0.32, (hx - 0.08, -hy + 0.1, 1.45), (0, 70, 20), mat=mats["bark"], segments=10,
                 radius_top=0.012, parent=root)
    kit.cylinder("horn_nail", 0.006, 0.08, (hx, -hy + 0.1, 1.52), (90, 0, 0), mat=iron, segments=6, parent=root)
    return root

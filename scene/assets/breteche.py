"""Bretèche over the outer gate: a small stone box on corbels, from which the gate is defended.

The garrison drops stones or water through the slot in its floor onto anyone at the gate, and the
sentry looks down the bridge through a sight slit in its front wall. It is entered from the
gatehouse's upper room at the 6 m floor.

Origin on the wall face at the foot of the corbels, centered on the gate. +Y points into the wall,
like the other mounted props: place it on the gatehouse's outer (north) face with rot_z 180, at
z = 5.35 so its floor is at 6.0.

Sizes: 2.6 m wide, 0.85 m deep. Three corbels of three stepped stones each carry it; the floor slab
reaches only 0.35 m out, so a 0.2 m slot stays open behind the front wall between the corbels. The
walls rise 1.7 m above the floor, and a stone-slab roof slopes up to the wall face. Nothing burns.
"""

import math

LIGHTS = []

WIDTH, DEPTH = 2.6, 0.85
CORBEL_W, COURSE = 0.32, 0.22
STEPS = (0.30, 0.55, 0.85)
FLOOR_Z = len(STEPS) * COURSE      # 0.66: top of the corbels
FLOOR_REACH = 0.35                  # the floor slab's reach from the wall; the slot lies beyond it
WALL_T = 0.30
WALL_H = 1.70
SLIT = (0.18, 0.62)                 # sight slit width and height in the front wall


def build(kit, mats, rng):
    root = kit.group("breteche")
    stone = mats["stone_wall"]
    from assets.gate_door import _dressed
    dressed = _dressed(stone)

    # corbels: each course reaches farther out than the one below; the stones run 0.15 m into the wall
    for i, x in enumerate((-WIDTH / 2 + CORBEL_W / 2 + 0.02, 0.0, WIDTH / 2 - CORBEL_W / 2 - 0.02)):
        for k, reach in enumerate(STEPS):
            d = reach + 0.15
            kit.box(f"corbel_{i}_{k}", (CORBEL_W + kit.jitter(rng, 0.01), d, COURSE - 0.008),
                    (x, -reach + d / 2, k * COURSE + COURSE / 2), mat=dressed, bevel=0.015, parent=root)

    # floor slab against the wall; the slot between it and the front wall stays open
    kit.box("floor", (WIDTH, FLOOR_REACH + 0.1, 0.16), (0, -FLOOR_REACH / 2 + 0.05, FLOOR_Z - 0.08),
            mat=dressed, bevel=0.01, parent=root)

    z0, z1 = FLOOR_Z, FLOOR_Z + WALL_H
    yf = -DEPTH + WALL_T / 2
    # lintel along the corbel tips, under the front wall
    kit.box("lintel", (WIDTH, WALL_T, 0.2), (0, yf, z0 + 0.1), mat=dressed, bevel=0.015, parent=root)
    # front wall with a sight slit
    sw, sh = SLIT
    s0 = z0 + 0.85
    kit.box("front_low", (WIDTH, WALL_T, s0 - z0 - 0.2), (0, yf, (z0 + 0.2 + s0) / 2), mat=stone, bevel=0.02,
            parent=root)
    side_w = (WIDTH - sw) / 2
    for side in (-1, 1):
        kit.box(f"front_{side}", (side_w, WALL_T, sh), (side * (sw / 2 + side_w / 2), yf, s0 + sh / 2), mat=stone,
                bevel=0.02, parent=root)
    kit.box("front_top", (WIDTH, WALL_T, z1 - s0 - sh), (0, yf, (s0 + sh + z1) / 2), mat=stone, bevel=0.02,
            parent=root)
    # side walls, back into the wall face
    for side in (-1, 1):
        kit.box(f"side_{side}", (WALL_T, DEPTH - WALL_T + 0.05, WALL_H),
                (side * (WIDTH / 2 - WALL_T / 2), -(DEPTH - WALL_T) / 2 + 0.025, (z0 + z1) / 2),
                mat=stone, bevel=0.02, parent=root)

    # roof: two stone slabs side by side, sloping up to the wall face so rain runs off the front
    rise = 0.38
    run = DEPTH + 0.2
    tilt = math.degrees(math.atan2(rise, run))
    length = math.hypot(rise, run)
    for side in (-1, 1):
        kit.box(f"roof_{side}", (WIDTH / 2 + 0.1, length, 0.11),
                (side * (WIDTH / 4 + 0.05), -run / 2 + 0.05, z1 + rise / 2 + 0.05), (tilt, kit.jitter(rng, 0.6), 0),
                mat=stone, bevel=0.015, parent=root)
    return root

"""The commander's desk: a heavy oak table with ledgers, tally sticks, a sand-shaker, an inkwell and quill, letters under a stone, a candle stand with three candles, a jug and a cup.

1.7 x 0.8 m, top at 0.86 m, long side along X, the commander's side toward +Y. Origin: the middle of the
table on the floor. A drawer in the front, stretchers low between the legs. On the top, west to east: an open
ledger and a closed one (the muster roll and the stores book), a bundle of tally sticks, the sand-shaker and the
inkwell with a quill, a letter with a red seal under a river stone, then the iron candle stand (three candles,
the room's brightest warm light) and a jug with a pewter cup. Light: one warm point light among the candles.
"""

import math

from . import _kitchen, _lights
from . import _shed_geo as geo
from . import _shed_props as props
from . import _tower as T

LIGHTS = []
L, D, TOP = 1.7, 0.8, 0.86
CANDLE = dict(pos=(0.6, 0.05, 1.12), color=T.WARM, watts=26.0, radius=0.03, specular=0.4, reach=4.5)


def build(kit, mats, rng):
    root = kit.group("tower_desk")
    wo, wd, iron, dw = mats["wood_old"], mats["wood_dark"], mats["iron"], mats["door_wood"]
    _lights.add(root, "tower_desk", **CANDLE)
    # legs, stretchers, drawer
    for n, (px, py) in enumerate(((-L / 2 + 0.1, -D / 2 + 0.09), (L / 2 - 0.1, -D / 2 + 0.09), (-L / 2 + 0.1, D / 2 - 0.09),
                                  (L / 2 - 0.1, D / 2 - 0.09))):
        kit.box(f"desk_leg_{n}", (0.13, 0.13, TOP - 0.06), (px, py, (TOP - 0.06) / 2), mat=wd, bevel=0.008, parent=root)
    for n, y in enumerate((-D / 2 + 0.09, D / 2 - 0.09)):
        kit.box(f"desk_stretcher_{n}", (L - 0.2, 0.05, 0.07), (0, y, 0.2), mat=wd, bevel=0.005, parent=root)
    for n, x in enumerate((-L / 2 + 0.1, L / 2 - 0.1)):
        kit.box(f"desk_end_stretcher_{n}", (0.05, D - 0.2, 0.07), (x, 0, 0.2), mat=wd, bevel=0.005, parent=root)
    kit.box("desk_apron", (L - 0.2, D - 0.2, 0.1), (0, 0, TOP - 0.11), mat=wd, parent=root)
    kit.box("drawer_front", (0.5, 0.025, 0.09), (0.35, -D / 2 + 0.07, TOP - 0.11), mat=wo, bevel=0.004, parent=root)
    kit.torus("drawer_ring", 0.018, 0.004, (0.35, -D / 2 + 0.05, TOP - 0.11), (90, 0, 0), iron, major_segments=10,
              minor_segments=4, parent=root)
    # the top: three thick planks
    y = -D / 2 - 0.02
    for n, w_ in enumerate((0.27, 0.28, 0.27)):
        kit.box(f"desk_top_{n}", (L + 0.06, w_ - 0.006, 0.07), (0, y + w_ / 2, TOP - 0.035),
                (rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), 0), dw if n != 1 else wo, bevel=0.01, parent=root)
        y += w_
    zt = TOP

    # west end: the open muster roll and the closed stores book (the group `desk_ledgers`, hotspot ledgers), a bundle of tally sticks
    led = kit.group("desk_ledgers", (-0.44, 0.1, zt), parent=root)
    ox, oy = 0.44, -0.1       # the ledgers' positions below are desk-local; the group's origin is their middle
    kit.box("roll_cover", (0.5, 0.34, 0.02), (-0.58 + ox, 0.02 + oy, 0.01), (0, 0, 4), mats["clay"], bevel=0.004, parent=led)
    for side in (-1, 1):
        kit.box(f"roll_pages_{side}", (0.23, 0.31, 0.022), (-0.58 + side * 0.121 + ox, 0.02 + oy, 0.031), (0, 0, 4),
                mats["parchment"], bevel=0.002, parent=led)
    for k in range(5):
        kit.box(f"roll_line_{k}", (0.16, 0.003, 0.0015), (-0.69 + ox, 0.1 - k * 0.04 + oy, 0.0425), (0, 0, 4), mats["iron"],
                parent=led)
    kit.box("stores_book", (0.26, 0.19, 0.045), (-0.18 + ox, 0.18 + oy, 0.0225), (0, 0, -9), wd, bevel=0.006, parent=led)
    kit.box("stores_pages", (0.245, 0.17, 0.034), (-0.178 + ox, 0.178 + oy, 0.0225), (0, 0, -9), mats["parchment"], parent=led)
    kit.box("stores_book_b", (0.24, 0.17, 0.03), (-0.18 + ox, 0.18 + oy, 0.06), (0, 0, -3), mats["clay"], bevel=0.005, parent=led)
    tally = geo.Mesh()
    for k in range(7):
        tally.box((0.34, 0.013, 0.011), (-0.27 + rng.uniform(-0.01, 0.01), -0.18 + 0.011 * k, zt + 0.006 + 0.009 * (k % 2)),
                  (0, 0, rng.uniform(-3, 3)))
    tally.finish("tally_sticks", mats["scrubbed"], root)
    notches = geo.Mesh()
    for k in range(9):
        notches.box((0.004, 0.015, 0.003), (-0.4 + 0.032 * k, -0.18 + 0.011 * 3, zt + 0.0125 + 0.003), (0, 0, 0))
    notches.finish("tally_notches", mats["iron"], root)
    kit.box("tally_loose", (0.3, 0.012, 0.01), (-0.3, -0.07, zt + 0.005), (0, 0, 24), mats["scrubbed"], parent=root)

    # middle: a sand-shaker, an inkwell with a quill, a letter under a river stone
    _kitchen.lathe(kit, "sand_shaker", [(0.0, 0.0), (0.032, 0.0), (0.036, 0.012), (0.03, 0.05), (0.022, 0.07), (0.026, 0.078),
                                        (0.0, 0.084)], 14, mats["pewter"], (0.08, -0.14, zt), root)
    _kitchen.lathe(kit, "inkwell", [(0.0, 0.0), (0.04, 0.0), (0.042, 0.02), (0.036, 0.04), (0.02, 0.045), (0.0, 0.04)], 14,
                   mats["clay"], (0.17, -0.1, zt), root)
    kit.beam("quill", (0.17, -0.1, zt + 0.04), (0.06, 0.02, zt + 0.19), (0.004, 0.004), mats["crumb"], parent=root)
    kit.box("quill_vane", (0.09, 0.012, 0.0015), (0.1, -0.03, zt + 0.15), (0, -50, -48), mats["crumb"], parent=root)
    kit.box("letter_a", (0.21, 0.29, 0.003), (0.02, 0.2, zt + 0.0015), (0, 0, 14), mats["parchment"], parent=root)
    kit.box("letter_b", (0.2, 0.27, 0.003), (0.0, 0.17, zt + 0.0045), (0, 0, -7), mats["parchment"], parent=root)
    _kitchen.blob(kit, "letter_seal", (-0.04, 0.3, zt + 0.0085), (0.022, 0.022, 0.007), mats["cloth_red"], root, segments=10)
    stone = geo.Mesh()
    stone.ellipsoid((0.1, 0.12, zt + 0.032), (0.075, 0.055, 0.032), (0, 0, 20), segments=10)
    stone.finish("river_stone", mats["rock"], root, smooth=True)

    # east: the candle stand (iron foot and stem, three arms) and a jug with a pewter cup
    cx, cy = 0.6, 0.05
    kit.cylinder("stand_foot", 0.075, 0.012, (cx, cy, zt + 0.006), mat=iron, segments=14, parent=root)
    kit.cylinder("stand_stem", 0.011, 0.24, (cx, cy, zt + 0.13), mat=iron, segments=8, parent=root)
    kit.torus("stand_ring", 0.03, 0.004, (cx, cy, zt + 0.12), mat=iron, major_segments=12, minor_segments=4, parent=root)
    heights = (0.0, 0.0, 0.0)
    for k, (dx, dy, h) in enumerate(((-0.1, 0.0, 0.17), (0.1, 0.0, 0.2), (0.0, 0.07, 0.15))):
        kit.beam(f"stand_arm_{k}", (cx, cy, zt + 0.12), (cx + dx, cy + dy, zt + 0.2), (0.008, 0.008), iron, parent=root)
        kit.cylinder(f"stand_cup_{k}", 0.018, 0.016, (cx + dx, cy + dy, zt + 0.205), mat=iron, radius_top=0.024, segments=10,
                     parent=root)
        T.candle(kit, mats, root, f"candle_{k}", (cx + dx, cy + dy, zt + 0.213), h=h * 0.42, r=0.012)
    _kitchen.lathe(kit, "desk_jug", [(0.0, 0.0), (0.05, 0.0), (0.075, 0.07), (0.07, 0.15), (0.04, 0.2), (0.045, 0.225),
                                     (0.036, 0.23), (0.0, 0.2)], 16, mats["clay"], (0.77, -0.04, zt), root)
    kit.torus("jug_handle", 0.045, 0.01, (0.84, -0.04, zt + 0.13), (90, 0, 0), mats["clay"], major_segments=12,
              minor_segments=4, parent=root)
    _kitchen.lathe(kit, "desk_cup", [(0.0, 0.0), (0.03, 0.0), (0.038, 0.07), (0.04, 0.075), (0.036, 0.075), (0.0, 0.01)], 14,
                   mats["pewter"], (0.69, -0.22, zt), root)
    return root

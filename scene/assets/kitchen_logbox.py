"""A wood box of split logs by the hearth: four planks, a handful of logs heaped in it, chips on the floor.

Origin: the middle of the box on the floor; it is 0.7 m long (X), 0.45 m deep and 0.35 m high.
"""

from . import _shed_geo as geo

LIGHTS = []
L, D, H = 0.7, 0.45, 0.35


def build(kit, mats, rng):
    root = kit.group("kitchen_logbox")
    wo, wd = mats["wood_old"], mats["wood_dark"]
    for s in (-1, 1):
        kit.box(f"box_end_{s}", (0.04, D, H), (s * (L / 2 - 0.02), 0, H / 2), mat=wd, bevel=0.004, parent=root)
        kit.box(f"box_side_{s}", (L, 0.03, H * 0.8), (0, s * (D / 2 - 0.015), H * 0.4 + 0.03), mat=wo, bevel=0.004, parent=root)
    kit.box("box_floor", (L - 0.06, D - 0.05, 0.03), (0, 0, 0.045), mat=wd, parent=root)
    logs = geo.Mesh()
    for row in range(2):
        for i in range(5 - row):
            x = -L / 2 + 0.14 + i * 0.125 + row * 0.06 + rng.uniform(-0.01, 0.01)
            r = rng.uniform(0.05, 0.065)
            logs.cyl((x, -D / 2 + 0.06, 0.12 + row * 0.1), (x + rng.uniform(-0.02, 0.02), D / 2 - 0.06, 0.12 + row * 0.1 + 0.01),
                     r, r * 0.95, sides=7, twist=rng.uniform(0, 6))
    logs.finish("box_logs", wd, root)
    chips = geo.Mesh()
    for _ in range(14):
        chips.box((rng.uniform(0.03, 0.07), rng.uniform(0.012, 0.025), 0.006),
                  (rng.uniform(-0.45, 0.45), rng.uniform(-0.4, -0.2), 0.004), (0, 0, rng.uniform(0, 180)))
    chips.finish("box_chips", wo, root)
    return root

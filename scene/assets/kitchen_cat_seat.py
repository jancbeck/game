"""The cat's seat by the hearth: a plaited basket with a folded sack in it, pressed flat by something that sleeps there, and a bowl of milk.

Origin: the middle of the basket on the floor; the bowl stands 0.5 m in front of it (toward -Y). The basket
is 0.48 m across and 0.17 m high.
"""

import math

from . import _kitchen
from . import _shed_geo as geo

LIGHTS = []


def build(kit, mats, rng):
    root = kit.group("kitchen_cat_seat")
    straw, burlap = mats["straw"], mats["burlap"]
    basket = [(0.0, 0.0), (0.18, 0.0), (0.225, 0.05), (0.24, 0.13), (0.242, 0.17), (0.228, 0.172), (0.218, 0.13), (0.2, 0.05),
              (0.0, 0.035)]
    _kitchen.lathe(kit, "basket", basket, 20, straw, (0, 0, 0), root, smooth=True)
    for n, z in enumerate((0.05, 0.1, 0.15)):
        kit.torus(f"basket_band_{n}", 0.225 + 0.006 * n, 0.007, (0, 0, z), mat=mats["rope"], major_segments=20,
                  minor_segments=4, parent=root)
    # the sack folded into a cushion, with the dent of a curled-up animal
    _kitchen.blob(kit, "cushion", (0.0, 0.0, 0.1), (0.2, 0.17, 0.05), burlap, root, rot_z=14, segments=12)
    _kitchen.blob(kit, "cushion_dent", (-0.02, 0.01, 0.135), (0.1, 0.08, 0.02), mats["ash"], root, rot_z=30, segments=10)
    fur = geo.Mesh()
    for n in range(10):
        a = rng.uniform(0, 2 * math.pi)
        d = rng.uniform(0.0, 0.09)
        fur.cyl((d * math.cos(a), d * math.sin(a), 0.125), (d * math.cos(a) + 0.02, d * math.sin(a) + 0.02, 0.131), 0.003, sides=3)
    fur.finish("cat_hair", mats["cast_iron"], root)
    # the bowl: red clay, milk to a finger below the rim
    bowl = [(0.0, 0.0), (0.05, 0.0), (0.085, 0.035), (0.1, 0.07), (0.104, 0.076), (0.094, 0.077), (0.08, 0.04), (0.0, 0.015)]
    _kitchen.lathe(kit, "cat_bowl", bowl, 16, mats["clay"], (0.0, -0.46, 0.0), root, smooth=True)
    _kitchen.lathe(kit, "cat_milk", [(0.0, 0.0), (0.075, 0.0)], 16, mats["milk"], (0.0, -0.46, 0.05), root)
    return root

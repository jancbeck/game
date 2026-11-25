"""Flour chest of a garrison kitchen: a plank chest with its lid propped open on a wall, a scoop, a leaning sack, flour on the floor.

Origin: center of the chest's footprint on the floor, its front toward -Y. The chest is 0.8 x 0.5 m and
0.55 m high; the lid is hinged at the back and stands open at 105 degrees. A sack of flour leans on the
left end. Flour is trodden out in front of the chest and dusts the lid and the rim.
"""

import math

from . import _kitchen
from . import _shed_props as props

LIGHTS = []
W, D, H = 0.8, 0.5, 0.55


def build(kit, mats, rng):
    root = kit.group("kitchen_flour")
    wo, wd, iron, flour = mats["wood_old"], mats["wood_dark"], mats["iron"], mats["flour"]
    for n, (x, y) in enumerate(((-W / 2 + 0.04, -D / 2 + 0.04), (W / 2 - 0.04, -D / 2 + 0.04),
                                (-W / 2 + 0.04, D / 2 - 0.04), (W / 2 - 0.04, D / 2 - 0.04))):
        kit.box(f"chest_post_{n}", (0.07, 0.07, H), (x, y, H / 2), mat=wd, bevel=0.006, parent=root)
    for n in range(4):
        kit.box(f"chest_front_{n}", (W, 0.025, H / 4 - 0.006), (0, -D / 2 + 0.0125, H / 8 + n * H / 4), mat=wo, bevel=0.004,
                parent=root)
    kit.box("chest_back", (W, 0.025, H), (0, D / 2 - 0.0125, H / 2), mat=wo, parent=root)
    for s in (-1, 1):
        kit.box(f"chest_side_{s}", (0.025, D, H), (s * (W / 2 - 0.0125), 0, H / 2), mat=wo, parent=root)
    kit.box("chest_floor", (W - 0.05, D - 0.05, 0.03), (0, 0, 0.1), mat=wd, parent=root)
    # flour inside, heaped, a scoop in it
    _kitchen.blob(kit, "flour_heap", (0.0, 0.0, H - 0.1), (0.34, 0.2, 0.12), flour, root, segments=12)
    kit.beam("scoop_handle", (0.05, -0.05, H - 0.04), (0.3, -0.3, H + 0.1), (0.022, 0.016), wo, bevel=0.003, parent=root)
    kit.cylinder("scoop", 0.05, 0.05, (0.0, 0.0, H - 0.06), mat=wo, radius_top=0.065, segments=10, parent=root)
    # the lid, hinged on the back, open
    hinge = kit.group("chest_lid", (0.0, D / 2, H), parent=root)
    hinge.rotation_euler = (math.radians(-105), 0, 0)
    for n in range(3):
        kit.box(f"lid_board_{n}", (W + 0.04, 0.17, 0.03), (0, 0.095 + n * 0.178, 0.0), mat=wo, bevel=0.004, parent=hinge)
    for n, s in enumerate((-1, 1)):
        kit.box(f"lid_batten_{n}", (0.06, D + 0.04, 0.03), (s * 0.28, 0.26, -0.03), mat=wd, parent=hinge)
        kit.box(f"lid_hinge_{n}", (0.1, 0.03, 0.03), (s * 0.28, 0.01, 0.0), mat=iron, parent=hinge)
    _kitchen.blob(kit, "lid_dust", (0.0, 0.3, 0.017), (0.3, 0.16, 0.002), flour, hinge, rot_z=10, segments=12)
    # a sack of flour leaning on the left end, its mouth rolled down
    props.sack(kit, mats, root, "flour_sack", (-W / 2 - 0.3, 0.05, 0.0), rot_z=24, s=1.1)
    for n in range(3):
        _kitchen.blob(kit, f"sack_dust_{n}", (-W / 2 - 0.3 + rng.uniform(-0.08, 0.08), 0.0 + rng.uniform(-0.1, 0.1),
                                              0.37 + 0.02 * n), (0.1, 0.07, 0.01), flour, root, rot_z=rng.uniform(0, 90), segments=8)
    # flour trodden out on the floor in front, with a few footprints worn through it
    _kitchen.scatter_blobs(kit, rng, "flour_floor", flour, root, (0.0, -0.55), (0.35, 0.18), 12, (0.04, 0.12), 0.004)
    return root

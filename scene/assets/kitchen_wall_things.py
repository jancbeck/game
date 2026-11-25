"""Things on the wall by the oven: a rail of drying herbs, a braid of garlic, and a broom against the wall.

Origin: the middle of the rail on the wall face at floor level; the wall is the XZ plane at y = 0 and lies
toward +Y, the room toward -Y. The rail is 0.9 m long at 2.0 m. The broom leans at x = +0.72, head on the
floor 0.25 m from the wall, handle tip against the wall at 1.5 m.
"""

import math

from . import _shed_geo as geo
from . import _kitchen

LIGHTS = []


def build(kit, mats, rng):
    root = kit.group("kitchen_wall_things")
    wd, wo, iron = mats["wood_dark"], mats["wood_old"], mats["iron"]
    z = 2.0
    kit.beam("herb_rail", (-0.45, -0.07, z), (0.45, -0.07, z), (0.05, 0.05), wd, bevel=0.006, parent=root)
    for n, s in enumerate((-1, 1)):
        kit.box(f"herb_rail_bracket_{n}", (0.04, 0.09, 0.04), (s * 0.43, -0.03, z - 0.01), mat=iron, parent=root)
    p = _kitchen.Provisions(rng)
    for x, kind in ((-0.35, "herbs"), (-0.12, "herbs"), (0.1, "onions"), (0.3, "herbs")):
        if kind == "herbs":
            p.herbs(x, -0.1, z - 0.02)
        else:
            p.onions(x, -0.1, z - 0.02, 7)
    p.finish(mats, root)
    # a braid of garlic lower down
    garlic = geo.Mesh()
    for n in range(7):
        garlic.ellipsoid((0.0 + (0.02 if n % 2 else -0.02), -0.12, 1.75 - 0.065 * n), (0.04, 0.04, 0.036), segments=7)
    garlic.finish("garlic", mats["crumb"], root, smooth=True)
    kit.cylinder("garlic_cord", 0.007, 0.5, (0.0, -0.12, 1.55), mat=mats["rope"], segments=5, parent=root)
    # the broom: a long ash handle, a bundle of birch twigs bound with withy
    kit.beam("broom_handle", (0.72, -0.25, 0.28), (0.76, -0.04, 1.5), (0.03, 0.03), wo, bevel=0.004, parent=root)
    twigs = geo.Mesh()
    for n in range(26):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.0, 0.07)
        twigs.cyl((0.72 + r * math.cos(a) * 0.4, -0.25 + r * math.sin(a) * 0.4, 0.3),
                  (0.72 + r * math.cos(a) * 2.2, -0.25 + r * math.sin(a) * 2.2 - 0.02, 0.0), 0.006, 0.004, sides=4)
    twigs.finish("broom_twigs", mats["straw"], root)
    kit.torus("broom_bind", 0.04, 0.007, (0.72, -0.25, 0.3), mat=mats["rope"], major_segments=10, minor_segments=4, parent=root)
    return root

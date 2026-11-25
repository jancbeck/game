"""An iron-bound chest at the foot of the bed in the commander's chamber: oak planks, a domed lid, three iron bands, a hasp and a padlock, a folded cloak on top.

1.0 m long along X, 0.5 m deep, 0.42 m to the lid's rim and 0.67 m to its crown. Origin: the middle of the chest on the floor,
the front toward -Y.
"""

from . import _kitchen
from . import _tower as T

LIGHTS = []
L, D, H = 1.0, 0.5, 0.42


def build(kit, mats, rng):
    root = kit.group("tower_chest")
    wo, wd, iron = mats["wood_old"], mats["wood_dark"], mats["iron"]
    kit.box("chest_body", (L, D, H - 0.06), (0, 0, 0.06 + (H - 0.06) / 2), mat=wo, bevel=0.01, parent=root)
    kit.box("chest_plinth", (L + 0.04, D + 0.04, 0.06), (0, 0, 0.03), mat=wd, bevel=0.006, parent=root)
    T.half_cyl(kit, "chest_lid", L + 0.02, D / 2 + 0.01, H, wo, root, axis="x", segments=14)
    for n, x in enumerate((-0.4, 0.0, 0.4)):
        T.half_cyl(kit, f"lid_band_{n}", 0.05, D / 2 + 0.018, H, iron, root, axis="x", loc=(x, 0.0), segments=14)
        kit.box(f"body_band_{n}", (0.05, D + 0.022, H - 0.06), (x, 0, 0.06 + (H - 0.06) / 2), mat=iron, parent=root)
    kit.box("hasp", (0.07, 0.014, 0.16), (0, -D / 2 - 0.02, H - 0.04), mat=iron, parent=root)
    kit.box("lock", (0.09, 0.04, 0.08), (0, -D / 2 - 0.025, H - 0.17), mat=mats["cast_iron"], bevel=0.006, parent=root)
    kit.torus("lock_shackle", 0.022, 0.005, (0, -D / 2 - 0.025, H - 0.12), (90, 0, 0), mats["cast_iron"], major_segments=10,
              minor_segments=4, parent=root)
    for n, s in enumerate((-1, 1)):
        kit.torus(f"handle_{n}", 0.05, 0.007, (s * (L / 2 + 0.02), 0, 0.28), (0, 90, 0), iron, major_segments=12,
                  minor_segments=4, parent=root)
        for dx, dy in ((0.0, 0.0),):
            kit.box(f"corner_{n}", (0.03, D + 0.03, 0.05), (s * (L / 2 - 0.02), 0, 0.09), mat=iron, parent=root)
    # a folded cloak on the lid
    kit.box("cloak", (0.5, 0.34, 0.08), (0.17, 0.0, H + D / 2 + 0.02), (0, 0, 6), mats["wool"], bevel=0.025, parent=root)
    kit.box("cloak_fold", (0.46, 0.3, 0.05), (0.17, 0.0, H + D / 2 + 0.085), (0, 0, 2), mats["wool"], bevel=0.02, parent=root)
    return root

"""Work table of a garrison kitchen with two stools: dough and flour, a loaf with slices cut, bowls, onions, a jug.

1.7 x 0.85 m, top at 0.9 m, scrubbed pale along the middle and black at the edges, long side along X.
Origin: center of the table on the floor. One stool at each long side, the north one pulled in so the aisle in front of the hearth stays clear. On the top, west to east: a
board with a cut loaf and its slices, a dusting of flour with a ball of dough and a rolling pin, a
bowl with onions, a pot with a wooden spoon, a jug and a cleaver.
"""

from . import _kitchen
from . import _shed_geo as geo
from . import _shed_props as props

LIGHTS = []
L, D, TOP = 1.7, 0.85, 0.9


def build(kit, mats, rng):
    root = kit.group("kitchen_table")
    wo, wd, iron = mats["wood_old"], mats["wood_dark"], mats["iron"]
    for n, (px, py) in enumerate(((-L / 2 + 0.09, -D / 2 + 0.08), (L / 2 - 0.09, -D / 2 + 0.08),
                                  (-L / 2 + 0.09, D / 2 - 0.08), (L / 2 - 0.09, D / 2 - 0.08))):
        kit.beam(f"table_leg_{n}", (px, py, 0.0), (px + rng.uniform(-0.008, 0.008), py, TOP - 0.04), (0.1, 0.1), wd,
                 bevel=0.008, parent=root)
    for n, y in enumerate((-D / 2 + 0.08, D / 2 - 0.08)):
        kit.box(f"table_rail_{n}", (L - 0.1, 0.05, 0.11), (0, y, TOP - 0.1), mat=wd, bevel=0.006, parent=root)
    for n, x in enumerate((-L / 2 + 0.09, L / 2 - 0.09)):
        kit.box(f"table_end_rail_{n}", (0.05, D - 0.16, 0.11), (x, 0, TOP - 0.1), mat=wd, bevel=0.006, parent=root)
    kit.box("table_shelf", (L - 0.2, D - 0.18, 0.03), (0, 0, 0.3), mat=wo, bevel=0.005, parent=root)
    y = -D / 2 - 0.01
    for n, w_ in enumerate((0.2, 0.21, 0.2, 0.21)):
        kit.box(f"table_top_{n}", (L + 0.05, w_, 0.045), (0, y + w_ / 2, TOP),
                (rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0), mats["scrubbed"] if n in (1, 2) else wd, bevel=0.008,
                parent=root)
        y += w_ + 0.012
    zt = TOP + 0.0225

    # on the shelf under the table: a crock and a pot
    props.jar(kit, mats, root, "shelf_crock", (-0.5, 0.0, 0.315), 0.1, 0.24)
    props.pot(kit, mats, root, "shelf_pot", (0.3, 0.05, 0.315), 0.11, 0.15)

    # west end: a board with a cut loaf, its slices, a knife
    kit.box("cutting_board", (0.46, 0.3, 0.035), (-0.62, 0.05, zt + 0.0175), (0, 0, 6), wd, bevel=0.006, parent=root)
    bz = zt + 0.035
    _kitchen.blob(kit, "loaf", (-0.7, 0.07, bz + 0.055), (0.15, 0.09, 0.06), mats["crust"], root, rot_z=8, segments=12)
    _kitchen.blob(kit, "loaf_cut", (-0.55, 0.06, bz + 0.052), (0.012, 0.085, 0.05), mats["crumb"], root, rot_z=8,
                  segments=10)
    for n, dx in enumerate((-0.5, -0.455, -0.41)):
        _kitchen.blob(kit, f"slice_{n}", (dx, 0.05 + 0.01 * n, bz + 0.01 + 0.012 * n), (0.075, 0.075, 0.009),
                      mats["crumb"], root, rot_z=rng.uniform(0, 60), segments=10)
    kit.box("table_knife", (0.22, 0.02, 0.008), (-0.38, -0.18, bz + 0.004), (0, 0, -25), iron, parent=root)

    # middle: flour dusted on the boards, a ball of dough, a rolling pin
    _kitchen.blob(kit, "flour_dust", (0.0, 0.02, zt + 0.0015), (0.2, 0.15, 0.0016), mats["flour"], root, rot_z=14,
                  segments=14)
    _kitchen.blob(kit, "flour_dust_b", (-0.12, -0.2, zt + 0.0015), (0.08, 0.05, 0.0016), mats["flour"], root, rot_z=-30,
                  segments=10)
    _kitchen.blob(kit, "dough", (0.02, 0.06, zt + 0.045), (0.12, 0.1, 0.05), mats["flour"], root, segments=12)
    kit.cylinder("rolling_pin", 0.024, 0.34, (0.12, -0.15, zt + 0.024), (0, 90, 4), wo, segments=8, parent=root)

    # east end: a bowl of onions, a pot with a spoon, a jug, a cleaver and a cloth
    props.bowl(kit, mats, root, "table_bowl_a", (0.5, 0.2, zt), 0.13, 0.08)
    onions = geo.Mesh()
    for n in range(5):
        onions.ellipsoid((0.5 + rng.uniform(-0.07, 0.07), 0.2 + rng.uniform(-0.06, 0.06), zt + 0.1 + 0.02 * (n % 2)),
                         (0.05, 0.05, 0.043), segments=8)
    onions.finish("table_onions", mats["straw"], root, smooth=True)
    props.bowl(kit, mats, root, "table_bowl_b", (0.58, -0.22, zt), 0.1, 0.07)
    props.pot(kit, mats, root, "table_pot", (0.3, -0.25, zt), 0.1, 0.14)
    kit.beam("table_spoon", (0.3, -0.25, zt + 0.08), (0.36, -0.12, zt + 0.3), (0.016, 0.016), wo, bevel=0.002, parent=root)
    props.jar(kit, mats, root, "table_jug", (0.78, 0.0, zt), 0.06, 0.24, covered=False)
    kit.box("table_cleaver", (0.15, 0.012, 0.1), (0.78, -0.3, zt + 0.07), (0, 0, 12), iron, parent=root)
    kit.box("table_cloth", (0.3, 0.22, 0.012), (0.58, 0.02, zt + 0.006), (0, 0, -8), mats["cloth_emblem"], parent=root)

    # a stool at each long side
    props.stool(kit, mats, rng, root, "stool_a", -0.15, -0.72)
    props.stool(kit, mats, rng, root, "stool_b", 0.55, 0.62)
    return root

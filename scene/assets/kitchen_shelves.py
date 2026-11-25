"""Wall shelves of a garrison kitchen: two boards on brackets with crocks, bowls, pots and a salt box.

Origin: center of the unit on the wall face at floor level; the wall is the XZ plane at y = 0 and
lies toward +Y, the shelves stand out toward -Y. 1.5 m wide, boards at 1.15 m and 1.7 m, 0.28 m deep.
"""

from . import _shed_props as props

LIGHTS = []
W, D = 1.5, 0.28


def build(kit, mats, rng):
    root = kit.group("kitchen_shelves")
    wo, wd, iron = mats["wood_old"], mats["wood_dark"], mats["iron"]
    for n, z in enumerate((1.15, 1.7)):
        kit.box(f"shelf_{n}", (W, D, 0.04), (0, -D / 2, z), (0, 0, rng.uniform(-0.3, 0.3)), wo, bevel=0.005, parent=root)
        for k, x in enumerate((-W / 2 + 0.12, W / 2 - 0.12)):
            kit.box(f"shelf_{n}_bracket_{k}", (0.05, D - 0.04, 0.05), (x, -D / 2, z - 0.07), mat=wd, parent=root)
            kit.beam(f"shelf_{n}_brace_{k}", (x, -D + 0.05, z - 0.03), (x, -0.03, z - 0.28), (0.04, 0.04), wd, parent=root)
    zt = 1.17
    props.jar(kit, mats, root, "crock_a", (-0.58, -0.14, zt), 0.08, 0.2)
    props.jar(kit, mats, root, "crock_b", (-0.36, -0.15, zt), 0.07, 0.17)
    props.jar(kit, mats, root, "crock_c", (-0.14, -0.14, zt), 0.065, 0.22, covered=False)
    props.pot(kit, mats, root, "shelf_pot", (0.2, -0.14, zt), 0.1, 0.14)
    props.bowl(kit, mats, root, "shelf_bowl_a", (0.5, -0.14, zt), 0.1, 0.07)
    props.bowl(kit, mats, root, "shelf_bowl_b", (0.5, -0.14, zt + 0.07), 0.095, 0.07)
    kit.box("salt_box", (0.2, 0.14, 0.16), (0.62, -0.14, 1.72 + 0.1), (0, 0, 6), wo, bevel=0.006, parent=root)
    props.bowl(kit, mats, root, "shelf_bowl_c", (-0.5, -0.14, 1.72), 0.1, 0.07)
    props.bowl(kit, mats, root, "shelf_bowl_d", (-0.5, -0.14, 1.79), 0.095, 0.07)
    props.jar(kit, mats, root, "crock_d", (-0.18, -0.14, 1.72), 0.075, 0.2)
    props.jar(kit, mats, root, "crock_e", (0.12, -0.15, 1.72), 0.07, 0.16)
    kit.cylinder("tallow", 0.05, 0.1, (0.3, -0.14, 1.77), mat=mats["straw"], segments=10, parent=root)
    return root

"""Larder of a garrison cookhouse: hams, sausages and onions on a pole, a plank bench with cheeses and crocks, a stack of crocks.

Origin: the middle of the larder floor (x 3.8 .. 6.6 in the plan, so the plan puts it at x = 5.2, y = 0).
The pole runs along X at y = +0.75 and z = 2.6 (everything on it hangs above head height, 1.8 m, so it is no obstacle to the walk) between the partition and the east wall, which carry it
(it is 2.8 m long). A bench 0.45 m deep stands against the east wall (local x = +1.4 is the wall face);
crocks stand two high at the south end of the west side.
"""

from . import _kitchen, _lights
from . import _shed_props as props

LIGHTS = []
POLE_Y, POLE_Z = 0.75, 2.6
# dusk through the window above the shelves, spread over the room (the window's own light is a narrow beam)
DUSK = dict(pos=(0.9, 1.0, 2.1), color=(0.45, 0.6, 1.0), watts=70.0, radius=0.5, specular=0.0, reach=5.0)


def build(kit, mats, rng):
    root = kit.group("kitchen_larder")
    _lights.add(root, "kitchen_larder_dusk", **DUSK)
    wd, wo, iron = mats["wood_dark"], mats["wood_old"], mats["iron"]
    kit.beam("larder_pole", (-1.4, POLE_Y, POLE_Z), (1.4, POLE_Y, POLE_Z - 0.01), (0.07, 0.07), wd, bevel=0.008, parent=root)
    p = _kitchen.Provisions(rng)
    zt = POLE_Z - 0.04
    for x, kind, s in ((-1.25, "ham", 1.0), (-1.0, "sausages", 1), (-0.72, "ham", 0.9), (-0.45, "onions", 1),
                       (-0.2, "ham", 1.05), (0.05, "herbs", 1), (0.3, "ham", 0.95), (0.55, "sausages", 1),
                       (0.8, "ham", 1.0), (1.05, "onions", 1), (1.27, "herbs", 1)):
        if kind == "ham":
            p.ham(x, POLE_Y, zt, s)
        elif kind == "sausages":
            p.sausages(x, POLE_Y, zt)
        elif kind == "herbs":
            p.herbs(x, POLE_Y, zt)
        else:
            p.onions(x, POLE_Y, zt, 8)
    p.finish(mats, root)

    # bench along the east wall: plank top on trestles, cheese wheels, crocks with cloth, a ham bone
    bx, by, bw, bd, bz = 1.15, -0.2, 0.45, 1.9, 0.5
    for n, y in enumerate((by - bd / 2 + 0.15, by + bd / 2 - 0.15)):
        kit.box(f"bench_trestle_{n}", (bw - 0.06, 0.06, bz), (bx, y, bz / 2), mat=wd, bevel=0.006, parent=root)
    for n in range(3):
        kit.box(f"bench_top_{n}", (bw / 3 - 0.006, bd, 0.04), (bx - bw / 3 + n * bw / 3, by, bz + 0.02), mat=wo, bevel=0.005,
                parent=root)
    zb = bz + 0.04
    for n, (y, r, h) in enumerate(((0.45, 0.17, 0.07), (0.45, 0.15, 0.06), (0.1, 0.16, 0.07))):
        z = zb + (0.07 if n == 1 else 0.0)
        kit.cylinder(f"cheese_{n}", r, h, (bx - 0.05, y if n != 2 else y - 0.1, z + h / 2), mat=mats["cheese"], segments=16,
                     bevel=0.01, parent=root)
    props.jar(kit, mats, root, "bench_crock_a", (bx, -0.35, zb), 0.09, 0.22)
    props.jar(kit, mats, root, "bench_crock_b", (bx - 0.05, -0.62, zb), 0.1, 0.26)
    props.jar(kit, mats, root, "bench_crock_c", (bx, -0.88, zb), 0.085, 0.2, covered=False)
    props.bowl(kit, mats, root, "bench_bowl", (bx - 0.02, -0.15, zb), 0.1, 0.07)

    # crocks stacked at the south end of the west side
    for n, (x, y, r, h) in enumerate(((-1.2, -1.4, 0.13, 0.34), (-0.9, -1.45, 0.12, 0.3), (-1.05, -1.2, 0.11, 0.28))):
        props.jar(kit, mats, root, f"floor_crock_{n}", (x, y, 0.0), r, h)
    props.jar(kit, mats, root, "floor_crock_top", (-1.18, -1.38, 0.34), 0.1, 0.2)

    return root

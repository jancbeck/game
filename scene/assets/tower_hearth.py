"""The small wall hearth of the commander's chamber, under a masonry hood and a stack that rises through the thickness of the back wall.

Origin: the middle of the hearth on the wall face at floor level; the wall (0.75 m thick) lies toward +Y,
the room toward -Y.

- A raised hearth stone 0.95 m wide and 0.55 m deep, a hood on two jambs and a timber lintel, tapering into a
  flue 0.6 x 0.5 m that climbs inside the wall and stands about 0.35 m over the 2.8 m wall top, with a sooty crown.
- The fire: three charred logs on firedogs over a bed of coals, three tongues of flame, an iron fireback.
  A small iron kettle hangs over it on a chain from the lintel; tongs and a poker lean on the jamb.
- Two warm point lights placed through _lights, with a low specular: one in the fire and one in front of the hearth.
  They are the room's warmest light, and the dimmest: a fire kept low by a man who counts his firewood.
- A wisp of steam off the kettle and smoke over the crown.
"""

import math

from . import _fire, _kitchen, _lights, _soot
from . import _shed_geo as geo

LIGHTS = []
LIGHT = dict(pos=(0.0, -0.3, 0.42), color=(1.0, 0.36, 0.07), watts=130.0, radius=0.12, specular=0.06, reach=7.0)
LIGHT_FLOOR = dict(pos=(0.0, -1.2, 0.4), color=(1.0, 0.33, 0.06), watts=32.0, radius=0.3, specular=0.04, reach=5.0)

W = 0.95                     # firebox width
DEPTH = 0.55
BASE = 0.16                  # height of the hearth stone
STACK_TOP = 3.15
FIRE = (0.0, -0.3, BASE + 0.06)


def build(kit, mats, rng):
    root = kit.group("tower_hearth")
    st, wd, iron = mats["stone_wall"], mats["wood_dark"], mats["iron"]
    from .gate_door import _dressed
    cut = _dressed(st)
    _lights.add(root, "tower_hearth", **LIGHT)
    _lights.add(root, "tower_hearth_floor", **LIGHT_FLOOR)
    fx, fy, fz = FIRE

    kit.box("hearth_base", (W + 0.5, DEPTH + 0.15, BASE), (0, -(DEPTH + 0.15) / 2, BASE / 2), mat=cut, bevel=0.015, parent=root)
    for n, s in enumerate((-1, 1)):
        kit.box(f"hood_jamb_{n}", (0.22, 0.26, 1.2), (s * (W / 2 + 0.11), -DEPTH + 0.13, BASE + 0.6), mat=st, bevel=0.012,
                parent=root)
    kit.box("hood_lintel", (W + 0.46, 0.24, 0.17), (0, -DEPTH + 0.12, BASE + 1.2 + 0.085), mat=wd, bevel=0.01, parent=root)
    z0 = BASE + 1.29
    hood = geo.Mesh()
    hood.prism(geo.rect(-W / 2 - 0.22, W / 2 + 0.22, -DEPTH, 0.0, z0), geo.rect(-0.3, 0.3, -0.32, 0.0, 2.45))
    hood.finish("hood", st, root, bevel=0.01)
    # the flue climbs inside the wall and shows over its top: bands, a corbelled crown
    kit.box("stack_shaft", (0.62, 0.7, STACK_TOP - 2.4), (0, 0.35, (STACK_TOP + 2.4) / 2), mat=st, bevel=0.01, parent=root)
    kit.box("stack_band", (0.72, 0.8, 0.09), (0, 0.4, 3.0), mat=cut, bevel=0.01, parent=root)
    kit.box("stack_corbel", (0.76, 0.84, 0.12), (0, 0.4, STACK_TOP - 0.06), mat=cut, bevel=0.008, parent=root)
    kit.box("crown_front", (0.7, 0.16, 0.2), (0, 0.0, STACK_TOP + 0.1), mat=cut, bevel=0.008, parent=root)
    kit.box("crown_back", (0.7, 0.2, 0.34), (0, 0.8, STACK_TOP + 0.17), mat=cut, bevel=0.008, parent=root)
    for n, s in enumerate((-1, 1)):
        kit.box(f"crown_side_{n}", (0.16, 0.5, 0.28), (s * 0.27, 0.4, STACK_TOP + 0.14), mat=cut, bevel=0.008, parent=root)
    kit.box("flue_floor", (0.38, 0.5, 0.02), (0, 0.4, STACK_TOP + 0.01), mat=wd, parent=root)
    _soot.plume(kit, root, "wall_soot", (0.0, -0.01, z0), 1.1, 1.0, strength=0.65)
    kit.box("fireback", (0.85, 0.04, 0.6), (0, -0.03, BASE + 0.35), mat=iron, bevel=0.006, parent=root)

    # fire: three charred logs on two firedogs, a low bed of coals, three tongues of flame
    coal, ash = _kitchen.coal_material(mats), mats["ash"]
    for n, s_ in enumerate((-1, 1)):
        kit.box(f"firedog_{n}", (0.04, 0.4, 0.04), (s_ * 0.26, fy, fz - 0.01), mat=mats["cast_iron"], bevel=0.005, parent=root)
        kit.box(f"firedog_post_{n}", (0.04, 0.04, 0.16), (s_ * 0.26, fy - 0.2, fz + 0.07), mat=mats["cast_iron"], bevel=0.005,
                parent=root)
    logs = geo.Mesh()
    for p0, p1 in (((-0.3, fy - 0.07, fz + 0.04), (0.3, fy + 0.1, fz + 0.06)), ((-0.22, fy + 0.15, fz + 0.04), (0.25, fy - 0.08, fz + 0.06)),
                   ((-0.05, fy - 0.12, fz + 0.1), (0.05, fy + 0.18, fz + 0.12))):
        logs.cyl(p0, p1, 0.045, 0.04, sides=7)
    logs.finish("hearth_logs", mats["wood_dark"], root)
    kit.sphere("hearth_coals", 0.22, (fx, fy, fz - 0.03), scale=(1.0, 0.8, 0.3), mat=coal, segments=16, parent=root)
    kit.sphere("hearth_ash_bed", 0.36, (fx, fy, fz - 0.07), scale=(1.0, 0.8, 0.12), mat=ash, segments=14, parent=root)
    fire = mats["fire"]
    for n, (dx, dy, h, r, lean) in enumerate(((-0.06, -0.02, 0.46, 0.09, (0.0, 0.14)), (0.11, 0.04, 0.36, 0.08, (0.04, 0.12)),
                                              (-0.02, -0.08, 0.28, 0.07, (-0.02, 0.08)))):
        _fire.flame(kit, fire, root, f"hearth_flame_{n}", (fx + dx, fy + dy, fz + 0.05), h, r, lean=lean,
                    twist=1.2 + n * 0.4, phase=n * 2.1)

    # a small iron kettle on a chain from the lintel, tongs and a poker on the jamb
    cx, cy = 0.0, fy
    kit.beam("lug_pole", (-0.7, cy, BASE + 1.18), (0.7, cy, BASE + 1.18), (0.03, 0.03), iron, bevel=0.004, parent=root)
    for n in range(5):
        kit.torus(f"chain_link_{n}", 0.02, 0.005, (cx, cy, BASE + 1.14 - 0.06 * n), (90 * (n % 2), 90 * ((n + 1) % 2), 0), iron,
                  major_segments=10, minor_segments=4, parent=root)
    kz = BASE + 0.72
    _kitchen.lathe(kit, "kettle", [(0.0, 0.0), (0.08, 0.0), (0.15, 0.04), (0.17, 0.12), (0.15, 0.2), (0.1, 0.235), (0.07, 0.25),
                                   (0.0, 0.25)], 20, mats["cast_iron"], (cx, cy, kz), root)
    kit.torus("kettle_bail", 0.16, 0.005, (cx, cy, kz + 0.2), (90, 0, 0), mats["cast_iron"], major_segments=16, minor_segments=4,
              parent=root)
    kit.beam("kettle_spout", (cx + 0.14, cy, kz + 0.1), (cx + 0.25, cy, kz + 0.22), (0.03, 0.03), mats["cast_iron"], parent=root)
    kit.beam("poker", (0.62, -DEPTH - 0.02, BASE + 0.1), (0.6, -DEPTH + 0.12, 1.0), (0.014, 0.014), iron, parent=root)
    kit.beam("fire_tongs", (0.7, -DEPTH - 0.02, BASE + 0.1), (0.72, -DEPTH + 0.1, 0.95), (0.018, 0.01), iron, parent=root)
    # ash raked onto the hearth stone and the boards, a split log and a few sticks beside the hearth
    _kitchen.scatter_blobs(kit, rng, "ash_on_floor", ash, root, (0.0, -0.95), (0.4, 0.12), 10, (0.03, 0.08), 0.004, z=0.04)
    wood = geo.Mesh()
    for k in range(4):
        wood.cyl((-0.82, -0.3 - 0.13 * k, 0.07), (-0.82 + rng.uniform(-0.05, 0.05), -0.62 - 0.13 * k, 0.07 + 0.02 * (k % 2)),
                 0.045, 0.04, sides=6)
    wood.finish("firewood", mats["wood_old"], root)

    _fire.smoke(kit, mats["smoke"], root, "kettle_steam", base=(cx + 0.18, cy, kz + 0.26), rise=0.45, drift=0.8, r0=0.07,
                r1=0.25, density=0.8, seed=rng.uniform(0, 50))
    _fire.smoke(kit, mats["smoke"], root, "chimney_smoke", base=(0.0, 0.4, STACK_TOP + 0.35), rise=1.4, drift=2.0, r0=0.2, r1=1.1,
                density=1.3, seed=rng.uniform(0, 50))
    _fire.sparks(kit, mats["embers"], root, "chimney_sparks", rng, 3, (0.0, 0.4, STACK_TOP + 0.3), 1.2, 0.06, (0.9, 0.2), 0.03)
    return root

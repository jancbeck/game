"""Open hearth of a garrison kitchen, against a wall, under a masonry hood and a chimney stack.

Origin: center of the hearth on the wall face at floor level. The wall face is the XZ plane at y = 0
and the wall (at least 0.8 m thick) lies toward +Y; the room is toward -Y. Place it with rot_z 0
against a wall that faces south.

- A raised stone hearth 1.9 m wide and 1.1 m deep, a hood on two jambs and a timber lintel
  that tapers into a stack. The stack climbs the wall (inside its thickness) and stands 0.8 m over a
  3.2 m wall, with a sooty crown and a plume of smoke above it.
- The fire: charred logs on firedogs over a bed of coals, four tongues of flame, an iron fireback.
  A cast-iron cauldron hangs over it on a chain from an iron bar across the hood, a ladle leaning
  on its rim; tongs and a poker lean on the right jamb.
- A wisp of steam rises off the soup.
- Two warm point lights placed through _lights with a low specular so that the stone does not
  mirror them: one in the fire, under the cauldron, and one in front of the hearth that spreads
  the glow over the floor. They are the kitchen's main light.
"""

import math

from . import _fire, _kitchen, _lights
from . import _shed_geo as geo
from . import _soot

LIGHTS = []
LIGHT = dict(pos=(0.0, -0.62, 0.5), color=(1.0, 0.36, 0.07), watts=300.0, radius=0.16, specular=0.25, reach=9.0)
LIGHT_FLOOR = dict(pos=(0.0, -1.7, 0.45), color=(1.0, 0.33, 0.06), watts=90.0, radius=0.35, specular=0.08, reach=6.5)

W = 1.9                      # hearth width
DEPTH = 1.1
STACK_TOP = 4.0
FIRE = (0.0, -0.55, 0.3)     # center of the coal bed


def build(kit, mats, rng):
    root = kit.group("kitchen_hearth")
    st, wd, iron = mats["stone_wall"], mats["wood_dark"], mats["iron"]
    from .gate_door import _dressed
    cut = _dressed(st)
    embers, fire = mats["embers"], mats["fire"]
    _lights.add(root, "kitchen_hearth", **LIGHT)
    _lights.add(root, "kitchen_hearth_floor", **LIGHT_FLOOR)
    fx, fy, fz = FIRE

    kit.box("hearth_base", (W, DEPTH, 0.26), (0, -DEPTH / 2, 0.13), mat=st, bevel=0.02, parent=root)
    for n, s in enumerate((-1, 1)):
        kit.box(f"hood_jamb_{n}", (0.26, 0.28, 1.29), (s * (W / 2 + 0.06), -DEPTH + 0.14, 0.26 + 0.645), mat=st,
                bevel=0.015, parent=root)
    kit.box("hood_lintel", (W + 0.46, 0.24, 0.2), (0, -DEPTH + 0.14, 1.64), mat=wd, bevel=0.012, parent=root)
    hood = geo.Mesh()
    hood.prism(geo.rect(-W / 2 - 0.2, W / 2 + 0.2, -DEPTH - 0.02, 0.0, 1.74),
               geo.rect(-0.45, 0.45, -0.42, 0.0, 2.75))
    hood.finish("hood", st, root, bevel=0.012)
    # the stack: a shaft through the wall's thickness, cut stone bands, a corbelled crown
    kit.box("stack_shaft", (0.9, 1.17, STACK_TOP - 2.7), (0, 0.235, (STACK_TOP + 2.7) / 2), mat=st, bevel=0.012,
            parent=root)
    for n, z in enumerate((3.55, 4.05)):
        kit.box(f"stack_band_{n}", (1.0, 1.28, 0.1), (0, 0.235, z), mat=cut, bevel=0.012, parent=root)
    kit.box("stack_corbel", (1.06, 1.34, 0.14), (0, 0.235, STACK_TOP - 0.07), mat=cut, bevel=0.008, parent=root)
    kit.box("crown_front", (1.0, 0.22, 0.26), (0, -0.28, STACK_TOP + 0.13), mat=cut, bevel=0.008, parent=root)
    kit.box("crown_back", (1.0, 0.3, 0.5), (0, 0.72, STACK_TOP + 0.25), mat=cut, bevel=0.008, parent=root)
    for n, s in enumerate((-1, 1)):
        kit.box(f"crown_side_{n}", (0.26, 0.7, 0.4), (s * 0.37, 0.225, STACK_TOP + 0.2), mat=cut, bevel=0.008,
                parent=root)
    kit.box("flue_floor", (0.48, 0.66, 0.02), (0, 0.225, STACK_TOP + 0.01), mat=wd, parent=root)
    for n, (dx, w, drop) in enumerate(((-0.3, 0.08, 0.7), (-0.1, 0.1, 0.35), (0.08, 0.07, 0.9), (0.25, 0.09, 0.5))):
        kit.box(f"soot_{n}", (w, 0.012, drop), (dx, -0.43, 2.72 - drop / 2), mat=wd, parent=root)
    _soot.plume(kit, root, "wall_soot", (0.0, -0.01, 1.74), 1.5, 1.3, strength=0.7)
    # iron fireback against the wall, behind the fire
    kit.box("fireback", (1.3, 0.04, 0.8), (0, -0.03, 0.66), mat=iron, bevel=0.006, parent=root)

    # fire: charred logs on two firedogs, a low bed of coals that glows in spots, tongues of flame
    coal = _kitchen.coal_material(mats)
    ash = mats["ash"]
    for n, s_ in enumerate((-1, 1)):
        kit.box(f"firedog_{n}", (0.04, 0.62, 0.05), (s_ * 0.34, fy, fz - 0.01), mat=mats["cast_iron"], bevel=0.006, parent=root)
        kit.box(f"firedog_post_{n}", (0.05, 0.05, 0.2), (s_ * 0.34, fy - 0.3, fz + 0.09), mat=mats["cast_iron"], bevel=0.006,
                parent=root)
    logs = geo.Mesh()
    for p0, p1 in (((-0.4, fy - 0.1, 0.34), (0.4, fy + 0.15, 0.37)), ((-0.3, fy + 0.22, 0.34), (0.34, fy - 0.12, 0.36)),
                   ((-0.06, fy - 0.17, 0.42), (0.06, fy + 0.27, 0.46))):
        logs.cyl(p0, p1, 0.058, 0.05, sides=7)
    logs.finish("hearth_logs", mats["wood_dark"], root)
    kit.sphere("hearth_coals", 0.3, (fx, fy, fz - 0.03), scale=(1.0, 0.82, 0.3), mat=coal, segments=16, parent=root)
    kit.sphere("hearth_ash_bed", 0.5, (fx, fy, fz - 0.08), scale=(1.0, 0.8, 0.12), mat=ash, segments=14, parent=root)
    for n, (dx, dy, h, r, lean) in enumerate(((-0.08, -0.02, 0.62, 0.12, (0.0, 0.14)), (0.14, 0.05, 0.5, 0.11, (0.04, 0.12)),
                                              (0.0, -0.1, 0.38, 0.09, (-0.02, 0.08)), (-0.2, 0.06, 0.3, 0.08, (-0.06, 0.1)))):
        _fire.flame(kit, fire, root, f"hearth_flame_{n}", (fx + dx, fy + dy, fz + 0.05), h, r, lean=lean,
                    twist=1.2 + n * 0.4, phase=n * 2.1)

    # cauldron: cast iron on a chain from an iron bar across the hood, soup nearly to the brim, a ladle on the rim
    cx, cy = 0.0, fy
    iron, cast = mats["iron"], mats["cast_iron"]
    kit.beam("lug_pole", (-1.0, cy, 1.725), (1.0, cy, 1.725), (0.035, 0.035), iron, bevel=0.004, parent=root)
    top = 1.72
    n_links = 6
    for n in range(n_links):
        kit.torus(f"chain_link_{n}", 0.024, 0.006, (cx, cy, top - 0.045 - 0.065 * n),
                  (90 * (n % 2), 90 * ((n + 1) % 2), 0), iron, major_segments=10, minor_segments=4, parent=root)
    pot_z = 0.64
    pot = [(0.0, 0.0), (0.12, 0.0), (0.22, 0.04), (0.28, 0.13), (0.30, 0.24), (0.29, 0.34), (0.278, 0.385),
           (0.27, 0.395), (0.258, 0.39), (0.262, 0.34), (0.0, 0.34)]
    _kitchen.lathe(kit, "cauldron", pot, 24, cast, (cx, cy, pot_z), root)
    _kitchen.lathe(kit, "cauldron_broth", [(0.0, 0.0), (0.24, -0.002), (0.26, 0.004)], 24, mats["broth"],
                   (cx, cy, pot_z + 0.348), root)
    kit.torus("cauldron_rim", 0.272, 0.014, (cx, cy, pot_z + 0.392), mat=cast, major_segments=24, minor_segments=5, parent=root)
    for n, s_ in enumerate((-1, 1)):
        kit.sphere(f"cauldron_lug_{n}", 0.022, (cx + s_ * 0.285, cy, pot_z + 0.36), mat=cast, segments=8, parent=root)
    kit.torus("cauldron_bail", 0.285, 0.0065, (cx, cy, pot_z + 0.36), (90, 0, 0), cast, major_segments=18, minor_segments=4,
              parent=root)
    # a few lumps of pease and fat afloat, a wooden ladle leaning on the rim
    lumps = geo.Mesh()
    for n in range(9):
        a, d = rng.uniform(0, 2 * math.pi), rng.uniform(0.02, 0.2)
        lumps.ellipsoid((cx + d * math.cos(a), cy + d * math.sin(a), pot_z + 0.352), (0.022, 0.02, 0.008), segments=6)
    lumps.finish("broth_lumps", mats["crumb"], root)
    kit.beam("ladle_handle", (cx + 0.12, cy - 0.1, pot_z + 0.35), (cx + 0.24, cy - 0.55, pot_z + 0.9), (0.02, 0.02),
             mats["wood_old"], bevel=0.003, parent=root)
    kit.cylinder("ladle_bowl", 0.045, 0.045, (cx + 0.11, cy - 0.08, pot_z + 0.34), mat=cast, radius_top=0.06, segments=10,
                 parent=root)
    # tongs and a poker on the right jamb, ash and charcoal on the apron
    kit.beam("poker", (0.98, -DEPTH - 0.02, 0.28), (0.97, -DEPTH + 0.2, 1.05), (0.016, 0.016), iron, parent=root)
    kit.beam("fire_tongs", (1.1, -DEPTH - 0.02, 0.28), (1.12, -DEPTH + 0.18, 1.0), (0.02, 0.012), iron, parent=root)
    ashes = geo.Mesh()
    for _ in range(24):
        px, py = rng.gauss(0.0, 0.3), rng.uniform(-1.3, -DEPTH + 0.1)
        s = rng.uniform(0.015, 0.04)
        ashes.box((s, s * rng.uniform(0.6, 1.3), s * 0.6), (px, py, 0.01 + s * 0.25),
                  (rng.uniform(-20, 20), rng.uniform(-20, 20), rng.uniform(0, 180)))
    ashes.finish("hearth_ash", mats["coals"], root)
    # ash raked onto the floor in front of the hearth, and grey ash on the hearth stone itself
    _kitchen.scatter_blobs(kit, rng, "ash_on_floor", ash, root, (0.1, -1.25), (0.5, 0.18), 14, (0.03, 0.09), 0.004, z=0.0)

    # steam off the soup, drawn up toward the hood
    _fire.smoke(kit, mats["smoke"], root, "pot_steam", base=(cx, cy, pot_z + 0.4), rise=0.55, drift=0.9, r0=0.14, r1=0.4,
                density=1.0, seed=rng.uniform(0, 50))

    # smoke over the crown, blown east like the other fires, and three sparks that rise with it
    top = (0.0, 0.225, STACK_TOP + 0.5)
    _fire.smoke(kit, mats["smoke"], root, "chimney_smoke", base=top, rise=1.8, drift=2.2, r0=0.3, r1=1.4,
                density=1.5, seed=rng.uniform(0, 50))
    _fire.sparks(kit, mats["embers"], root, "chimney_sparks", rng, 3, (0.0, 0.225, STACK_TOP + 0.4), 1.6, 0.08,
                 (0.9, 0.2), 0.035)
    return root

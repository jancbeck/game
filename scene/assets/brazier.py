"""Iron fire basket on four splayed legs, open to the sky: staves, charred logs, coals, a fire.

Footprint is centered on X/Y = 0, rests on Z = 0, rim at about 0.8 m. About twenty ragged flame
tongues, up to 0.7 m tall, burn over dark coals and charred logs that glow only in their cracks.
The rain keeps the fire low and makes it smoke: a thick plume leaves just above the flame tips,
bends over downwind and thins out within about 4 m, and a few embers drift with it. Wind blows
toward +X, slightly +Y, and the flames lean that way.
Every effect part is its own object with its pivot at its base or emitter.

The two fire lights scatter only a small share of their light in the haze and smoke
(`VOLUME_FACTOR`): a light inside the haze would bleach the air around the flames to a white veil
and wash their orange out.
"""

import math

from . import _fire, _lights

# main fire light, plus a lower, redder light in front that spills onto the floor and posts.
# `reach` keeps the glint of a floor fire off walls across the yard (see _lights.py).
LIGHTS = []
FIRE_LIGHTS = [dict(pos=(0.0, 0.0, 1.10), color=(1.0, 0.36, 0.07), watts=340.0, reach=11.0),
               dict(pos=(0.0, -0.45, 0.95), color=(1.0, 0.27, 0.04), watts=120.0, reach=11.0)]

VOLUME_FACTOR = 0.18          # share of the light that scatters in the haze and smoke

BOWL_Z0, BOWL_Z1 = 0.38, 0.77
BOWL_R0, BOWL_R1 = 0.24, 0.35

WIND = (0.24, 0.05)           # flame lean in meters per meter of height
SPARK_WIND = (0.9, 0.2)       # embers drift downwind: meters per meter of rise, at the top
FLAME_SCALE = 0.72            # rain keeps the fire low and smoky
EMBER_COUNT = 16

# wet wood smokes heavily; the plume leaves just above the flame tips and the wind lays it down
SMOKE = dict(base=(0.20, 0.04, 1.45), rise=0.9, drift=1.6, r0=0.22, r1=1.0, density=0.8)


def _bowl_radius(z):
    return BOWL_R0 + (z - BOWL_Z0) / (BOWL_Z1 - BOWL_Z0) * (BOWL_R1 - BOWL_R0)


def build(kit, mats, rng):
    root = kit.group("brazier")
    for i, spec in enumerate(FIRE_LIGHTS):
        # a light sitting inside the haze would bleach the air around the flames to a white veil
        _lights.add(root, f"brazier_{i}", **spec).data.volume_factor = VOLUME_FACTOR
    iron, embers, fire = mats["iron"], mats["embers"], mats["fire"]

    # bowl: tapered shell, rim ring, hoops and twelve staves that make it a basket
    mid_z = (BOWL_Z0 + BOWL_Z1) / 2
    kit.cylinder("bowl", BOWL_R0, BOWL_Z1 - BOWL_Z0, (0, 0, mid_z), mat=iron, segments=16,
                 radius_top=BOWL_R1, bevel=0.006, parent=root)
    kit.torus("rim", BOWL_R1 + 0.005, 0.028, (0, 0, BOWL_Z1 + 0.005), mat=iron,
              major_segments=20, minor_segments=6, parent=root)
    for i, z in enumerate((0.47, 0.60)):
        kit.torus(f"hoop_{i}", _bowl_radius(z) + 0.008, 0.022, (0, 0, z), mat=iron,
                  major_segments=20, minor_segments=5, parent=root)
    for i in range(12):
        a = 2 * math.pi * i / 12
        r0, r1 = _bowl_radius(BOWL_Z0) + 0.03, _bowl_radius(BOWL_Z1) + 0.03
        kit.beam(f"stave_{i}", (r0 * math.cos(a), r0 * math.sin(a), BOWL_Z0),
                 (r1 * math.cos(a), r1 * math.sin(a), BOWL_Z1 + 0.02), section=(0.022, 0.022),
                 mat=iron, bevel=0.003, parent=root)

    # legs: four splayed iron bars tied together by a low ring
    for i in range(4):
        a = math.radians(45 + 90 * i + kit.jitter(rng, 4))
        top = (0.25 * math.cos(a), 0.25 * math.sin(a), 0.52)
        foot = (0.35 * math.cos(a), 0.35 * math.sin(a), 0.0)
        kit.beam(f"leg_{i}", top, foot, section=(0.055, 0.055), mat=iron, bevel=0.006, parent=root)
    kit.torus("leg_ring", 0.325, 0.016, (0, 0, 0.14), mat=iron, major_segments=20,
              minor_segments=5, parent=root)

    # fuel: coal mound heaped over the rim, three charred logs, bright lumps
    kit.sphere("coals", 0.33, (0, 0, BOWL_Z1 - 0.02), scale=(1, 1, 0.6), mat=embers,
               segments=16, parent=root)
    for i, (yaw, pitch, off) in enumerate(((30, 74, (0.04, -0.03)), (-50, 78, (-0.05, 0.05)),
                                           (130, 80, (0.0, 0.07)))):
        kit.cylinder(f"log_{i}", 0.04, 0.42, (off[0], off[1], 0.93), rot_deg=(pitch, 0, yaw),
                     mat=embers, segments=8, bevel=0.004, parent=root)
    for i in range(7):
        a = 2 * math.pi * i / 7 + kit.jitter(rng, 0.4)
        r = 0.19 + kit.jitter(rng, 0.04)
        kit.sphere(f"lump_{i}", 0.055 + kit.jitter(rng, 0.012),
                   (r * math.cos(a), r * math.sin(a), 0.875), scale=(1.1, 0.9, 0.7),
                   mat=embers, segments=8, parent=root)

    # flames: two tall core tongues, a ragged ring of eight of different height licking outward, bright
    # narrow tongues inside, and low flickers over the rim; every one leans downwind
    zb = 0.90
    f = FLAME_SCALE
    _fire.flame(kit, fire, root, "flame_core", (0, 0, zb), 0.95 * f, 0.17 * f, lean=WIND,
                twist=1.5, phase=0.3)
    _fire.flame(kit, fire, root, "flame_core_b", (-0.04, 0.03, zb), 0.78 * f, 0.13 * f,
                lean=(WIND[0] + 0.12, WIND[1] - 0.05), twist=-1.1, phase=1.2)
    for i in range(8):
        ang = 45 * i + kit.jitter(rng, 14)
        a = math.radians(ang)
        h = rng.uniform(0.38, 0.74)
        rad = rng.uniform(0.09, 0.125)
        out = rng.uniform(0.10, 0.22)
        _fire.flame(kit, fire, root, f"flame_{i}", (0.14 * math.cos(a), 0.14 * math.sin(a), zb - 0.03),
                    h * f, rad * f, lean=(out * math.cos(a) + WIND[0], out * math.sin(a) + WIND[1]),
                    twist=-1.4 + i * 0.55, phase=i * 1.9 + kit.jitter(rng, 0.4))
    for i, (dx, dy, h) in enumerate(((0.04, 0.02, 0.62), (-0.05, -0.03, 0.50), (0.0, 0.06, 0.42))):
        _fire.flame(kit, fire, root, f"inner_{i}", (dx, dy, zb + 0.02), h * f, 0.075 * f,
                    lean=(WIND[0] + dx, WIND[1] + dy), twist=1.0 + i, phase=3.1 + i * 2.0)
    for i in range(6):
        a = 2 * math.pi * i / 6 + 0.6 + kit.jitter(rng, 0.2)
        _fire.flame(kit, fire, root, f"lick_{i}", (0.27 * math.cos(a), 0.27 * math.sin(a), zb - 0.05),
                    (0.24 + kit.jitter(rng, 0.07)) * f, 0.058 * f,
                    lean=(0.34 * math.cos(a) + WIND[0], 0.34 * math.sin(a) + WIND[1]),
                    twist=1.0, phase=i * 2.3)

    # a few embers rise from the coals and drift downwind; the smoke plume follows the flames
    _fire.sparks(kit, embers, root, "sparks", rng, EMBER_COUNT, (0, 0, 1.0), 2.4, 0.18, SPARK_WIND,
                 0.05)
    _fire.smoke(kit, mats["smoke"], root, "smoke", seed=rng.uniform(0, 50), **SMOKE)
    return root

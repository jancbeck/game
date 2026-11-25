"""Lantern on a wall bracket: origin at the mount point on the wall, the arm sticks out toward -Y.

Same model as lantern.py with the hanging variant forced, so a plan entry does not depend on the
rng seed. Put it under "mounted" with the usual rot_z. Its light is placed here and not through
LIGHTS: the candle sits 0.42 m from the wall, and a full-specular light there leaves a round glint
on the stone, so the light keeps a low specular (see _lights.py).
"""

from . import _lights, lantern

LIGHTS = []
LIGHT = dict(radius=0.12, specular=0.2, reach=6.0)


def build(kit, mats, rng):
    root = lantern.build(kit, mats, rng, hanging=True)
    pos, color, watts = lantern.LIGHTS_HANGING[0]
    _lights.add(root, "lantern_hanging", pos, color, watts, **LIGHT)
    return root

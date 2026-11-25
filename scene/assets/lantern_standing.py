"""Lantern standing on the ground (or on a crate, via the "z" key of a plan prop).

Same model as lantern.py with the standing variant forced, so a plan entry does not depend on the
rng seed. Put it under "props".
"""

from . import lantern

LIGHTS = lantern.LIGHTS_STANDING


def build(kit, mats, rng):
    return lantern.build(kit, mats, rng, hanging=False)

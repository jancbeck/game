"""Drip bucket for the well: the same bucket and ripples with the thread of drops cut to the
well roof's eave, 1.3 m above the capstone it stands on. Always the small bucket, which fits the
0.39 m wide capstone ring."""

from . import drip_bucket


def build(kit, mats, rng):
    return drip_bucket.build(kit, mats, rng, drip_height=1.3, big=False)

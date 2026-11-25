"""Falling water: streams and drip chains off the eaves, the gallows and the gatehouse, with the splashes.

Place it once, at the origin, unrotated and at scale 1: `"drips": {"pos": [0, 0], "rot_z": 0}`.
The geometry is in world meters and is made from the location's plan.json, which this module reads itself,
so it follows the props when they move. Sources (see _drips_src.py):

- the cookhouse lean-to: the whole eave and the right-hand barge edge
- the stable roof, both eaves of the well roof
- the gallows crossbeam (both edges and both ends) and the deck rim
- the drip course above the lintel of every `lit_door`
- two stone spouts at the foot of the gatehouse parapet, built here, that throw the roof water out

Each source is a string of drip points. A heavy point is a continuous jet that thins as it speeds up,
necks and breaks into beads; two heavy jets side by side are joined by a thin veil of water; a light
point is a chain of drips that open up toward the ground. Where
the water lands there is a crown of droplets, a ripple ring and, on floors, a dark mirror-wet patch.
Everything is real geometry with a clear, glossy, emission-free water material (_drips_mat.py), so
it catches the light of the fires from any side. It casts no shadow.

Buckets that have drips of their own (`drip_bucket*` in the plan) are left alone.
"""

import math

import location

from . import _drips_geo as geo
from . import _drips_mat as dm
from . import _drips_src as src



def _spouts(kit, mats, root, spouts, rng):
    """Stone scuppers on the gatehouse face, tilted down, with a dark mouth."""
    for i, (x, face, z) in enumerate(spouts):
        kit.box(f"spout_{i}", (0.26, 0.56, 0.2), (x + kit.jitter(rng, 0.01), face - 0.24, z + 0.0),
                (-7.0, 0.0, kit.jitter(rng, 1.0)), mats["stone_wall"], bevel=0.02, parent=root)
        kit.box(f"spout_mouth_{i}", (0.1, 0.05, 0.06), (x, face - 0.515, z + 0.01),
                (-7.0, 0.0, 0.0), mats["iron"], parent=root)


def build(kit, mats, rng):
    root = kit.group("drips")
    plan = location.plan()
    drips, spouts = src.collect(plan, rng)

    water, rings, wet = geo.Soup(), geo.Soup(("fade",)), geo.Soup(("fade",))
    veils = geo.Soup(("fade",))
    heavy = [d for d in drips if d.flow >= 0.5]
    for i, a in enumerate(heavy):
        for b in heavy[i + 1:]:
            near = math.hypot(a.x - b.x, a.y - b.y) < 0.26 and abs(a.z - b.z) < 0.05
            same_way = a.heading[0] * b.heading[0] + a.heading[1] * b.heading[1] > 0.9
            if near and same_way and rng.random() < 0.65:
                h_end = min(a.z - a.z_land, b.z - b.z_land, rng.uniform(0.5, 1.1))
                geo.sheet(veils, (a.x, a.y, a.z, a.heading, a.hv), (b.x, b.y, b.z, b.heading, b.hv), h_end, rng)
    for d in drips:
        lean = geo.WIND if d.flow >= 0.5 else (geo.WIND[0] * 0.5, geo.WIND[1] * 0.5)
        if d.flow >= 0.5:
            geo.stream(water, d.x, d.y, d.z, d.z_land, d.heading, d.hv, d.flow, rng)
        else:
            geo.chain(water, d.x, d.y, d.z, d.z_land, d.heading, d.hv, d.flow, rng)
        dx, dy = geo.lateral(d.z - d.z_land, d.heading, d.hv, lean)
        x, y = d.x + dx, d.y + dy
        geo.crown(water, x, y, d.z_land, d.flow, rng)
        r_in = 0.02 + 0.035 * d.flow
        geo.ring(rings, x, y, d.z_land, r_in, r_in + 0.008 + 0.008 * d.flow)
        if d.flow > 0.55:
            geo.ring(rings, x, y, d.z_land, r_in * 2.0, r_in * 2.0 + 0.007 + 0.006 * d.flow)
        if d.patch:
            geo.patch(wet, x, y, d.z_land, 0.10 + 0.20 * d.flow, rng,
                      stretch=(1.0 + abs(d.heading[0]) * 0.5, 1.0 + abs(d.heading[1]) * 0.5))

    water.to_object("drip_water", dm.water(), root)
    rings.to_object("drip_rings", dm.ring(), root)
    wet.to_object("drip_wet", dm.wet(), root)
    veils.to_object("drip_veils", dm.sheet(), root)
    _spouts(kit, mats, root, spouts, rng)
    return root

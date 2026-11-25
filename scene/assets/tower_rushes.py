"""Rushes strewn on the boards of the commander's chamber: thin flat strands, thicker near the stair door, the
desk and the hearth, where boots come and go.

Origin: the middle of the room at z = 0. One merged mesh of about 150 strands, each 0.2-0.5 m long, laid down
at random angles and gathered in drifts; none lies where the desk or the bed stands.
"""

import math

from . import _shed_geo as geo

LIGHTS = []
# drifts: centre x, y, spread x, y, strands
DRIFTS = ((2.0, -1.25, 0.45, 0.5, 40), (-0.4, -0.5, 0.7, 0.28, 30), (0.45, 1.25, 0.5, 0.22, 24), (-1.5, -1.5, 0.5, 0.25, 16),
          (1.5, 0.3, 0.4, 0.4, 14))


def build(kit, mats, rng):
    root = kit.group("tower_rushes")
    m = geo.Mesh()
    for cx, cy, sx, sy, n in DRIFTS:
        for _ in range(n):
            x, y = rng.gauss(cx, sx), rng.gauss(cy, sy)
            if not (-2.65 < x < 2.65 and -2.0 < y < 2.0):
                continue
            ln = rng.uniform(0.2, 0.5)
            ang = rng.uniform(0, 180)
            m.box((ln, rng.uniform(0.006, 0.012), 0.004), (x, y, 0.043 + rng.uniform(0, 0.006)),
                  (rng.uniform(-4, 4), rng.uniform(-4, 4), ang))
    m.finish("rush_strands", mats["straw"], root)
    return root

"""Clump of dead grass: 45 to 90 arching blades, 0.25 to 0.55 m tall, about 0.5 m across.

Origin at the clump center on Z = 0. Most blades are `straw`; a few green shoots in
`moss` stand up in the middle on some instances. 1k to 2k triangles.
"""

import math

from mathutils import Vector

from . import _tube


def _blades(mesh, rng, count, height, spread):
    for _ in range(count):
        az = rng.uniform(0, 2 * math.pi)
        rad = abs(rng.gauss(0, 0.045))
        pos = Vector((math.cos(az) * rad, math.sin(az) * rad, -0.01))
        h = height * rng.uniform(0.45, 1.0)
        lean = math.radians(rng.uniform(4, 8 + spread))
        bend = math.radians(rng.uniform(15, 55 + spread * 2))
        az_l = az + rng.uniform(-0.7, 0.7)
        out = Vector((math.cos(az_l), math.sin(az_l), 0))
        steps = 5
        w0 = rng.uniform(0.012, 0.022)
        pts, widths = [], []
        for k in range(steps + 1):
            t = k / steps
            pts.append(pos.copy())
            widths.append(w0 * (1 - t) ** 0.8 + 0.0008)
            ang = min(lean + bend * t ** 1.6, math.radians(125))
            pos = pos + (out * math.sin(ang) + Vector((0, 0, math.cos(ang)))) * (h / steps)
            pos.z = max(pos.z, 0.01)
        mesh.blade(pts, widths, Vector((-out.y, out.x, 0)), twist=rng.uniform(-1, 1))


def build(kit, mats, rng):
    root = kit.group("grass_tuft")
    height = rng.uniform(0.25, 0.55)
    spread = rng.uniform(10, 35)
    straw, green = _tube.Mesh(), _tube.Mesh()
    _blades(straw, rng, rng.randint(45, 90), height, spread)
    if rng.random() < 0.5:
        _blades(green, rng, rng.randint(6, 16), height * 0.75, spread * 0.5)
    straw.to_object("grass_straw", mats["straw"], root)
    if green.faces:
        green.to_object("grass_green", mats["moss"], root)
    return root

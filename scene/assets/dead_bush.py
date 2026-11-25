"""Dead scrub: a tangle of thin arching stems that fork into twigs, 0.6 to 1.5 m tall.

Origin at the base on Z = 0. The rng sets the height, the number of stems and how
far they fan out, so instances differ. One merged mesh in `bark`, 8k to 20k triangles.
"""

import math

from mathutils import Vector

from . import _tube


def build(kit, mats, rng):
    root = kit.group("dead_bush")
    height = rng.uniform(0.6, 1.5)
    fan = rng.uniform(20, 45)  # how far the stems lean out from vertical, degrees

    P = _tube.Params(
        seg=[0.12, 0.10, 0.09, 0.08, 0.07],
        gnarl=[0.30, 0.45, 0.50, 0.50, 0.50],
        kink=[0.10, 0.15, 0.15, 0.15, 0.15],
        up=[0.0, 0.0, -0.01, -0.02, -0.02],
        density=[5.0, 5.5, 5.5, 5.0, 0],
        angle=[(30, 70)] * 5,
        up_bias=[0.1, 0.05, 0.0, 0.0, 0.0],
        shrink=[(0.5, 0.7)] * 5,
        len_ratio=[(0.30, 0.55), (0.35, 0.6), (0.4, 0.65), (0.4, 0.65), (0.4, 0.65)],
        t_first=[0.12] * 5,
        collar=0.2,
        r_min=0.003,
        min_len=0.06,
        max_level=4,
        break_p=0.10,
        floor=0.03,
        floor_level=0,
        max_branches=1200,
    )
    mesh = _tube.Mesh()
    grower = _tube.Grower(mesh, rng, P)

    azim = rng.uniform(0, 2 * math.pi)
    for _ in range(rng.randint(10, 18)):
        azim += _tube.GOLDEN + rng.uniform(-0.4, 0.4)
        tilt = math.radians(max(8, rng.gauss(fan, 12)))
        d = Vector((math.sin(tilt) * math.cos(azim), math.sin(tilt) * math.sin(azim), math.cos(tilt)))
        start = Vector((rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), -0.03))
        grower.add(start, d, height * rng.uniform(0.7, 1.15), rng.uniform(0.013, 0.024), 0,
                   droop=rng.uniform(0.03, 0.10), end_ratio=0.3)
    grower.run()

    mesh.scale(height / max(mesh.max_z(), 0.05))
    mesh.to_object("dead_bush_wood", mats["bark"], root)
    return root

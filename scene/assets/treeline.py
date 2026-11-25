"""Distant tree line: a low rolling hill with four staggered rows of bare trees and scrub.

Origin at the middle of the band's front foot on Z = 0; the band runs along X
(about 54 m) and is 14 m deep, the front edge at Y = -7 and the crest near Y = +5.
The hill rises 3 to 4 m, the trees are 7 to 14 m tall, so the crest reaches 15 m
or more. The hill is a fixed shape, so `hill_height` gives the ground height for
any point and single trees can be placed on it. Two meshes: `mud` for the hill,
`wood_dark` for the trees and scrub. About 330k to 360k triangles.

Place it behind the wall the camera looks over, close enough that the frame
shows it: with an orthographic camera at 38 degrees down, distance does not
shrink anything, and ground 25 m north of the castle is already off the top of
the frame.
"""

import math

from mathutils import Vector

from . import _tube

LENGTH = 54.0
DEPTH = 14.0
AMP = 4.0
FLAT = 0.30      # front part of the depth that stays level with the ground, as a fraction
CREST = 0.85     # where the hill is highest, as a fraction of the depth
ROWS = (-4.0, -0.6, 2.8, 6.2)   # local Y of the tree rows


def _smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def hill_height(x, y):
    """Ground height of the hill (meters above the band's Z = 0) at local (x, y)."""
    t = (y + DEPTH / 2) / DEPTH
    prof = _smooth(FLAT, CREST, t) * (1 - 0.3 * _smooth(CREST, 1.0, t))
    ridge = 0.72 + 0.16 * math.sin(x * 0.11 + 0.7) + 0.12 * math.sin(x * 0.27 + 2.1)
    bump = 0.18 * math.sin(x * 0.45 + 1.3) * math.sin(y * 0.6 + 0.4)
    taper = _smooth(0.0, 0.16, 0.5 - abs(x) / LENGTH)
    return AMP * (prof * ridge + bump * prof) * taper


def _lite_sides(r):
    if r > 0.15:
        return 6
    if r > 0.04:
        return 5
    return 4 if r > 0.02 else 3


def _tree_params(rng):
    return _tube.Params(
        seg=[0.5, 0.45, 0.4, 0.35, 0.3, 0.28, 0.25],
        gnarl=[0.14, 0.34, 0.40, 0.44, 0.46, 0.48, 0.48],
        kink=[0.0, 0.16, 0.2, 0.22, 0.22, 0.22, 0.22],
        up=[0.03, 0.05, 0.03, 0.01, 0.0, 0.0, 0.0],
        spring=[0.06, 0.14, 0.14, 0.12, 0.10, 0.10, 0.10],
        keep=0.45,
        density=[0, 1.8, 2.8, 3.8, 4.4, 4.4, 0],
        angle=[(22, 52), (38, 72), (35, 70), (35, 68), (32, 65), (32, 65), (32, 65)],
        up_bias=[0.0, 0.15, 0.1, 0.05, 0.03, 0.0, 0.0],
        shrink=[(0.45, 0.65), (0.45, 0.65), (0.5, 0.7), (0.55, 0.78), (0.55, 0.78), (0.55, 0.78), (0.55, 0.78)],
        len_ratio=[(0.35, 0.6), (0.4, 0.7), (0.4, 0.7), (0.35, 0.6), (0.35, 0.6), (0.35, 0.6), (0.35, 0.6)],
        t_first=[0.3, 0.2, 0.15, 0.12, 0.1, 0.1, 0.1],
        r_min=0.006,
        min_len=0.22,
        max_level=6,
        break_p=0.04,
        floor=0.4,
        max_branches=320,
        sides=_lite_sides,
    )


def _tree(rng, height):
    """One bare tree of about `height` m, base at the origin, as its own small mesh."""
    mesh = _tube.Mesh()
    grower = _tube.Grower(mesh, rng, _tree_params(rng))
    tilt = math.radians(rng.uniform(0, 9))
    az = rng.uniform(0, 2 * math.pi)
    lean = Vector((math.sin(tilt) * math.cos(az), math.sin(tilt) * math.sin(az), math.cos(tilt)))
    grower.add((0, 0, -0.3), lean, height * rng.uniform(0.62, 0.8), height * rng.uniform(0.018, 0.027), 0,
               sway=(rng.uniform(0.04, 0.1), rng.uniform(0.2, 0.4), rng.uniform(0, 6.28)),
               flare=(0.25, 0.4), n_lat=rng.randint(6, 9), t_range=(0.3, 0.97), end_ratio=0.22)
    grower.run()
    return mesh, height / max(mesh.max_z(), 0.5)


def _scrub(rng):
    """Low tangle of stems, 1 to 1.8 m."""
    mesh = _tube.Mesh()
    P = _tube.Params(seg=[0.3, 0.25, 0.2], gnarl=[0.35, 0.5, 0.5], kink=[0.1, 0.15, 0.15],
                     density=[3.0, 4.0, 0], angle=[(30, 70)] * 3, shrink=[(0.5, 0.7)] * 3,
                     len_ratio=[(0.35, 0.6)] * 3, t_first=[0.15] * 3, r_min=0.006, min_len=0.2,
                     max_level=2, floor=0.05, floor_level=0, max_branches=40, sides=_lite_sides)
    grower = _tube.Grower(mesh, rng, P)
    azim = rng.uniform(0, 6.28)
    for _ in range(rng.randint(6, 10)):
        azim += _tube.GOLDEN
        tilt = math.radians(rng.uniform(15, 50))
        d = Vector((math.sin(tilt) * math.cos(azim), math.sin(tilt) * math.sin(azim), math.cos(tilt)))
        grower.add((0, 0, -0.05), d, rng.uniform(1.0, 1.8), rng.uniform(0.02, 0.035), 0, droop=0.08,
                   end_ratio=0.3)
    grower.run()
    return mesh


def _hill_mesh():
    nx, ny = int(LENGTH / 1.0), int(DEPTH / 1.0)
    mesh = _tube.Mesh()
    for j in range(ny + 1):
        y = -DEPTH / 2 + DEPTH * j / ny
        for i in range(nx + 1):
            x = -LENGTH / 2 + LENGTH * i / nx
            mesh.verts.append((x, y, hill_height(x, y) - 0.02))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            mesh.faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    return mesh


def build(kit, mats, rng):
    root = kit.group("treeline")
    _hill_mesh().to_object("treeline_hill", mats["mud"], root)

    wood = _tube.Mesh()
    for r, row_y in enumerate(ROWS):
        x = -LENGTH / 2 + rng.uniform(0, 2.5)
        while x < LENGTH / 2:
            y = row_y + rng.uniform(-0.9, 0.9)
            edge = _smooth(0.0, 0.16, 0.5 - abs(x) / LENGTH)
            if rng.random() < 0.15 + 0.85 * edge:
                height = rng.uniform(7.0, 11.0) + r * rng.uniform(0.6, 1.1)
                tree, s = _tree(rng, height)
                wood.append(tree, s, (x, y, hill_height(x, y)))
            x += rng.uniform(3.0, 4.8)

    # scrub along the front edge and between the trunks hides the join with the ground
    for _ in range(36):
        x = rng.uniform(-LENGTH / 2 + 3, LENGTH / 2 - 3)
        y = rng.uniform(-DEPTH / 2 + 0.5, ROWS[2])
        wood.append(_scrub(rng), 1.0, (x, y, hill_height(x, y)))

    wood.to_object("treeline_trees", mats["wood_dark"], root)
    return root

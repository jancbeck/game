"""The boarded floor of the commander's chamber: oak boards 0.2-0.26 m wide laid along X, joints staggered, worn.

Origin: the middle of the room at z = 0. The boards cover x -2.8 .. 2.8 and y -2.1 .. 2.1 and run a few mm
over the dark slab of the platform, so the gaps between them read as black lines. They are 2.0-3.2 m long
and meet over joists, which show as a joint every two rows or so; a quarter are of richer brown oak, a fifth of darker, older boards. A
worn dip runs from the stair door to the desk.
"""

from . import _shed_geo as geo

LIGHTS = []
X0, X1, Y0, Y1 = -2.8, 2.8, -2.1, 2.1


def build(kit, mats, rng):
    root = kit.group("tower_floor")
    y = Y0
    row = 0
    while y < Y1 - 0.02:
        w = min(rng.uniform(0.2, 0.27), Y1 - y)
        # joints: one or two per row, staggered from row to row
        cuts = [X0]
        x = X0 + rng.uniform(1.4, 3.0)
        while x < X1 - 0.6:
            cuts.append(x)
            x += rng.uniform(1.6, 3.2)
        cuts.append(X1)
        for a, b in zip(cuts, cuts[1:]):
            r = rng.random()
            mat = mats["wood_dark"] if r < 0.2 else mats["door_wood"] if r < 0.45 else mats["wood_old"]
            kit.box(f"board_{row}", (b - a - 0.008, w - 0.012, 0.04), ((a + b) / 2, y + w / 2, 0.02 + rng.uniform(-0.002, 0.002)),
                    (rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15), 0), mat, bevel=0.003, parent=root)
        y += w
        row += 1
    return root

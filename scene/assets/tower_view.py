"""What lies outside the window of the commander's chamber, in the valley mist: a stunted pine clinging to the cliff on a ledge of wet rock.

Origin: the middle of the room at z = 0. Only the throat of the paired window in the back wall (y 2.57 .. 2.85, x -2.4 .. -1.6, z 1.05 ..
2.45) looks out. The camera looks down at 46 degrees, so a ray that enters the opening near its head leaves the throat
near its sill and lands 3 to 12 m beyond the wall; the lower 0.9 m of the throat is what shows. The valley itself is the apron of
plan.json; this prop adds the nearer things that sit in that slice, so the drop has steps: a ledge of rock and a leaning pine, dark
against the mist. Nothing else lies outside: the cliff face is turned away from the camera.
"""

import math

from . import _kitchen, _shed_geo as geo

LIGHTS = []


def build(kit, mats, rng):
    root = kit.group("tower_view")
    m = geo.Mesh()
    # a ledge of broken rock jutting from the cliff face under the window, 2 m beyond the wall and 1.3 m under the floor
    for _ in range(20):
        x, y = rng.gauss(-2.0, 0.5), rng.gauss(4.9, 0.55)
        s = rng.uniform(0.2, 0.7)
        m.ellipsoid((x, y, -1.5 + rng.uniform(-0.25, 0.2)), (s * 0.8, s * rng.uniform(0.7, 1.2), s * rng.uniform(0.35, 0.6)),
                    (rng.uniform(-10, 10), rng.uniform(-10, 10), rng.uniform(0, 180)), segments=9)
    m.finish("cliff_ledge", mats["cliff_rock"], root, smooth=True)
    # a pine leaning out from the ledge: trunk and a few flat boughs
    base = (-2.25, 5.2, -1.5)
    top = (-1.95, 4.8, 0.15)
    t = geo.Mesh()
    t.cyl(base, top, 0.09, 0.035, sides=7)
    for k in range(7):
        f = 0.2 + k * 0.1
        p = tuple(b + (c - b) * f for b, c in zip(base, top))
        ang = rng.uniform(0, 2 * math.pi)
        ln = rng.uniform(0.4, 0.8) * (1.3 - f)
        t.cyl(p, (p[0] + math.cos(ang) * ln, p[1] + math.sin(ang) * ln, p[2] - 0.1), 0.025, 0.01, sides=5)
    t.finish("cliff_pine", mats["bark"], root)
    return root

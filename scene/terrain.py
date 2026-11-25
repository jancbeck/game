"""Height of the ground outside the walls, shared by build_scene.build_terrain and the props that stand on it.

The castle stands on a low natural mound. Far out, the ground is the rolling mud of the lower ward
(z = -3) and the country around it. Close to the north, east and south-east walls it rises in a
concave talus to 1.0-1.7 m above the lower ward at the wall foot, so the battered plinths of the
walls and towers stand in a slope that follows their outline. The distance is measured to the
footprints of the tall blocks in the location's plan.json, so the slope follows any change of the walls.

The mound is left out in two places:

- west of the west curtain, where `west_ditch` lays its own ground skin over the terrain;
- south of the inner ward's south edge, where the castle rock ends in a cliff.

The cliff. The castle stands on a rock spur whose south side drops about 10 m. Its edge (`EDGE`)
runs 2.5-3.5 m outside the south parapet and the south-east curtain, and right under the cliff-side
wall of the commander's tower (`palas`, plan block `sw_tower`) at the south-west corner, which stands
on the rock shelf at the edge with a buttress down the face. Inside the edge, a strip of bare rock rises
toward the wall feet as a rounded shoulder, so the parapet's retaining wall and the tower stand on rock.
Outside it the face falls steeply, then runs out in a scree slope. The cliff dies out east of the east curtain, where the mound takes over, and runs on
west beyond the west ditch. This is why the south side needs only a breast-high parapet.

`ground_z(x, y)` is the world height of the terrain mesh at (x, y); `rock(x, y)` is 1 where the
terrain shows bare rock instead of mud.
"""

import math
import random

from mathutils import Vector, noise

import location
from planlib import entries, height

FOOT = 1.35        # mean height of the mound at the wall foot above the plain ground, meters
FOOT_VAR = 0.35    # its variation along the walls
REACH = 6.5        # mean distance from the wall face at which the mound meets the plain ground
REACH_VAR = 1.6
MIN_BLOCK = 5.0    # blocks taller than this above the lower ward carry the mound; parapets do not

# cliff edge from west to east; the rock is on the left (north), the drop on the right (south)
EDGE = [(-60.0, -19.6), (-24.0, -19.2), (-15.0, -19.3), (-11.5, -19.0), (-2.7, -17.4), (-2.4, -14.3),
        (3.5, -13.95), (5.3, -15.7), (13.0, -12.3), (15.5, -11.4), (24.0, -9.0), (60.0, -8.0)]
DROP = 10.0        # height of the cliff face
FACE = 3.5         # horizontal run of the steep face
SCREE = 0.22       # slope of the scree below the face
SHOULDER = 1.0     # rise of the rock strip from the edge toward the wall feet
SHOULDER_W = 3.0   # its width

_CACHE = {}


def _smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def _off():
    """The noise offset of the plain ground; `_ditch_field.terrain_z` draws the same one."""
    if "off" not in _CACHE:
        rng = random.Random(7)
        _CACHE["off"] = Vector((rng.uniform(0, 100), rng.uniform(0, 100), 0))
    return _CACHE["off"]


def reset():
    """Forget the measured walls, so the next call reads the location's plan again."""
    _CACHE.pop("rects", None)


def _rects():
    """Footprints of the tall blocks: (cx, cy, half w, half d, cos, sin)."""
    if "rects" not in _CACHE:
        plan = location.plan()
        heights = plan["heights"]
        lw = heights["lower_ward"]
        out = []
        for name, b in entries(plan["blocks"]):
            h = height(b["h"], heights)
            if h - lw <= MIN_BLOCK:
                continue
            if "from" in b:
                a, c = Vector((*b["from"], 0)), Vector((*b["to"], 0))
                center, w, d = (a + c) / 2, (c - a).length + b["t"] * 0.5, b["t"]
                rot = math.atan2(c.y - a.y, c.x - a.x)
            else:
                center, (w, d) = Vector((*b["center"], 0)), b["size"]
                rot = math.radians(b.get("rot_z", 0))
            out.append((center.x, center.y, w / 2, d / 2, math.cos(rot), math.sin(rot)))
        _CACHE["rects"] = out
        _CACHE["lower_ward"] = lw
    return _CACHE["rects"]


def lower_ward():
    _rects()
    return _CACHE["lower_ward"]


def wall_distance(x, y):
    """Distance from (x, y) to the nearest tall block footprint; 0 inside one."""
    best = 1e9
    for cx, cy, hw, hd, c, s in _rects():
        dx, dy = x - cx, y - cy
        lx, ly = abs(dx * c + dy * s) - hw, abs(-dx * s + dy * c) - hd
        d = math.hypot(max(lx, 0.0), max(ly, 0.0))
        if d < best:
            best = d
    return best


def plain_z(x, y):
    """The rolling mud without the mound: flat-ish at the castle, rolling farther out."""
    r = max(0.0, Vector((x, y + 2, 0)).length - 20.0)
    amp = 0.15 + min(r, 30.0) * 0.12
    return lower_ward() - 0.02 + amp * noise.noise(Vector((x, y, 0)) * 0.06 + _off()) - 0.1


def mound_weight(x, y):
    """1 where the mound carries the walls, fading to 0 at the west ditch and over the south lower ward."""
    west = _smooth(-12.6, -10.4, x)
    south = max(_smooth(-11.0, -8.0, y), _smooth(5.0, 10.5, x))
    return west * south


def mound_z(x, y):
    """Height of the mound above the plain ground at (x, y), before weighting."""
    p = Vector((x, y, 0.0))
    foot = FOOT + FOOT_VAR * noise.noise(p * 0.09 + Vector((31.0, 7.0, 0.0)))
    reach = REACH + REACH_VAR * noise.noise(p * 0.07 + Vector((-12.0, 44.0, 0.0)))
    s = min(1.0, wall_distance(x, y) / reach)
    talus = (1.0 - s) ** 2
    lumps = 0.14 * noise.noise(p * 0.45 + Vector((5.0, 5.0, 0.0))) * (1.0 - s)
    return foot * talus + lumps


def edge_distance(x, y):
    """Signed distance from the cliff edge: positive beyond it (over the drop), negative on the rock."""
    best, sign = 1e9, 1.0
    for (ax, ay), (bx, by) in zip(EDGE, EDGE[1:]):
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        px, py = ax + t * dx - x, ay + t * dy - y
        d = math.hypot(px, py)
        if d < best:
            best = d
            sign = 1.0 if dx * (y - ay) - dy * (x - ax) < 0 else -1.0
    return sign * best


def cliff_weight(x):
    """The cliff runs along the whole south side and dies out east of the east curtain."""
    return 1.0 - _smooth(15.0, 20.0, x)


def cliff_z(x, y):
    """Change of height from the cliff: the rock shoulder inside the edge, the face and scree outside."""
    w = cliff_weight(x)
    if w <= 0.0:
        return 0.0
    e = edge_distance(x, y)
    p = Vector((x, y, 0.0))
    if e <= 0.0:
        rise = SHOULDER * _smooth(0.0, SHOULDER_W, -e) * (0.75 + 0.5 * noise.noise(p * 0.3 + Vector((3.0, 9.0, 0.0))))
        knobs = 0.25 * noise.noise(p * 0.9) * _smooth(0.0, 1.0, -e)
        # only under the walls: west of them lies the west ditch's own ground skin
        clear = _smooth(-14.5, -12.5, x)
        return w * clear * (rise + knobs) * (1.0 - _smooth(-9.0, -6.0, e))
    t = min(1.0, e / FACE)
    drop = DROP * (1.0 - (1.0 - t) ** 1.6) + SCREE * max(0.0, e - FACE)
    # jagged face: buttresses and gullies down the face, bedding ledges across it, strongest mid-face
    face = math.sin(math.pi * min(1.0, e / (FACE + 1.5)))
    gullies = 1.6 * noise.noise(Vector((x * 0.32, y * 0.32, 0.0)) + Vector((17.0, 3.0, 0.0)))
    knobs = 0.7 * noise.noise(p * 1.1 + Vector((0.0, 0.0, 0.3 * drop)))
    ledges = 0.45 * ((drop / 1.4) % 1.0 - 0.5)
    return -w * (drop + face * (gullies + knobs + ledges))


def rock(x, y):
    """1 on the rock strip, the cliff face and the scree; 0 on mud."""
    w = cliff_weight(x)
    if w <= 0.0:
        return 0.0
    e = edge_distance(x, y)
    return w * _smooth(-SHOULDER_W - 0.5, -SHOULDER_W + 0.5, e) * (1.0 - _smooth(FACE + 3.0, FACE + 6.0, e))


def ground_z(x, y):
    """World height of the terrain at (x, y)."""
    w = mound_weight(x, y)
    z = plain_z(x, y)
    if w > 0.0:
        z += w * mound_z(x, y)
    return z + cliff_z(x, y)

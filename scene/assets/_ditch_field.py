"""Layout and ground height of the strip outside the west curtain wall, in world meters.

Not a prop (the leading underscore keeps it out of `assets.available()`). west_ditch.py and its
helpers build the ditch from these pure functions of (x, y), and the plan entries that stand near
the ditch (trees, bushes, tufts) read their ground heights from `ground()`.

From the wall outward (e = meters west of the platform's retaining face at x = -13.0):

- the retaining face rises 3.3 m to the cobble ledge at z = 0; silt has drifted against its foot;
- e 0.35 to 1.35: a trodden track with two wheel ruts, puddles in the ruts and a gully that carries
  the drain's trickle across it;
- e 1.7 to 2.4: the inner bank of the ditch, a slope down to the water;
- the ditch: about 2 m of still water, ending in a shallow pool at both ends;
- the outer bank: the spoil of the ditch, banked 0.6 m above the plain and falling away to it.

The ground is a skin laid 3.5 cm above the terrain that `build_scene.build_terrain` makes (that
function is copied here, not edited). The terrain is a closed sheet, so the ditch cannot be dug
below it: the water stands just above the highest terrain in the ditch, and banks of spoil on both
sides give it its depth. Every height is above the terrain at the same (x, y), so the skin follows
the ground it covers.
"""

import math
import random

from mathutils import Vector, noise

LOWER_WARD = -3.0
WALL_X = -13.0                  # retaining face of the platform: the visible wall below the ledge
LEDGE_Z = 0.0                   # top of that face, where the platform's cobbles end
ORIGIN = (-13.0, 0.0)           # world x, y of the prop root (z is the lower ward)

X_MIN, X_MAX = -24.0, -12.6     # the skin's extent; its west and its two y ends taper into the terrain
Y_MIN, Y_MAX = -17.0, 15.0
FADE = 2.5                      # width of that taper, meters

TRACK_E = 0.85                  # distance of the track axis from the wall
GAUGE = 0.36                    # the ruts lie this far either side of the axis
TRACK_HALF = 0.5                # half width of the trodden track
RUT_WIDTH = 0.085
RUT_DEPTH = 0.075
PLATEAU = 0.26                  # height of the land between wall and ditch above the terrain
FOOT = 0.10                     # extra silt against the wall foot
CREST = 0.58                    # height of the ditch's outer bank above the terrain

DRAIN_Y = -2.6                  # where the wall drain empties (see _ditch_wall.py)
DRAIN_Z = -1.15


def smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- the terrain underneath

_OFF = None


def _off():
    global _OFF
    if _OFF is None:
        rng = random.Random(7)
        _OFF = Vector((rng.uniform(0, 100), rng.uniform(0, 100), 0))
    return _OFF


def terrain_z(x, y):
    """World height of the terrain mesh (a copy of the formula in build_scene.build_terrain)."""
    r = max(0.0, Vector((x, y + 2, 0)).length - 20.0)
    amp = 0.15 + min(r, 30.0) * 0.12
    return LOWER_WARD - 0.02 + amp * noise.noise(Vector((x, y, 0)) * 0.06 + _off()) - 0.1


# ---------------------------------------------------------------- layout lines

def centre(y):
    """x of the ditch's center line. The bank beside the track keeps a fixed distance from it (room for the
    fence), so the ditch widens and narrows on its far side."""
    return track_x(y) - 0.82 - 0.75 - half_width(y)


def half_width(y):
    return 1.05 + 0.18 * math.sin(0.45 * y + 1.3)


def depth_weight(y):
    """1 along the ditch, 0 beyond its two ends, where the ground closes over it."""
    return smooth(-15.5, -11.0, y) * (1.0 - smooth(9.0, 13.0, y))


def track_e(y):
    return TRACK_E + 0.10 * math.sin(0.37 * y + 2.0)


def track_x(y):
    return WALL_X - track_e(y)


def rut_gate(y):
    """Ruts come and go: a cart does not press the same depth along the whole track."""
    return smooth(-0.35, 0.15, noise.noise(Vector((y * 0.21, 3.7, 0.0)))) * 0.55 + 0.45


# Standing water in the track: (x, y, half length in x, half length in y, extra depth). Each rut holds
# a chain of long basins; a bowl in front of the gully mouth and a hoof-pressed hollow are round.
def _puddle_sites():
    rng = random.Random(1311)
    sites = []
    for side in (-1, 1):
        y = Y_MIN + 2.0 + rng.uniform(0.0, 2.0)
        while y < 11.5:
            length = rng.uniform(1.2, 3.4)
            yc = y + length / 2
            sites.append((track_x(yc) - side * GAUGE + rng.uniform(-0.02, 0.02), yc, rng.uniform(0.15, 0.20),
                          length / 2, rng.uniform(0.04, 0.065)))
            y += length + rng.uniform(0.3, 1.8)
    sites.append((track_x(1.0) - 0.05, 1.6, 0.55, 0.65, 0.07))
    sites.append((track_x(-7.4) + 0.15, -7.4, 0.5, 0.5, 0.06))
    sites.append((WALL_X - 0.32, DRAIN_Y - 0.1, 0.34, 0.3, 0.07))
    return sites


PUDDLES = _puddle_sites()


# The gully from the drain's basin at the wall foot to the ditch: a polyline of (e, y).
def _gully():
    return [(0.3, DRAIN_Y - 0.1), (0.75, DRAIN_Y - 0.22), (1.25, DRAIN_Y - 0.5), (1.75, DRAIN_Y - 0.58),
            (2.2, DRAIN_Y - 0.9)]


GULLY = _gully()


def _dist_polyline(pts, e, y):
    best = 1e9
    for (e0, y0), (e1, y1) in zip(pts, pts[1:]):
        dx, dy = e1 - e0, y1 - y0
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else min(1.0, max(0.0, ((e - e0) * dx + (y - y0) * dy) / L2))
        best = min(best, math.hypot(e - (e0 + t * dx), y - (y0 + t * dy)))
    return best


def gully_distance(x, y):
    return _dist_polyline(GULLY, WALL_X - x, y)


# ---------------------------------------------------------------- ground height

_W = None


def water_level():
    """Height of the ditch water: just above the highest terrain anywhere the ditch could reach."""
    global _W
    if _W is None:
        top = -99.0
        y = Y_MIN
        while y <= Y_MAX:
            if depth_weight(y) > 0.2:
                c, hw = centre(y), half_width(y)
                x = c - hw - 1.0
                while x <= c + hw + 1.0:
                    top = max(top, terrain_z(x, y))
                    x += 0.25
            y += 0.5
        _W = top + 0.03
    return _W


def _edge_fade(x, y):
    """0 at the skin's west and y ends, 1 inside: the skin comes down to the terrain there."""
    return (smooth(X_MIN, X_MIN + FADE, x) * smooth(Y_MIN, Y_MIN + FADE, y) * smooth(Y_MAX, Y_MAX - FADE, y))


def ground(x, y):
    """World height of the skin at (x, y)."""
    t = terrain_z(x, y)
    e = WALL_X - x
    c, hw, k = centre(y), half_width(y), depth_weight(y)
    d = x - c                                        # positive toward the wall
    W = water_level()

    plateau = PLATEAU + FOOT * (1.0 - smooth(0.0, 1.0, e))
    flat = t + 0.035 + (plateau - 0.035) * smooth(-2.2, 0.8, d)       # ground with no ditch cut into it

    bed = W - 0.30
    crest = t + CREST + 0.07 * noise.noise(Vector((y * 0.35, 8.1, 0.0)))
    if d >= 0.0:
        cut = bed + (t + plateau - bed) * smooth(hw - 0.25, hw + 0.75, d)
    else:
        o = -d
        if o <= hw + 0.95:
            cut = bed + (crest - bed) * smooth(hw - 0.25, hw + 0.95, o)
        else:
            cut = t + 0.035 + (crest - t - 0.035) * (1.0 - smooth(hw + 0.95, hw + 4.8, o))
    z = flat + (cut - flat) * k

    # the track: crowned, with two ruts and the puddle hollows
    de = e - track_e(y)
    on_track = 1.0 - smooth(0.38, 0.72, abs(de))
    crown = 0.02 * on_track * (1.0 - min(1.0, (de / 0.5) ** 2))
    ruts = 0.0
    for s in (-1, 1):
        ruts += math.exp(-(((de - s * GAUGE) / RUT_WIDTH) ** 2))
    z += crown - RUT_DEPTH * rut_gate(y) * ruts * smooth(0.0, 0.4, e)
    for px, py, rx, ry, depth in PUDDLES:
        q = ((x - px) / rx) ** 2 + ((y - py) / ry) ** 2
        if q < 9.0:
            z -= depth * math.exp(-q)
    g = _dist_polyline(GULLY, e, y)
    if g < 0.5:
        z -= 0.05 * math.exp(-((g / 0.10) ** 2))

    # lumps: coarse clods and fine grit, flatter where the track is trodden
    p = Vector((x * 1.7, y * 1.7, 2.0))
    lump = 0.035 * noise.noise(p) + 0.012 * noise.noise(p * 3.7)
    z += lump * (1.0 - 0.75 * on_track)

    f = _edge_fade(x, y)
    return t + 0.012 + (z - t - 0.012) * f


def wetness(x, y, z):
    """0 to 1: how saturated, dark and glossy the mud is at (x, y), where the skin's height is z.

    Saturated at the waterline, in the ruts, around the puddles and the gully, trodden-damp along the track,
    and spattered at the wall foot where the ledge sheds its rain."""
    e = WALL_X - x
    c, hw, k = centre(y), half_width(y), depth_weight(y)
    d = x - c
    de = e - track_e(y)
    W = water_level()
    shore = (1.0 - smooth(W, W + 0.40, z)) * (1.0 - smooth(hw + 0.4, hw + 1.7, abs(d))) * smooth(0.2, 0.6, k)
    ruts = 0.0
    for s in (-1, 1):
        ruts += math.exp(-(((de - s * GAUGE) / 0.15) ** 2))
    ruts *= (0.5 + 0.5 * rut_gate(y)) * smooth(0.0, 0.4, e)
    track = 0.35 * (1.0 - smooth(0.3, 0.75, abs(de)))
    halo = 0.0
    for px, py, rx, ry, depth in PUDDLES:
        q = ((x - px) / (rx * 1.6)) ** 2 + ((y - py) / (ry * 1.3)) ** 2
        if q < 9.0:
            halo = max(halo, math.exp(-q * 0.8))
    g = _dist_polyline(GULLY, e, y)
    gully = math.exp(-((g / 0.2) ** 2)) * smooth(-0.05, 0.4, e)
    foot = 0.3 * (1.0 - smooth(0.0, 0.5, e))
    damp = 0.34 * (1.0 - smooth(1.5, 2.6, e)) * smooth(0.2, 0.6, e)       # trodden, damp earth between wall and ditch
    n = noise.noise(Vector((x * 2.6, y * 2.6, 9.0)))
    w = max(shore, ruts, track, halo * 0.9, gully * 0.9, foot, damp) * (0.8 + 0.4 * n)
    return min(1.0, max(0.0, w))


def surface_normal_z(x, y):
    """Z component of the surface normal (1 on the flat), from finite differences."""
    h = 0.08
    dx = (ground(x + h, y) - ground(x - h, y)) / (2 * h)
    dy = (ground(x, y + h) - ground(x, y - h)) / (2 * h)
    return 1.0 / math.sqrt(1.0 + dx * dx + dy * dy)


# ---------------------------------------------------------------- zones for scattering

def zone(x, y):
    """Where (x, y) lies: 'wall' (the foot), 'track', 'inner' (bank beside the track), 'water', 'outer' (the
    spoil bank) or 'plain'."""
    e = WALL_X - x
    c, hw = centre(y), half_width(y)
    d = x - c
    if e < 0.35:
        return "wall"
    if depth_weight(y) > 0.5 and abs(d) < hw + 0.2:
        return "water"
    if abs(e - track_e(y)) < TRACK_HALF + 0.05:
        return "track"
    if d > 0.0:
        return "inner"
    return "outer" if -d < hw + 4.6 else "plain"


def to_local(x, y, z):
    """World position to the prop root's frame (the root stands at ORIGIN, on the lower ward)."""
    return (x - ORIGIN[0], y - ORIGIN[1], z - LOWER_WARD)

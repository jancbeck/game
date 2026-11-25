"""Wet cobbles with a ground history: worn paths, ruts, puddles in the low spots, drier high ground.

Two parts.

1. `ground_maps(plan)` bakes the history of the courtyard floor into 2D maps in
   world meters, from plan.json (wall footprints, grate, gate, well, cart, shed,
   braziers) and a few named sites. Nothing in it depends on a camera. A ground
   height field is built from physical causes: the camber toward the drain grate,
   slow settlement, wear hollows along the paths, wheel ruts and hoof pits, gutters
   along the wall feet, pooling in the corners, splash trenches under the eaves,
   a hollow in front of the gate, a drain channel from the gate road to the grate
   with an overflow channel on to the parapet, and bowls worn where people stand
   at the fires. Water stands wherever that height is below one water level. The
   level is set so that WATER_COVER of the open floor is under water: sheets along
   ruts, channels, gutters, bowls and the holes of lost setts, with the stones of the
   higher ground standing out as islands. The same paths drive the mud, the trodden
   straw, the patches of packed earth, and the drier, lighter setts on the high
   spots and in the rain shadow of the gatehouse and the roofs.

2. `build(mat, nt, bsdf)` is the material. The setts are laid in courses. The floor is
   cut into regions of about 3 m, each with its own seed, lightness and gloss: straight rows
   in some, segmental fans in others, with courses that sag and sway. A course is 10 to 17 cm
   wide and is cut into setts of 11 to 21 cm, with boundaries that stray from the grid. Each
   sett is a rounded, slightly tapered box with a soft shoulder, a nearly flat crown that leans
   a little, and its own color, gloss and height. The joints between them are packed with dark
   wet mud and grit. The maps decide where the stones are worn into mud, patched with earth,
   buried under mud (a ragged band along every wall foot, aprons around the well, the cookhouse,
   the forge, the stable and the gallows, the worn tracks between them), sunk into the ground,
   strewn with straw, dirtied by dung, banked with silt around the grate, dry, or under water.
   Each sett sinks into the mud at a level of its own, so the edge of a patch follows the
   stones. The apron in front of the gate stands above the water level except for a few shallow
   pools, so the water cannot join into one sheet. Stone tops are damp (roughness 0.36 to 0.54);
   mud is matte; only the joints, hollows, ruts and the pools are mirror wet.
   Standing water is a dark base (brown where wheels and boots stir it up) with a
   mirror (roughness 0.03) and wind-driven ripples whose crests run along x, so a
   lit point is smeared into a streak along y. It carries no emission: the
   reflections are the raytraced scene, so a torch, brazier or door light shows up
   in any puddle that lies between it and the viewer.

The maps are 8-bit images made in memory when the material is built. Their
channels:

    map A   R water depth (signed, see DEPTH_MIN/DEPTH_MAX)   G traffic (wear)
            B wheel ruts                                       A packed earth
    map B   R dryness                                          G straw
            B silt and mud halo                                A hoof pits
    map C   R mud tracked in from the gate                     G dung zone
            B silt fan at the grate                            A cart lane
    map D   R macro mud (see _ground_mud.py)                   G sunk setts
            B worn track                                       A moss at the wall feet

Object coordinates are meters because kit.py keeps object scale at 1.
"""

import math
import types
import zlib

import numpy as np

import location
from mats import _ground_mud as gm

# ---------------------------------------------------------------- sett look
REGION_SCALE = 0.30  # coursing regions per meter: each is a field of rows or of fans with its own seed
FAN_SHARE = 0.38  # share of regions laid as segmental fans; the others are straight rows
FAN_RADIUS = (2.4, 4.2)  # radius in meters of the arcs of a fan, to the middle of the region
ROW_HEIGHT = (0.100, 0.170)  # nominal width of a course in meters, per region
COURSE_WAVE = 0.13  # meters the courses sag and sway across a few meters of floor
ROW_JITTER = 0.26  # how far the course boundaries stray from the nominal grid, as a share of it
SETT_LENGTH = (0.110, 0.215)  # nominal length of a sett along its course, per region
SETT_JITTER = 0.30  # same for the boundaries between setts in a course
JOINT_GAP = 0.0052  # half the gap between two setts, in meters
SHOULDER = 0.026  # width in meters of the rounded shoulder from joint to flat top
STONE_RELIEF = 0.010  # meters from joint to crown
STONE_TILT = 0.20  # how much each sett leans; each top then catches the light on its own
MISSING_SETTS = 0.025  # share of setts that are gone, patched with earth; more along paths
MISSING_EXTRA = 0.06  # extra share on the busiest paths

STONE_COLORS = [  # ramp over the per-stone random value; grey-blue with a few warm and olive setts, warmth comes from the fires
    (0.00, (0.078, 0.080, 0.080)),  # dark grey
    (0.18, (0.125, 0.112, 0.098)),  # warm grey-brown
    (0.38, (0.108, 0.112, 0.104)),  # olive grey
    (0.55, (0.170, 0.172, 0.165)),  # light worn grey
    (0.70, (0.140, 0.152, 0.172)),  # pale blue-grey
    (0.85, (0.115, 0.122, 0.135)),  # bluish grey
    (1.00, (0.088, 0.094, 0.108)),  # dark blue-grey
]
DRY_LIFT = 0.3  # how much lighter the dry setts are
FLOOR_GAIN = 1.30  # lifts stone, mud and straw together, so the floor is about as bright in the reference view as clean setts were
STONE_GAIN = 1.10  # lifts the setts a little more, so they stay readable next to the mud
REGION_LIGHT = (0.80, 1.22)  # lightness of a whole region of setts: some were laid or turned later, some are weathered darker
TRAIL_DARKEN = 0.42  # how much darker the setts of the main tracks are
MOSS_TINT, MOSS_TINT_AMOUNT = (0.66, 0.84, 0.50), 0.75  # green cast of damp stone at the wall feet, and how far it goes
WEAR_DARKEN = 0.25  # how much darker the stone tops of a busy path are
WEAR_FLATTEN = 0.55  # how far worn setts on a path fade toward one average color
MEAN_STONE = (0.100, 0.097, 0.079)
WORN_FROM, WORN_FULL = 0.1, 0.7  # traffic below this leaves the setts alone, above this the path is fully worn
PATINA = (0.68, 1.28)  # lightness range of the broad washes across the floor
MUD_DARK = (0.038, 0.033, 0.015)
MUD_LIGHT = (0.110, 0.098, 0.044)  # olive-brown, the one color of the floor that is not blue-grey
JOINT_MUD = (0.030, 0.023, 0.014)  # the dark wet mud packed into the joints
TRACK_MUD = (0.082, 0.070, 0.031)  # mud carried in on boots and wheels
EARTH_DARK = (0.046, 0.038, 0.024)
EARTH_LIGHT = (0.098, 0.082, 0.052)  # packed earth: warmer and lighter than the mud
STRAW_COLOR = (0.240, 0.198, 0.092)
STRAW_WET = (0.120, 0.092, 0.044)  # straw trodden into mud
DUNG_COLOR = (0.030, 0.0225, 0.0095)
SILT_COLOR = (0.022, 0.019, 0.014)  # fine silt left by the drain water: nearly black
DAMP_TINT = (0.84, 0.83, 0.79)
DRY_TINT = (0.92, 0.91, 0.87)
ROUGH_TOP = (0.36, 0.54)  # damp stone tops: lowest and highest roughness among setts
ROUGH_DRY = 0.64  # dry stone
ROUGH_SHOULDER = 0.48  # the worn, dirty shoulder where a top bends down into the joint
ROUGH_JOINT = 0.10  # mud-filled joint with a film of water
ROUGH_MUD, ROUGH_EARTH, ROUGH_FRINGE = 0.62, 0.66, 0.20  # tracked wet mud, packed earth, wet film at a puddle's rim
ROUGH_DUNG, ROUGH_SILT = 0.62, 0.16
MUD_SPECULAR = 0.30  # Specular IOR Level of mud
DAMP_SPECULAR = 0.5  # Specular IOR Level of damp stone: a satin sheen

# ---------------------------------------------------------------- water
WATER_BASE = (0.024, 0.027, 0.031)  # deep water over silt: nearly black, the mirror does the rest
TURBID_WATER = (0.058, 0.042, 0.026)  # water churned up by wheels and boots: brown, not black
WATER_SHALLOW = (0.72, 0.67, 0.58)  # stones and mud seen through a film of water
ROUGH_WATER = 0.03
PUDDLE_SPECULAR = 1.0  # Specular IOR Level in puddles (0.5 is the neutral default)
COAT_IOR = 1.8  # water film on dark ground: stronger than real water so it holds a sky sheen from a high view
WATER_COAT = 1.0  # weight of the water film's own reflection over the silt
SETT_JITTER_M = 0.012  # meters between the lowest and the highest sett top, from the sett's own random value
SETT_CROWN_M = 0.010  # meters a sett crown stands above its joints: crowns stay dry at a puddle's rim
RIPPLE_SCALES = (16.0, 4.5)  # rain ripple noise per meter: fine, swell
RIPPLE_STRETCH = 0.15  # ripples are wind-driven: crests run along x, so a reflection is smeared along y
RIPPLE_TILT = (0.0062, 0.0046)  # meters of height of those two
RING_LAYERS = [(1.15, (0.0, 0.0), 0.20), (0.8, (13.7, 7.3), 0.15)]  # rain rings: (cells per m, offset, share of cells with a ring)
RING_TILT = 0.0018  # meters of height of the rings

# ---------------------------------------------------------------- the baked map
PPM = 48  # map pixels per meter
MAP_X0, MAP_Y0 = -13.8, -15.0  # world meters of the map's lower left corner
MAP_W, MAP_H = 1350, 1200  # pixels; covers x -13.8..14.3 and y -15..10, the whole floor
DEPTH_MIN, DEPTH_MAX = -0.04, 0.08  # water depth range stored in map A, meters; negative is dry ground below the level
GROUND_SEED = 11

WATER_COVER = 0.15  # share of the open floor that stands under water; the water level is found from it
CAMBER_DEPTH, CAMBER_RADIUS = 0.016, 2.2  # the floor falls toward the grate: depth at the rim, 1/e radius in meters
SETTLE = [(6.0, 0.008), (2.4, 0.011), (0.8, 0.0045), (0.28, 0.0030)]  # (feature size m, meters std) of the uneven ground
HOLLOW_DEPTH = 0.012  # wear hollow at full traffic: paths are worn below the setts around them
RUT_DEPTH = 0.050  # wheel ruts, meters
RUT_GAUGE, RUT_HALF = 1.25, 0.17  # wheel distance and rut half-width, meters
HOOF_DEPTH = 0.040  # hoof pits
GUTTER_DEPTH, GUTTER_AT, GUTTER_WIDTH = 0.022, 0.55, 0.30  # wall-foot gutter: depth, distance from the wall, half-width
CORNER_DEPTH, CORNER_REACH = 0.020, 0.75  # extra sag where two walls meet
DRIP_DEPTH, DRIP_WIDTH = 0.040, 0.24  # splash trench under an eave
GATE_DEPTH = 0.006  # hollow in front of the gate, where everyone stops
DRAIN_DEPTH, DRAIN_WIDTH = 0.016, 0.62  # shallow channel along the middle of the gate road down to the grate
SILL_HEIGHT, SILL_STATIONS = 0.013, (1.55, 2.75, 4.0, 5.3)  # cross ridges of silt and setts in the channel: where along it, and how high; they cut the water into pools
GATE_POOLS = [  # shallow pools in front of the gate, relative to the gate: (dx, dy, half x m, half y m, rotation rad, depth m)
    (-0.25, -0.95, 1.05, 0.45, 0.08, 0.017),  # across the threshold
    (0.15, -2.9, 0.42, 0.95, 0.12, 0.016),  # down the middle of the road
    (-2.7, -4.1, 0.62, 1.15, -0.05, 0.016),  # where the left torch is mirrored: long, so the reflection is a long streak
    (1.45, -3.9, 0.6, 1.05, 0.10, 0.016),  # where the right torch is mirrored
]
GATE_LIFT = 0.09  # for the water, the apron in front of the gate stands this much higher: only its pools hold water
MUD_EDGE = (0.52, 0.62)  # the macro mud field plus noise: below the first value there is none, above the second it covers the stones
MUD_SETT_BIAS = 0.46  # how much the sinking level of one sett differs from the next, in units of the field
SUNK_GAP = 0.011  # extra joint half-width between sunk setts, meters
SUNK_DEPTH = 0.016  # sunk setts lie this much lower than their neighbors
BARE_DEPTH = 0.018  # a patch of lost setts is a pothole this deep at its middle
OUTFALL_DEPTH, OUTFALL_WIDTH = 0.026, 0.45  # the overflow channel from the grate to the parapet
BOWL_DEPTH = 0.034  # worn bowls in front of the fires
STAND_DEPTH = 0.022  # bowls worn where people stand around the braziers, the well and the forge
EARTH_DEPTH = 0.007  # packed earth sits lower than the setts around it
SILT_RAISE = 0.012  # silt and rubble banked against the wall foot
MEANDER = 0.22  # meters: how far paths and ruts wander from their drawn line
HIGH_SHARE = (0.72, 0.95)  # ground height quantiles of the open floor between which a sett turns from damp to dry

DRY_UNDER_GATE = 1.4  # meters out from the gatehouse face that stay dry
APRON_FULL, APRON_FADE = 0.25, 0.85  # silt apron along wall bases: solid to here, gone by there, in meters
TRACK_REACH = 7.0  # meters along the roads over which the mud carried in from the gate thins out
TRACK_RAISE = 0.0005  # meters of mud that fill the joints and hollows where it lies thick
GRATE_SILT_RAISE = 0.008  # meters of silt banked around the grate
LANE_HALF = 1.05  # half width of the cart lane worn from the gate into the yard, meters
LANE_REACH = 12.0  # meters along the lane over which its wear fades


# ---------------------------------------------------------------- plan and sites
def _plan():
    try:
        return location.plan()
    except (OSError, ValueError):
        return {}


def _wall_rects(plan):
    """(cx, cy, half width, half depth, rotation in radians) of every wall block, as build_block lays them out."""
    out = []
    for b in plan.get("blocks", {}).values():
        if not isinstance(b, dict):
            continue
        if "from" in b:
            ax, ay = b["from"]
            bx, by = b["to"]
            out.append(((ax + bx) / 2, (ay + by) / 2, (math.hypot(bx - ax, by - ay) + b["t"] * 0.5) / 2, b["t"] / 2,
                        math.atan2(by - ay, bx - ax)))
        elif "center" in b:
            out.append((*b["center"], b["size"][0] / 2, b["size"][1] / 2, math.radians(b.get("rot_z", 0))))
    return out


def _gatehouse(plan):
    """The wall block with the gate opening, as a rectangle like _wall_rects gives, or None."""
    for b in plan.get("blocks", {}).values():
        if isinstance(b, dict) and "cut_gate" in b and "center" in b:
            return (*b["center"], b["size"][0] / 2, b["size"][1] / 2, math.radians(b.get("rot_z", 0)))
    return None


def _frame(pos, rot_deg):
    """Local meters of a prop to world: a function (x, y) -> (X, Y), and the prop's rotation in radians."""
    r = math.radians(rot_deg)
    c, sn = math.cos(r), math.sin(r)
    return (lambda x, y: (pos[0] + x * c - y * sn, pos[1] + x * sn + y * c)), r


def _sites(plan):
    """Named places that wear the ground. Props in plan.json win over the defaults.

    The stable and the forge are given as frames (local meters to world), since both are placed
    with a rotation: the stable's open front is local -Y, its roof spans local x -2..2 and
    y -1.65..1.5; the forge's front is local -Y and its work area lies 1 to 2 m in front.
    """
    props = plan.get("props", {})
    south = plan.get("blocks", {}).get("south_parapet")
    parapet = (tuple(south["from"]), tuple(south["to"])) if south else ((-10.4, -12.9), (2.9, -10.4))

    def at(key, default):
        return tuple(props[key]["pos"]) if key in props else default

    def frame(key, pos, rot):
        p = props.get(key)
        return _frame(tuple(p["pos"]) if p else pos, p.get("rot_z", rot) if p else rot)

    return {
        "gate": at("gate_door", (-1.15, 3.0)),
        "well": at("well", (-4.6, -6.9)),
        "cart": at("cart", (2.9, -6.6)),
        "shed": at("shed", (-8.25, 0.87)),
        "brazier": at("brazier", (-7.0, -0.5)),
        "brazier2": at("brazier#2", (-7.6, -7.9)),
        "grate": at("grate", (-0.4, -2.6)),
        "gallows": at("gallows", (5.78, -0.72)),
        "stair": at("wall_stair", (-9.8, -7.6)),
        "parapet": parapet,
        "stable": frame("stable", (9.8, -6.3), -90.0),  # against the east wall, x 8.2..11.3
        "forge": frame("forge", (5.8, -3.95), 0.0),
    }


def _paths(s):
    """Worn routes as waypoint lists: (name, points, half width m, weight 0..1, hooves)."""
    gx, gy = s["gate"]
    wx, wy = s["well"]
    return [
        ("gate road", [(gx, gy - 0.5), (gx + 0.05, 1.2), (gx + 0.2, -0.3)], 1.0, 1.0, False),
        ("cart road", _tracks(s)[0][0] + _tracks(s)[1][0][1:], 0.78, 0.9, False),
        ("stable road", _tracks(s)[0][0] + _tracks(s)[2][0][1:], 0.82, 0.95, True),
        ("well road", [(gx + 0.2, -0.3), (-1.9, -1.8), (-3.2, -3.9), (wx + 0.2, wy + 1.3)], 0.95, 0.9, False),
        ("shed road", [(gx + 0.2, -0.3), (-2.8, -0.8), (-4.9, -1.0), (s["brazier"][0] + 0.2, s["brazier"][1] - 0.8)],
         0.8, 0.85, False),
        ("stair road", [(wx - 0.9, wy - 0.4), (-7.3, -6.9), (s["stair"][0] + 0.6, s["stair"][1] + 0.2)], 0.7, 0.65, False),
        ("gallows spur", [(3.1, -4.5), (3.6, -3.4), (4.0, -2.4)], 0.5, 0.35, False),
        ("parapet walk", _parapet_walk(s), 0.6, 0.5, False),
    ]


def _parapet_walk(s):
    """Where the sentries pace: a line 1.7 m inside the south parapet, from the wall stair eastward."""
    (ax, ay), (bx, by) = s["parapet"]
    length = math.hypot(bx - ax, by - ay)
    nx, ny = -(by - ay) / length, (bx - ax) / length
    return [(ax + (bx - ax) * t + nx * 1.7, ay + (by - ay) * t + ny * 1.7) for t in (0.08, 0.3, 0.55, 0.8)]


def _tracks(s):
    """Wheel tracks as (waypoints, point before them): the gate road, then the cart and the stable branches.

    Each track is the line two wheel ruts follow. The branches start at the fork and take the
    gate road's direction with them.
    """
    gx, gy = s["gate"]
    cx, cy = s["cart"]
    stable = s["stable"][0]
    trunk = [(gx, gy - 0.5), (gx + 0.05, 1.2), (gx + 0.2, -0.3), (0.7, -1.4), (1.8, -3.0)]
    cart = [(1.8, -3.0), (cx - 0.5, cy + 1.7), (cx - 0.1, cy + 0.9)]
    forge = s["forge"][0]
    to_stable = [(1.8, -3.0), (3.1, -4.5), forge(-1.2, -2.2), stable(-0.3, -3.2), stable(0.0, -1.9)]
    return [(trunk, None), (cart, trunk[-2]), (to_stable, trunk[-2])]


def _drain_line(s):
    """The channel water follows from the gate down the middle of the road to the grate."""
    gx, gy = s["gate"]
    grate = s["grate"]
    return [(gx + 0.1, gy - 2.6), (gx + 0.3, -0.4), (grate[0] - 0.3, grate[1] + 1.2), (grate[0], grate[1] + 0.2),
            (grate[0] - 0.1, grate[1] - 1.4), (grate[0] - 0.6, grate[1] - 3.0)]


def _outfall(s):
    """The stone-lined channel that carries the grate's overflow south to a scupper in the parapet."""
    grate = s["grate"]
    (ax, ay), (bx, by) = s["parapet"]
    t = (grate[0] - 0.6 - ax) / (bx - ax)
    return [(grate[0] - 0.6, grate[1] - 3.0), (grate[0] - 1.1, grate[1] - 5.6), (grate[0] - 1.4, ay + (by - ay) * t + 0.9)]


def _spline(pts, per=12, lead=None):
    """Catmull-Rom curve through the waypoints, so ruts and paths bend smoothly instead of kinking.

    `lead` is the point before the first waypoint, which a branch needs to leave its trunk without a kink.
    """
    p = [np.array(q, float) for q in pts]
    p = [np.array(lead, float) if lead else 2 * p[0] - p[1]] + p + [2 * p[-1] - p[-2]]
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for t in np.linspace(0.0, 1.0, per, endpoint=False):
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    out.append(p[-2])
    return [(float(q[0]), float(q[1])) for q in out]


def _discs(s):
    """Trodden standing places: (center, radius m, weight): around the braziers, the well, in front of the forge and stable."""
    stable, forge = s["stable"][0], s["forge"][0]
    return [
        (s["brazier"], 1.15, 0.7),
        (s["brazier2"], 1.1, 0.6),
        (s["well"], 1.7, 0.75),
        (forge(0.4, -1.6), 1.6, 0.8),
        (stable(0.9, -2.5), 1.4, 0.85),
        (stable(-0.9, -2.5), 1.4, 0.85),
        (stable(0.0, -3.6), 1.5, 0.65),
    ]


def _bowls(s):
    """Shallow low places (cx, cy, half length m, half width m, rotation rad) where water gathers in front of the fires.

    People stand there to warm their hands and the ground has been worn down, one in front of each
    brazier, one under the gate torches and one at the forge mouth.
    """
    forge, forge_rot = s["forge"]
    fx, fy = forge(0.0, -1.9)
    gx = s["gate"][0]
    return [
        (s["brazier"][0] + 0.3, s["brazier"][1] - 1.9, 1.5, 0.75, 0.10),
        (s["brazier2"][0] + 0.3, s["brazier2"][1] - 1.6, 1.5, 0.70, -0.12),
        (gx - 2.6, -1.9, 1.5, 0.70, 0.05),
        (fx, fy, 1.6, 0.80, forge_rot),
    ]


def _roofs(s):
    """Footprints (cx, cy, half x, half y, rotation rad) that keep the rain off the ground below."""
    shed = s["shed"]
    stable, rot = s["stable"]
    return [
        (shed[0], shed[1], 2.2, 2.15, 0.0),
        (*s["gallows"], 1.8, 1.5, math.radians(-46.0)),
        (*s["well"], 1.1, 0.95, 0.0),
        (*stable(0.0, -0.075), 2.0, 1.575, rot),
    ]


def _drips(s):
    """Eave lines where roof water falls: ((x0, y0), (x1, y1)) just outside the roof edge."""
    shed, well, stable = s["shed"], s["well"], s["stable"][0]
    return [
        ((shed[0] - 2.2, shed[1] - 2.4), (shed[0] + 2.2, shed[1] - 2.4)),
        ((well[0] - 1.1, well[1] - 1.12), (well[0] + 1.1, well[1] - 1.12)),
        ((well[0] - 1.1, well[1] + 1.12), (well[0] + 1.1, well[1] + 1.12)),
        (stable(-2.0, -1.8), stable(2.0, -1.8)),
    ]


# ---------------------------------------------------------------- numpy helpers
def _grid():
    xs = MAP_X0 + (np.arange(MAP_W) + 0.5) / PPM
    ys = MAP_Y0 + (np.arange(MAP_H) + 0.5) / PPM
    X, Y = np.meshgrid(xs.astype(np.float32), ys.astype(np.float32))
    return X, Y


def _smooth(e0, e1, x):
    """GLSL smoothstep; e0 > e1 gives a falling edge."""
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _blur(a, sigma_m):
    """Gaussian blur through the FFT; the map edges wrap, which is outside the floor."""
    fy = np.fft.fftfreq(a.shape[0])[:, None]
    fx = np.fft.rfftfreq(a.shape[1])[None, :]
    sp = sigma_m * PPM
    gain = np.exp(-2.0 * math.pi ** 2 * sp ** 2 * (fx * fx + fy * fy))
    return np.fft.irfft2(np.fft.rfft2(a) * gain, s=a.shape).astype(np.float32)


def _fbm(rng, size_m, octaves=3, gain=0.55):
    """Smooth noise of unit standard deviation with features of about size_m."""
    out = np.zeros((MAP_H, MAP_W), np.float32)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        n = _blur(rng.standard_normal((MAP_H, MAP_W)).astype(np.float32), size_m * 0.35 / 2 ** o)
        out += n / n.std() * amp
        norm += amp * amp
        amp *= gain
    return out / math.sqrt(norm)


def _segment(X, Y, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = np.clip(((X - a[0]) * dx + (Y - a[1]) * dy) / (dx * dx + dy * dy), 0.0, 1.0)
    return np.hypot(X - (a[0] + t * dx), Y - (a[1] + t * dy)), t, math.hypot(dx, dy)


def _polyline(X, Y, pts, offset=0.0):
    """Distance to a waypoint line (every segment shifted sideways by `offset`) and arc length at the nearest point."""
    best = np.full(X.shape, 1e9, np.float32)
    along = np.zeros(X.shape, np.float32)
    start = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        nx, ny = -(b[1] - a[1]) / length * offset, (b[0] - a[0]) / length * offset
        d, t, _ = _segment(X, Y, (a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny))
        closer = d < best
        best = np.where(closer, d, best)
        along = np.where(closer, start + t * length, along)
        start += length
    return best, along


def _point_on(pts, s):
    """Point, and unit direction, at arc length s along a waypoint line."""
    for a, b in zip(pts[:-1], pts[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if s <= length:
            u = (b[0] - a[0]) / length, (b[1] - a[1]) / length
            return (a[0] + u[0] * s, a[1] + u[1] * s), u
        s -= length
    return None, None


def _rect(X, Y, r):
    """Meters from each point to a rotated rectangle (0 inside)."""
    cx, cy, hx, hy, rot = r
    c, s = math.cos(rot), math.sin(rot)
    px, py = X - cx, Y - cy
    qx = np.maximum(np.abs(px * c + py * s) - hx, 0.0)
    qy = np.maximum(np.abs(-px * s + py * c) - hy, 0.0)
    return np.hypot(qx, qy)


def _inside(X, Y, r, margin=0.0):
    """1 inside a rotated rectangle grown by `margin`, 0 outside, soft over 0.15 m."""
    cx, cy, hx, hy, rot = r
    c, s = math.cos(rot), math.sin(rot)
    px, py = X - cx, Y - cy
    q = np.maximum(np.abs(px * c + py * s) - hx - margin, np.abs(-px * s + py * c) - hy - margin)
    return _smooth(0.08, -0.08, q)


def _in_polygon(X, Y, poly):
    """True inside a polygon (even-odd rule), for a list of (x, y) corners."""
    inside = np.zeros(X.shape, bool)
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if y0 == y1:
            continue
        crosses = (Y < y0) != (Y < y1)
        inside ^= crosses & (X < x0 + (Y - y0) * (x1 - x0) / (y1 - y0))
    return inside


def _window(X, Y, cx, cy, reach):
    """Slices of the map around a world point, for painting small marks."""
    i0 = max(int((cy - reach - MAP_Y0) * PPM), 0)
    i1 = min(int((cy + reach - MAP_Y0) * PPM) + 1, MAP_H)
    j0 = max(int((cx - reach - MAP_X0) * PPM), 0)
    j1 = min(int((cx + reach - MAP_X0) * PPM) + 1, MAP_W)
    return slice(i0, i1), slice(j0, j1)


# ---------------------------------------------------------------- the ground history
def _stream(name):
    """A random generator of its own for each feature, so tuning one leaves the others where they are."""
    return np.random.default_rng([GROUND_SEED, zlib.crc32(name.encode())])


def ground_maps(plan):
    """All 2D fields of the floor, each (MAP_H, MAP_W) float32 with row 0 at MAP_Y0, computed once per build."""
    return gm.get_maps(types.SimpleNamespace(**globals()), plan)


def _ground_maps(plan):
    """The calculation behind ground_maps. See the module docstring."""
    rng = _stream("paths")
    X, Y = _grid()
    s = _sites(plan)
    walls = _wall_rects(plan)

    # ---- walls: distance to the nearest face, and where two walls meet
    reach = [np.exp(-_rect(X, Y, w) / CORNER_REACH) for w in walls]
    d_wall = np.min([_rect(X, Y, w) for w in walls], axis=0) if walls else np.full(X.shape, 9.0, np.float32)
    corner = np.clip(np.sum(reach, axis=0) - np.max(reach, axis=0), 0.0, 1.0) if walls else 0 * X
    wander = _fbm(_stream('wander'), 1.6, 2) * 0.12  # meters the wall-foot features wobble

    # ---- paths: traffic, wheel ruts, hoof pits
    Xw = X + _fbm(rng, 3.2, 3) * MEANDER
    Yw = Y + _fbm(rng, 3.2, 3) * MEANDER
    traffic = np.zeros_like(X)
    ruts = np.zeros_like(X)
    hooves = np.zeros_like(X)
    patchy = _fbm(rng, 1.1, 2)
    rut_break = _fbm(rng, 1.3, 2)
    rut_pools = _smooth(-0.6, 0.9, _fbm(_stream("rut_pools"), 1.1, 2))  # a rut holds water in stretches and is mud in between
    for _, pts, half, weight, hoofed in _paths(s):
        pts = _spline(pts)
        d = _polyline(Xw, Yw, pts)[0]
        t = weight * _smooth(half * 1.3, half * 0.3, d) * np.clip(0.8 + 0.2 * patchy, 0.0, 1.0)
        traffic = 1.0 - (1.0 - traffic) * (1.0 - t)
        if hoofed:
            length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts[:-1], pts[1:]))
            step = 0
            for sl in np.arange(0.4, length - 0.2, 0.34):
                (px, py), (ux, uy) = _point_on(pts, sl)
                side = 1.0 if step % 2 == 0 else -1.0
                step += 1
                px += -uy * side * 0.2 + rng.normal(0, 0.05) + ux * rng.normal(0, 0.05)
                py += ux * side * 0.2 + rng.normal(0, 0.05) + uy * rng.normal(0, 0.05)
                rows, cols = _window(X, Y, px, py, 0.35)
                u = (X[rows, cols] - px) * ux + (Y[rows, cols] - py) * uy
                v = -(X[rows, cols] - px) * uy + (Y[rows, cols] - py) * ux
                size = rng.uniform(0.9, 1.25)
                pit = np.exp(-(u * u / (2 * (0.085 * size) ** 2) + v * v / (2 * (0.058 * size) ** 2)))
                hooves[rows, cols] = np.maximum(hooves[rows, cols], pit * weight)
    for track, lead in _tracks(s):
        pts = _spline(track, lead=lead)
        dr = np.minimum(_polyline(Xw, Yw, pts, RUT_GAUGE / 2)[0], _polyline(Xw, Yw, pts, -RUT_GAUGE / 2)[0])
        ruts = np.maximum(ruts, _smooth(RUT_HALF * 1.6, RUT_HALF * 0.35, dr) * _smooth(-2.4, -1.1, rut_break))
    stand = np.zeros_like(X)
    for (cx, cy), radius, weight in _discs(s):
        dist = np.hypot(Xw - cx, Yw - cy)
        t = weight * _smooth(radius + 0.45, radius - 0.15, dist) * np.clip(0.8 + 0.2 * patchy, 0.0, 1.0)
        traffic = 1.0 - (1.0 - traffic) * (1.0 - t)
        stand = np.maximum(stand, weight * _smooth(radius * 1.1, radius * 0.2, dist))
    traffic = np.clip(traffic, 0.0, 1.0)

    # ---- rain shadow and drips
    shadow = np.max([_inside(X, Y, r) for r in _roofs(s)], axis=0)
    drip = np.zeros_like(X)
    pool = _smooth(-0.5, 0.5, _fbm(_stream('drip'), 0.9, 2))  # a drip trench holds water in stretches
    for a, b in _drips(s):
        d, _, _ = _segment(X, Y, a, b)
        drip = np.maximum(drip, np.exp(-(d / DRIP_WIDTH) ** 2) * (0.55 + 0.45 * pool))
    drip *= 1.0 - shadow

    # ---- the front of the gate: a worn hollow where carts and people stop
    gx, gy = s["gate"]
    gate_hollow = np.exp(-(((X - gx) / 1.9) ** 2 + ((Y - (gy - 1.25)) / 0.62) ** 2))

    # ---- bowls in front of the fires, with ragged outlines
    bowls = np.zeros_like(X)
    ragged_edge = _fbm(_stream('bowls'), 0.8, 2) * 0.12
    for cx, cy, hx, hy, rot in _bowls(s):
        c, sn = math.cos(rot), math.sin(rot)
        u = ((X - cx) * c + (Y - cy) * sn) / hx
        v = (-(X - cx) * sn + (Y - cy) * c) / hy
        bowls = np.maximum(bowls, _smooth(1.0, 0.3, np.hypot(u, v) + ragged_edge))

    # ---- the drain channel: rain runs down the middle of the gate road to the grate
    drain = np.exp(-(_polyline(Xw, Yw, _spline(_drain_line(s)))[0] / DRAIN_WIDTH) ** 2)
    outfall = np.exp(-(_polyline(Xw, Yw, _spline(_outfall(s), lead=_drain_line(s)[-2]))[0] / OUTFALL_WIDTH) ** 2)
    outfall *= 0.45 + 0.55 * _smooth(-0.6, 0.6, _fbm(_stream("outfall"), 1.2, 2))  # it silts up in stretches

    # ---- the ground height, meters relative to the datum
    d_grate = np.hypot(X - s["grate"][0], Y - s["grate"][1])
    base = -CAMBER_DEPTH * np.exp(-(d_grate / CAMBER_RADIUS) ** 2)
    for size, std in SETTLE:
        base += _fbm(_stream(f'settle{size}'), size, 3 if size > 1 else 2) * std
    gutter = np.exp(-(((d_wall + wander) - GUTTER_AT) / GUTTER_WIDTH) ** 2) * (0.35 + 0.65 * _smooth(-0.8, 0.5, _fbm(_stream('gutter'), 1.7, 2)))
    gutter = np.maximum(gutter * 0.8, corner * (1.0 - _smooth(0.25, 1.1, d_wall)))
    apron = _smooth(APRON_FADE, APRON_FULL, d_wall + wander * 1.8)

    yard = gm.yard_mask(types.SimpleNamespace(**globals()), X, Y, plan, d_wall)
    macro = gm.macro_fields(types.SimpleNamespace(**globals()), X, Y, Xw, Yw, s, d_wall, corner, wander, traffic, shadow,
                            yard, patchy)
    earth = _earth_patches(_stream('earth'), X, Y, d_wall, traffic, shadow, macro["mud"], _fbm(_stream("earth_warp"), 0.4, 2))
    sills = _sills(Xw, Yw, s, _fbm(_stream("sills"), 0.7, 2))
    gate_lift, gate_pools = _gate_pools(X, Y, s, _fbm(_stream("gate_pools"), 0.6, 2))
    track = _tracked_mud(X, Y, Xw, Yw, s, patchy)
    lane = _cart_lane(Xw, Yw, s)
    grate_silt = _grate_silt(X, Y, s, _fbm(_stream('gsilt'), 0.7, 2))
    ground = (base - HOLLOW_DEPTH * _blur(traffic, 0.22) - RUT_DEPTH * ruts * np.clip(0.75 + 0.25 * rut_break, 0.3, 1.2) * (0.35 + 0.65 * rut_pools)
              - HOOF_DEPTH * hooves - GUTTER_DEPTH * gutter * (1.0 - apron * 0.5) - CORNER_DEPTH * corner * 0.5
              - DRIP_DEPTH * drip - GATE_DEPTH * gate_hollow - DRAIN_DEPTH * drain - OUTFALL_DEPTH * outfall - STAND_DEPTH * stand - BOWL_DEPTH * bowls
              - EARTH_DEPTH * earth - BARE_DEPTH * _smooth(0.5, 0.95, earth) - SUNK_DEPTH * macro["sunk"]
              + SILT_RAISE * apron * (1.0 - gutter) + TRACK_RAISE * track + GRATE_SILT_RAISE * grate_silt + SILL_HEIGHT * sills
)
    ground += 0.03 * shadow  # sheltered ground stays above the water

    # ---- water: the level is where the given share of the open floor lies below it
    open_floor = _in_polygon(X, Y, plan["platform"]["polygon"]) & (d_wall > 0.4) & (shadow < 0.5)
    level = float(np.clip(np.quantile(ground[open_floor], WATER_COVER), -0.07, 0.0))
    depth = np.clip(np.maximum(level - (ground + GATE_LIFT * gate_lift), gate_pools), DEPTH_MIN, DEPTH_MAX)
    standing = _smooth(0.0, 0.004, depth)
    halo = np.clip(_blur(standing, 0.30) * 2.2, 0.0, 1.0) * (1.0 - standing)

    # ---- dry setts: the highest ground, the lee of the gatehouse, the shelter of roofs
    q_lo, q_hi = np.quantile(ground[open_floor], HIGH_SHARE)
    high = _smooth(q_lo, q_hi, ground)
    gatehouse = _gatehouse(plan)
    lee = _smooth(DRY_UNDER_GATE, 0.5, _rect(X, Y, gatehouse)) * 0.9 if gatehouse else 0 * X
    dry = np.clip(np.maximum(np.maximum(high, lee) * (1.0 - 0.75 * traffic), shadow * 0.9) * (1.0 - standing), 0.0, 1.0)

    straw = _straw(_stream('straw'), X, Y, s, plan, traffic, shadow)
    silt = np.clip(np.maximum(apron * 0.9, halo), 0.0, 1.0)
    dung = _dung_zone(X, Y, s)

    return {
        "depth": depth, "traffic": traffic, "ruts": np.clip(ruts, 0.0, 1.0), "earth": earth,
        "dry": dry, "straw": straw, "silt": silt, "hooves": np.clip(hooves, 0.0, 1.0),
        "ground": ground, "walls": d_wall,
        "track": track, "lane": lane, "dung": dung, "grate_silt": grate_silt,
        "mud": macro["mud"], "sunk": macro["sunk"], "trail": macro["trail"], "moss": macro["moss"], "yard": yard,
    }


def _earth_patches(rng, X, Y, d_wall, traffic, shadow, mud, warp):
    """Soft blobs of packed earth where setts have been lost: on the busy paths, along wall feet and at the rim of the mud."""
    out = np.zeros_like(X)
    placed, tries = 0, 0
    while placed < 70 and tries < 6000:
        tries += 1
        x, y = rng.uniform(-12.5, 12.8), rng.uniform(-13.2, 8.6)
        i, j = int((y - MAP_Y0) * PPM), int((x - MAP_X0) * PPM)
        if d_wall[i, j] < 0.2:
            continue
        rim = 4.0 * mud[i, j] * (1.0 - mud[i, j])
        chance = 0.08 + 0.8 * traffic[i, j] + 0.3 * math.exp(-d_wall[i, j] / 0.8) + 0.5 * rim
        if rng.random() > chance * (1.0 - shadow[i, j] * 0.6):
            continue
        placed += 1
        r0 = rng.uniform(0.22, 0.55) * (1.0 + 0.4 * traffic[i, j])
        rows, cols = _window(X, Y, x, y, r0 * 2.6)
        patch = np.zeros(X[rows, cols].shape, np.float32)
        for _ in range(rng.integers(4, 8)):
            ox, oy = rng.normal(0, r0 * 0.8, 2)
            r = r0 * rng.uniform(0.4, 0.95)
            d = np.hypot(X[rows, cols] - (x + ox), Y[rows, cols] - (y + oy)) + warp[rows, cols] * r * 0.55
            patch = np.maximum(patch, _smooth(r * 1.15, r * 0.55, d))
        out[rows, cols] = np.maximum(out[rows, cols], patch)
    return out


def _gate_pools(X, Y, s, ragged):
    """The apron in front of the gate and the depth in meters of the shallow pools on it: (lift 0..1, pools)."""
    gx, gy = s["gate"]
    lift = np.exp(-(((X - (gx - 0.4)) / 3.5) ** 4 + ((Y - (gy - 2.6)) / 3.0) ** 4))
    pools = np.zeros_like(X)
    for dx, dy, hx, hy, rot, depth in GATE_POOLS:
        c, sn = math.cos(rot), math.sin(rot)
        u = ((X - (gx + dx)) * c + (Y - (gy + dy)) * sn) / hx
        v = (-(X - (gx + dx)) * sn + (Y - (gy + dy)) * c) / hy
        pools = np.maximum(pools, depth * _smooth(1.05, 0.15, np.hypot(u, v) + 0.2 * ragged))
    return lift, pools


def _sills(Xw, Yw, s, ragged):
    """Cross ridges in the drain channel: silt and tilted setts that stop the water and cut it into pools."""
    d, along = _polyline(Xw, Yw, _spline(_drain_line(s)))
    out = np.zeros_like(Xw)
    for k, at in enumerate(SILL_STATIONS):
        reach = 0.95 + 0.25 * math.sin(k * 2.1)
        out = np.maximum(out, np.exp(-((along - at - 0.35 * ragged) / 0.22) ** 2) * _smooth(reach, reach * 0.4, d))
    return out


def _straw(rng, X, Y, s, plan, traffic, shadow):
    """Straw trodden into the setts: around the shed and the stable, the piles in the plan, the cart, the forge."""
    out = np.zeros_like(X)

    def blob(c, sigma, amp):
        return amp * np.exp(-((X - c[0]) ** 2 + (Y - c[1]) ** 2) / (2 * sigma ** 2))

    for key, p in plan.get("props", {}).items():
        if key.split("#")[0] == "straw_pile":
            out += blob(p["pos"], 0.85 * p.get("scale", 1.0), 0.8)
    out += blob((s["shed"][0] + 0.5, s["shed"][1] - 0.8), 1.7, 0.9)
    out += 0.7 * _inside(X, Y, _roofs(s)[0], margin=0.3)
    stable, forge = s["stable"][0], s["forge"][0]
    out += blob(stable(0.0, -2.2), 1.9, 0.9) + 0.8 * _inside(X, Y, _roofs(s)[3], margin=0.3)
    out += blob(forge(0.4, -1.6), 1.4, 0.6)
    out += blob((s["cart"][0] - 0.4, s["cart"][1] + 0.4), 1.6, 0.65)
    stable_road = _polyline(X, Y, _spline(_tracks(s)[0][0] + _tracks(s)[2][0][1:]))[0]
    out += 0.45 * _smooth(1.2, 0.2, stable_road) * traffic
    return np.clip(out * np.clip(0.65 + 0.35 * _fbm(rng, 0.8, 2), 0.2, 1.2), 0.0, 1.0)


def _tracked_mud(X, Y, Xw, Yw, s, patchy):
    """Mud carried in through the gate on boots and wheels: solid in the passage, thinning along the roads."""
    gx, gy = s["gate"]
    passage = _inside(X, Y, (gx + 0.1, gy + 3.2, 1.5, 3.4, 0.0))  # the gate floor, x -2.6..0.3
    apron = np.exp(-(((Xw - (gx + 0.1)) / 2.1) ** 2 + ((Yw - (gy - 1.5)) / 1.7) ** 2))
    routes = np.zeros_like(X)
    gate_len = 3.2
    for name, pts, half, weight, _ in _paths(s):
        if name not in ("gate road", "cart road", "stable road", "well road", "shed road"):
            continue
        d, along = _polyline(Xw, Yw, _spline(pts))
        base = gate_len if name in ("well road", "shed road") else 0.0
        t = weight * _smooth(half * 1.5, half * 0.25, d) * np.exp(-(along + base) / TRACK_REACH)
        routes = 1.0 - (1.0 - routes) * (1.0 - t)
    dy = (gy - 0.2) - Yw  # meters south of the gate mouth
    cone = _smooth(1.0, 0.3, np.abs(Xw - (gx + 0.1)) / (1.1 + 0.6 * np.maximum(dy, 0.0))) * np.exp(-np.maximum(dy, 0.0) / TRACK_REACH)
    cone *= _smooth(-0.4, 0.3, dy)
    track = np.maximum(np.maximum(passage * 0.95, apron * 0.9), np.maximum(routes, cone * 0.8))
    return np.clip(track * np.clip(0.72 + 0.28 * patchy, 0.0, 1.2), 0.0, 1.0)


def _cart_lane(Xw, Yw, s):
    """The lane the carts have worn from the gate into the yard: the trunk track and its two branches."""
    lane = np.zeros_like(Xw)
    for track, lead in _tracks(s):
        d, along = _polyline(Xw, Yw, _spline(track, lead=lead))
        lane = np.maximum(lane, _smooth(LANE_HALF * 1.35, LANE_HALF * 0.4, d) * np.exp(-along / LANE_REACH))
    return np.clip(lane, 0.0, 1.0)


def _dung_zone(X, Y, s):
    """Where animals have stood and dropped dung: in front of the stable and forge, around the cart and the cookhouse."""
    stable, forge = s["stable"][0], s["forge"][0]
    cx, cy = s["cart"]
    shed = s["shed"]

    def blob(c, sigma, amp):
        return amp * np.exp(-((X - c[0]) ** 2 + (Y - c[1]) ** 2) / (2 * sigma ** 2))

    zone = (blob(stable(0.0, -2.5), 1.7, 1.0) + blob(stable(0.0, -4.0), 1.3, 0.6) + blob(forge(0.5, -1.9), 1.2, 0.55)
            + blob((cx - 0.3, cy + 0.4), 1.4, 0.75) + blob((shed[0] + 0.3, shed[1] - 1.7), 1.3, 0.5))
    return np.clip(zone, 0.0, 1.0)


def _grate_silt(X, Y, s, ragged):
    """Dark silt the drain water drops around the grate: a fan upstream where the water slows, a rim, a short tongue below."""
    gx, gy = s["grate"]
    dx, dy = X - (gx - 0.05), Y - (gy + 0.15)
    up = dy > 0
    half = 0.55 + 0.42 * np.maximum(dy, 0.0)
    fan = _smooth(1.0, 0.3, np.abs(dx) / half) * np.exp(-(np.maximum(dy, 0.0) / 1.5) ** 2) * up
    tongue = _smooth(1.0, 0.4, np.abs(dx) / 0.6) * np.exp(-(np.minimum(dy, 0.0) / 1.0) ** 2) * (~up) * 0.8
    rim = np.exp(-(np.hypot(dx, dy) / 0.85) ** 2)
    return np.clip(np.maximum(np.maximum(fan, tongue), rim) * np.clip(0.8 + 0.3 * ragged, 0.2, 1.2), 0.0, 1.0)


# ---------------------------------------------------------------- images
def _image(name, channels):
    """An 8-bit data image, one channel per entry, in the order of `channels`."""
    import bpy
    data = np.clip(np.stack(channels, axis=-1), 0.0, 1.0).astype(np.float32)
    img = bpy.data.images.new(name, MAP_W, MAP_H, alpha=True, float_buffer=False)
    img.colorspace_settings.name = "Non-Color"
    img.alpha_mode = "CHANNEL_PACKED"
    img.pixels.foreach_set(data.ravel())
    img.update()
    try:
        img.pack()  # a saved .blend keeps the maps
    except RuntimeError:
        pass
    return img


def ground_images(plan):
    m = ground_maps(plan)
    depth = (m["depth"] - DEPTH_MIN) / (DEPTH_MAX - DEPTH_MIN)
    a = _image("floor_map_a", [depth, m["traffic"], m["ruts"], m["earth"]])
    b = _image("floor_map_b", [m["dry"], m["straw"], m["silt"], m["hooves"]])
    c = _image("floor_map_c", [m["track"], m["dung"], m["grate_silt"], m["lane"]])
    d = _image("floor_map_d", [m["mud"], m["sunk"], m["trail"], m["moss"]])
    return a, b, c, d


# ---------------------------------------------------------------- node helpers
def _link(nt, sock, value):
    if hasattr(value, "node"):
        nt.links.new(value, sock)
    elif value is not None:
        if sock.type == "RGBA" and len(value) == 3:
            value = (*value, 1.0)
        sock.default_value = value


def _node(nt, idname, inputs=None, **attrs):
    n = nt.nodes.new(idname)
    for k, v in attrs.items():
        setattr(n, k, v)
    for k, v in (inputs or {}).items():
        _link(nt, n.inputs[k], v)
    return n


def _math(nt, op, a, b=None, c=None, clamp=False):
    n = _node(nt, "ShaderNodeMath", operation=op, use_clamp=clamp)
    for i, v in enumerate((a, b, c)):
        _link(nt, n.inputs[i], v)
    return n.outputs[0]


def _vec(nt, op, a, b=None, c=None):
    n = _node(nt, "ShaderNodeVectorMath", operation=op)
    for i, v in enumerate((a, b, c)):
        _link(nt, n.inputs[i], v)
    return n.outputs[0]


def _range(nt, value, lo, hi, to_lo=0.0, to_hi=1.0, smooth=False):
    n = _node(nt, "ShaderNodeMapRange",
              {"Value": value, "From Min": lo, "From Max": hi, "To Min": to_lo, "To Max": to_hi},
              interpolation_type="SMOOTHSTEP" if smooth else "LINEAR")
    return n.outputs["Result"]


def _mix(nt, fac, a, b, blend="MIX"):
    n = _node(nt, "ShaderNodeMix", data_type="RGBA", blend_type=blend)
    _link(nt, n.inputs[0], fac)
    _link(nt, n.inputs[6], a)
    _link(nt, n.inputs[7], b)
    return n.outputs[2]


def _mix_vec(nt, fac, a, b):
    n = _node(nt, "ShaderNodeMix", data_type="VECTOR")
    _link(nt, n.inputs[0], fac)
    _link(nt, n.inputs[4], a)
    _link(nt, n.inputs[5], b)
    return n.outputs[1]


def _noise(nt, vec, scale, detail=2.0, dims="3D", rough=0.5, distortion=0.0):
    n = _node(nt, "ShaderNodeTexNoise",
              {"Vector": vec, "Scale": scale, "Detail": detail, "Roughness": rough, "Distortion": distortion},
              noise_dimensions=dims)
    return n.outputs["Fac"]


def _xyz(nt, vec):
    n = _node(nt, "ShaderNodeSeparateXYZ", {"Vector": vec})
    return n.outputs["X"], n.outputs["Y"], n.outputs["Z"]


def _mix_float(nt, fac, a, b):
    n = _node(nt, "ShaderNodeMix", data_type="FLOAT")
    _link(nt, n.inputs[0], fac)
    _link(nt, n.inputs[2], a)
    _link(nt, n.inputs[3], b)
    return n.outputs[0]


def _white(nt, a, b, c):
    """Three values in 0..1, fixed for the point (a, b, c): a hash, not a texture."""
    vec = _node(nt, "ShaderNodeCombineXYZ", {"X": a, "Y": b, "Z": c}).outputs[0]
    noise = _node(nt, "ShaderNodeTexWhiteNoise", {"Vector": vec}, noise_dimensions="3D")
    rnd = _node(nt, "ShaderNodeSeparateColor", {"Color": noise.outputs["Color"]})
    return rnd.outputs["Red"], rnd.outputs["Green"], rnd.outputs["Blue"]


def _cut(nt, coord, pitch, jitter, other, seed):
    """Cut a line into runs of about `pitch`, each boundary strayed by a hash: index, start and end of the run holding `coord`.

    Only the boundaries of the run and its two neighbors can matter, so four hashes decide it.
    """
    k0 = _math(nt, "FLOOR", _math(nt, "DIVIDE", coord, pitch))

    def bound(k):
        h = _white(nt, k, other, seed)[0]
        stray = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", h, 0.5), 2.0 * jitter)
        return _math(nt, "MULTIPLY", _math(nt, "ADD", k, stray), pitch)

    before, start, stop, after = (bound(_math(nt, "ADD", k0, d)) for d in (-1.0, 0.0, 1.0, 2.0))
    below = _math(nt, "LESS_THAN", coord, start)
    above = _math(nt, "GREATER_THAN", coord, stop)
    index = _math(nt, "ADD", _math(nt, "SUBTRACT", k0, below), above)
    lo = _mix_float(nt, below, _mix_float(nt, above, start, stop), before)
    hi = _mix_float(nt, below, _mix_float(nt, above, stop, after), start)
    return index, lo, hi


def _paving(nt, pos, lane, sunk):
    """Setts laid in courses: rows in some regions, segmental fans in others.

    The floor is split into regions of about 3 m by a Voronoi texture. Each region has its own
    seed and either straight rows at a right angle, give or take a few degrees, or arcs about a point
    a few meters away. A course is a strip of about 12 to 15 cm whose edges stray from the grid;
    it is cut into setts of about 10 to 20 cm whose ends stray as well. A sett is a rounded box:
    a super-ellipse outline, a shoulder that bends down to the joint, a nearly flat crown that
    leans a little. Returns the per-sett values the material needs.
    """
    # ---- regions
    drift = _node(nt, "ShaderNodeTexNoise", {"Vector": pos, "Scale": 0.35, "Detail": 2.0, "Roughness": 0.5},
                  noise_dimensions="3D").outputs["Color"]
    wide = _vec(nt, "MULTIPLY_ADD", _vec(nt, "SUBTRACT", drift, (0.5, 0.5, 0.5)), (1.4, 1.4, 0.0), pos)
    args = {"Vector": wide, "Scale": REGION_SCALE, "Randomness": 0.95}
    region = _node(nt, "ShaderNodeTexVoronoi", args, voronoi_dimensions="2D", feature="F1")
    seam = _math(nt, "DIVIDE", _node(nt, "ShaderNodeTexVoronoi", args, voronoi_dimensions="2D",
                                      feature="DISTANCE_TO_EDGE").outputs["Distance"], REGION_SCALE)
    site = _node(nt, "ShaderNodeVectorMath", {0: region.outputs["Position"], 3: 1.0 / REGION_SCALE},
                 operation="SCALE").outputs[0]
    sx, sy, _ = _xyz(nt, site)
    a0, a1, a2 = _white(nt, sx, sy, 3.7)
    c0, c1, c2 = _white(nt, _math(nt, "ADD", sx, 9.1), sy, 1.3)
    d0, d1, _ = _white(nt, _math(nt, "ADD", sx, 4.4), _math(nt, "ADD", sy, 1.7), 6.6)
    seed = _math(nt, "MULTIPLY", a0, 40.0)
    fan = _math(nt, "GREATER_THAN", a1, 1.0 - FAN_SHARE)
    phi = _math(nt, "MULTIPLY", a2, 2.0 * math.pi)
    reach = _math(nt, "MULTIPLY", fan, _math(nt, "MULTIPLY_ADD", c2, FAN_RADIUS[1] - FAN_RADIUS[0], FAN_RADIUS[0]))
    right_angle = _math(nt, "MULTIPLY", _math(nt, "FLOOR", _math(nt, "MULTIPLY", c0, 2.0)), math.pi / 2)
    alpha = _math(nt, "ADD", right_angle, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", c1, 0.5), 0.42))
    beta = _mix_float(nt, fan, alpha, _math(nt, "ADD", phi, math.pi))  # a fan's axis points from its center to the region
    center_x = _math(nt, "ADD", sx, _math(nt, "MULTIPLY", reach, _math(nt, "COSINE", phi)))
    center_y = _math(nt, "ADD", sy, _math(nt, "MULTIPLY", reach, _math(nt, "SINE", phi)))

    # ---- the frame of the region: x along the course, y across; a fan's y is the radius
    wobble = _node(nt, "ShaderNodeTexNoise", {"Vector": pos, "Scale": 2.6, "Detail": 2.0, "Roughness": 0.5},
                   noise_dimensions="3D").outputs["Color"]
    warped = _vec(nt, "MULTIPLY_ADD", _vec(nt, "SUBTRACT", wobble, (0.5, 0.5, 0.5)), (COURSE_WAVE, COURSE_WAVE, 0.0), pos)
    wx, wy, _ = _xyz(nt, warped)
    rel_x, rel_y = _math(nt, "SUBTRACT", wx, center_x), _math(nt, "SUBTRACT", wy, center_y)
    cb, sb = _math(nt, "COSINE", beta), _math(nt, "SINE", beta)
    along = _math(nt, "ADD", _math(nt, "MULTIPLY", rel_x, cb), _math(nt, "MULTIPLY", rel_y, sb))
    across = _math(nt, "SUBTRACT", _math(nt, "MULTIPLY", rel_y, cb), _math(nt, "MULTIPLY", rel_x, sb))
    radius = _math(nt, "SQRT", _math(nt, "ADD", _math(nt, "MULTIPLY", along, along), _math(nt, "MULTIPLY", across, across)))
    v = _mix_float(nt, fan, across, radius)

    # ---- courses, then setts in each course
    row_h = _math(nt, "MULTIPLY_ADD", d0, ROW_HEIGHT[1] - ROW_HEIGHT[0], ROW_HEIGHT[0])
    row, row_lo, row_hi = _cut(nt, v, row_h, ROW_JITTER, 7.0, seed)
    row_mid = _math(nt, "MULTIPLY", _math(nt, "ADD", row_lo, row_hi), 0.5)
    row_half = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", row_hi, row_lo), 0.5)
    dy = _math(nt, "SUBTRACT", v, row_mid)
    theta = _math(nt, "ARCTAN2", across, along)
    u = _mix_float(nt, fan, along, _math(nt, "MULTIPLY", theta, row_mid))  # arc length on the row's middle line
    h0, h1, _ = _white(nt, row, seed, 1.0)
    length = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY_ADD", d1, SETT_LENGTH[1] - SETT_LENGTH[0], SETT_LENGTH[0]),
                   _math(nt, "MULTIPLY_ADD", h0, 0.32, 0.84))
    u = _math(nt, "MULTIPLY_ADD", h1, 10.0, u)  # every course starts at its own phase
    sett, u_lo, u_hi = _cut(nt, u, length, SETT_JITTER, row, seed)
    dx = _math(nt, "SUBTRACT", u, _math(nt, "MULTIPLY", _math(nt, "ADD", u_lo, u_hi), 0.5))
    half_x = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", u_hi, u_lo), 0.5)

    # ---- one sett: size, lean, and the random values that tell it from its neighbors
    b0, b1, b2 = _white(nt, sett, row, _math(nt, "ADD", seed, 11.0))
    t0, t1, t2 = _white(nt, _math(nt, "ADD", sett, 0.37), _math(nt, "ADD", row, 0.61), _math(nt, "ADD", seed, 23.0))
    s0, s1, s2 = _white(nt, _math(nt, "ADD", sett, 0.71), _math(nt, "ADD", row, 0.29), _math(nt, "ADD", seed, 37.0))
    gap = _math(nt, "ADD", _math(nt, "MULTIPLY_ADD", b2, 0.0015, JOINT_GAP),
                _math(nt, "ADD", _math(nt, "MULTIPLY", lane, 0.004), _math(nt, "MULTIPLY", sunk, SUNK_GAP)))
    hx = _math(nt, "MAXIMUM", _math(nt, "SUBTRACT", half_x, gap), 0.012)
    hrow = _math(nt, "MAXIMUM", _math(nt, "SUBTRACT", row_half, gap), 0.012)
    hy = _math(nt, "MULTIPLY", hrow, _math(nt, "MULTIPLY_ADD", b1, 0.15, 0.85))  # a sett need not fill its course
    dy = _math(nt, "SUBTRACT", dy, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", hrow, hy), _math(nt, "MULTIPLY_ADD", t2, 2.0, -1.0)))
    hy_here = _math(nt, "MULTIPLY", hy, _math(nt, "ADD", 1.0, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", t0, 0.5),
                                                                    _math(nt, "MULTIPLY", _math(nt, "DIVIDE", dx, hx), 0.5))))
    hx_here = _math(nt, "MULTIPLY", hx, _math(nt, "ADD", 1.0, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", t1, 0.5),
                                                                    _math(nt, "MULTIPLY", _math(nt, "DIVIDE", dy, hy), 0.4))))  # tapered, no two alike
    qx = _math(nt, "DIVIDE", _math(nt, "ABSOLUTE", dx), hx_here)
    qy = _math(nt, "DIVIDE", _math(nt, "ABSOLUTE", dy), hy_here)
    quartic = _math(nt, "ADD", _math(nt, "POWER", qx, 4.0), _math(nt, "POWER", qy, 4.0))
    rim = _math(nt, "POWER", quartic, 0.25)  # 0 in the middle of the sett, 1 on its outline, a super-ellipse
    rim = _math(nt, "ADD", rim, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, pos, 13.0, 2.0, "2D"), 0.5), 0.16))  # a wobbly outline
    small = _math(nt, "MINIMUM", hx, hy)
    edge = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, rim), small)  # meters inside the outline
    edge = _math(nt, "MINIMUM", edge, _math(nt, "SUBTRACT", seam, 0.004))  # a joint runs along the border of a region

    shoulder = _range(nt, edge, 0.0, SHOULDER, smooth=True)
    dome = _range(nt, _math(nt, "DIVIDE", edge, small), 0.0, 1.0)
    profile = _math(nt, "MULTIPLY", shoulder, _math(nt, "MULTIPLY_ADD", dome, 0.18, 0.82))
    lean = _math(nt, "ADD", _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", t0, 0.5), _math(nt, "DIVIDE", dx, hx)),
                 _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", t1, 0.5), _math(nt, "DIVIDE", dy, hy)))
    stand = _math(nt, "ADD", _math(nt, "MULTIPLY_ADD", s2, 0.4, 0.8),
                  _math(nt, "MULTIPLY", lean, _math(nt, "MULTIPLY_ADD", sunk, STONE_TILT * 2.0, STONE_TILT)))
    stand = _math(nt, "MULTIPLY", stand, _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", sunk, 0.4)))  # sunk setts stand lower
    return {"edge": edge, "profile": profile, "height": _math(nt, "MULTIPLY", profile, stand), "value": b0,
            "gloss": s0, "lost": s1, "region": a0}


def water_ripples(nt, pos):
    """Height (0.03 m bump distance) of a puddle surface; also used by mud.py.

    Fine ripples and a slow swell, wind-driven: their crests run along x, so a lit
    point is smeared along y into a streak. Rain rings from two sparse Voronoi layers
    sit on top, each ring with its own size and wavelength.
    """
    crests = _vec(nt, "MULTIPLY", pos, (RIPPLE_STRETCH, 1.0, 1.0))
    fine = _noise(nt, crests, RIPPLE_SCALES[0], 2.0, "3D", rough=0.6)
    swell = _noise(nt, crests, RIPPLE_SCALES[1], 2.0, "3D", rough=0.5)
    rings = 0.0
    for scale, offset, cover in RING_LAYERS:
        cell = _node(nt, "ShaderNodeTexVoronoi", {"Vector": _vec(nt, "ADD", pos, (*offset, 0.0)), "Scale": scale,
                                                   "Randomness": 1.0}, voronoi_dimensions="2D", feature="F1")
        rnd = _node(nt, "ShaderNodeSeparateColor", {"Color": cell.outputs["Color"]})
        r = cell.outputs["Distance"]  # 0 at the center, about 0.5 at the cell edge
        on = _range(nt, rnd.outputs["Red"], 1.0 - cover - 0.03, 1.0 - cover)
        radius = _math(nt, "MULTIPLY_ADD", rnd.outputs["Green"], 0.22, 0.18)  # each ring has its own size
        waves = _math(nt, "MULTIPLY_ADD", rnd.outputs["Blue"], 3.0, 4.0)  # and its own wavelength
        wave = _math(nt, "SINE", _math(nt, "MULTIPLY", r, _math(nt, "MULTIPLY", waves, 2 * math.pi)))
        fade = _range(nt, r, 0.04, radius, 1.0, 0.0, smooth=True)
        rings = _math(nt, "ADD", rings, _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", wave, fade), on))
    surface = _math(nt, "ADD", _math(nt, "MULTIPLY", fine, RIPPLE_TILT[0] / 0.03),
                    _math(nt, "MULTIPLY", swell, RIPPLE_TILT[1] / 0.03))
    return _math(nt, "ADD", surface, _math(nt, "MULTIPLY", rings, RING_TILT / 0.03))


def _strands(nt, pos, per_m, length_m, width_m, keep):
    """Loose straw: a stalk of random angle in a share of the Voronoi cells, 1 on the stalk and 0 off it."""
    cell = _node(nt, "ShaderNodeTexVoronoi", {"Vector": pos, "Scale": per_m, "Randomness": 1.0},
                 voronoi_dimensions="2D", feature="F1")
    rnd = _node(nt, "ShaderNodeSeparateColor", {"Color": cell.outputs["Color"]})
    angle = _math(nt, "MULTIPLY", rnd.outputs["Green"], math.pi)
    ca, sa = _math(nt, "COSINE", angle), _math(nt, "SINE", angle)
    scaled = _node(nt, "ShaderNodeVectorMath", {0: pos, 3: per_m}, operation="SCALE").outputs[0]
    lx, ly, _ = _xyz(nt, _vec(nt, "SUBTRACT", scaled, cell.outputs["Position"]))
    along = _math(nt, "ADD", _math(nt, "MULTIPLY", lx, ca), _math(nt, "MULTIPLY", ly, sa))
    across = _math(nt, "SUBTRACT", _math(nt, "MULTIPLY", ly, ca), _math(nt, "MULTIPLY", lx, sa))
    half_l, half_w = length_m * per_m * 0.5, width_m * per_m * 0.5
    stalk = _math(nt, "MULTIPLY",
                  _range(nt, _math(nt, "ABSOLUTE", across), half_w, half_w * 0.4, 0.0, 1.0, smooth=True),
                  _range(nt, _math(nt, "ABSOLUTE", along), half_l, half_l * 0.75, 0.0, 1.0, smooth=True))
    return _math(nt, "MULTIPLY", stalk, _range(nt, rnd.outputs["Red"], keep - 0.05, keep, 1.0, 0.0))


def _prints(nt, pos, per_m=3.2):
    """Boot prints in soft mud: an oblong dent in a share of the Voronoi cells, leaning along the way to the gate. 1 inside a dent."""
    cell = _node(nt, "ShaderNodeTexVoronoi", {"Vector": pos, "Scale": per_m, "Randomness": 0.7}, voronoi_dimensions="2D", feature="F1")
    rnd = _node(nt, "ShaderNodeSeparateColor", {"Color": cell.outputs["Color"]})
    scaled = _node(nt, "ShaderNodeVectorMath", {0: pos, 3: per_m}, operation="SCALE").outputs[0]
    lx, ly, _ = _xyz(nt, _vec(nt, "SUBTRACT", scaled, cell.outputs["Position"]))
    angle = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", rnd.outputs["Green"], 0.5), 1.1)
    ca, sa = _math(nt, "COSINE", angle), _math(nt, "SINE", angle)
    along = _math(nt, "ADD", _math(nt, "MULTIPLY", ly, ca), _math(nt, "MULTIPLY", lx, sa))  # length runs along y
    across = _math(nt, "SUBTRACT", _math(nt, "MULTIPLY", lx, ca), _math(nt, "MULTIPLY", ly, sa))
    reach = _math(nt, "ADD", _math(nt, "POWER", _math(nt, "DIVIDE", _math(nt, "ABSOLUTE", across), 0.17 * per_m / 3.2 * 0.5), 2.0),
                  _math(nt, "POWER", _math(nt, "DIVIDE", _math(nt, "ABSOLUTE", along), 0.42 * per_m / 3.2 * 0.5), 2.0))
    dent = _range(nt, reach, 1.0, 0.45, 0.0, 1.0, smooth=True)
    return _math(nt, "MULTIPLY", dent, _range(nt, rnd.outputs["Red"], 0.62, 0.55, 1.0, 0.0))


# ---------------------------------------------------------------- material
def build(mat, nt, bsdf):
    plan = _plan()
    img_a, img_b, img_c, img_d = ground_images(plan)
    pos = _node(nt, "ShaderNodeTexCoord").outputs["Object"]
    x, y, _ = _xyz(nt, pos)

    # ---- the baked ground history
    sx, sy = MAP_W / PPM, MAP_H / PPM
    uv = _node(nt, "ShaderNodeCombineXYZ", {"X": _math(nt, "MULTIPLY_ADD", x, 1.0 / sx, -MAP_X0 / sx),
                                            "Y": _math(nt, "MULTIPLY_ADD", y, 1.0 / sy, -MAP_Y0 / sy)}).outputs[0]
    tex = []
    for img in (img_a, img_b, img_c, img_d):
        t = _node(nt, "ShaderNodeTexImage", {"Vector": uv}, interpolation="Linear", extension="EXTEND")
        t.image = img
        tex.append(t)
    sep_a, sep_b, sep_c, sep_d = (_node(nt, "ShaderNodeSeparateColor", {"Color": t.outputs["Color"]}) for t in tex)
    water_m = _math(nt, "MULTIPLY_ADD", sep_a.outputs["Red"], DEPTH_MAX - DEPTH_MIN, DEPTH_MIN)
    traffic, ruts, earth_map = sep_a.outputs["Green"], sep_a.outputs["Blue"], tex[0].outputs["Alpha"]
    traffic = _range(nt, traffic, WORN_FROM, WORN_FULL, smooth=True)  # a path has a body and an edge
    dry, straw_density, silt, hooves = sep_b.outputs["Red"], sep_b.outputs["Green"], sep_b.outputs["Blue"], tex[1].outputs["Alpha"]
    track_map, dung_zone, grate_silt, lane = sep_c.outputs["Red"], sep_c.outputs["Green"], sep_c.outputs["Blue"], tex[2].outputs["Alpha"]

    mud_map, sunk, trail, moss = sep_d.outputs["Red"], sep_d.outputs["Green"], sep_d.outputs["Blue"], tex[3].outputs["Alpha"]

    paving = _paving(nt, pos, lane, sunk)
    edge, stone_value = paving["edge"], paving["value"]
    crown_mask = _range(nt, edge, 0.004, SHOULDER, smooth=True)  # 1 on a sett's crown, 0 in the joint

    # ---- stone height, and from it where stones stand out of shallow water
    hammered = _math(nt, "ADD", _math(nt, "MULTIPLY", _noise(nt, pos, 18.0, 2.0, "2D"), 0.10),
                     _math(nt, "MULTIPLY", _noise(nt, pos, 55.0, 2.0, "2D"), 0.06))  # tool marks and wear on the tops
    grit_h = _math(nt, "ADD", _math(nt, "MULTIPLY", _noise(nt, pos, 150.0, 2.0, "2D"), 0.07), _math(nt, "MULTIPLY", _noise(nt, pos, 60.0, 2.0, "2D"), 0.07))
    stone_height = _math(nt, "ADD", paving["height"], _math(nt, "MULTIPLY", _math(nt, "ADD", hammered, grit_h), crown_mask))

    # ---- earth: patches from the map and single lost setts, both with ragged edges
    ragged = _noise(nt, pos, 12.0, 3.0, "2D")
    missing_at = _math(nt, "SUBTRACT", 1.0 - MISSING_SETTS, _math(nt, "MULTIPLY", traffic, MISSING_EXTRA))
    lost = _range(nt, paving["lost"], missing_at, _math(nt, "ADD", missing_at, 0.012))
    earth = _math(nt, "MAXIMUM", lost,
                  _range(nt, _math(nt, "ADD", earth_map, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", ragged, 0.5), 0.55)),
                         0.42, 0.55, smooth=True))

    # ---- tracked mud: thick near the gate, thinning along the roads, with ragged edges and bare stone showing through
    streaks = _noise(nt, _node(nt, "ShaderNodeCombineXYZ", {"X": x, "Y": _math(nt, "MULTIPLY", y, 0.12)}).outputs[0], 9.0, 3.0, "2D")  # long streaks along the way from the gate
    track_raw = _math(nt, "ADD", _math(nt, "MULTIPLY", track_map, 1.25),
                      _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", streaks, 0.5), 0.5))
    track_raw = _math(nt, "ADD", track_raw,
                      _math(nt, "ADD", _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, pos, 4.2, 3.0, "2D"), 0.5), 0.6),
                            _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, pos, 24.0, 3.0, "2D"), 0.5), 0.30)))
    prints = _math(nt, "MULTIPLY", _prints(nt, pos), _range(nt, track_raw, 0.45, 0.7))  # boot prints where the mud is thick
    track_cov = _range(nt, track_raw, 0.26, 0.50, smooth=True)  # mud lies over the stones
    track_film = _range(nt, track_raw, 0.04, 0.32, smooth=True)  # a smear of mud darkens the stones around it

    # ---- macro mud: the baked field cut by noise and by a threshold of each sett's own, so setts sink in turn
    sett_bias = _math(nt, "SUBTRACT", paving["lost"], 0.5)
    macro_raw = _math(nt, "ADD", mud_map, _math(nt, "ADD", _math(nt, "MULTIPLY", sett_bias, MUD_SETT_BIAS),
                      _math(nt, "ADD", _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, pos, 3.4, 3.0, "2D"), 0.5), 0.5),
                            _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, pos, 21.0, 3.0, "2D"), 0.5), 0.22))))
    macro_cov = _range(nt, macro_raw, MUD_EDGE[0], MUD_EDGE[1], smooth=True)
    macro_film = _range(nt, macro_raw, MUD_EDGE[0] - 0.34, MUD_EDGE[1] - 0.05, smooth=True)
    track_cov = _math(nt, "MAXIMUM", track_cov, macro_cov)
    track_film = _math(nt, "MAXIMUM", track_film, macro_film)
    prints = _math(nt, "MAXIMUM", prints, _math(nt, "MULTIPLY", _prints(nt, pos), _range(nt, macro_raw, 0.62, 0.85)))

    # ---- silt: the fan the drain water drops around the grate
    silt_raw = _math(nt, "ADD", grate_silt, _math(nt, "ADD", _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, pos, 7.0, 3.0, "2D"), 0.5), 0.55),
                                                  _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, pos, 38.0, 3.0, "2D"), 0.5), 0.2)))
    silt_fan = _range(nt, silt_raw, 0.30, 0.52, smooth=True)

    # ---- water depth at this sett: the map's level minus the crown that stands above it
    micro = _math(nt, "MULTIPLY", stone_height, SETT_CROWN_M)
    micro = _math(nt, "MULTIPLY", micro, _math(nt, "SUBTRACT", 1.0, _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", earth, 0.8), _math(nt, "MULTIPLY", track_cov, 0.7))))
    micro = _math(nt, "ADD", micro, _math(nt, "MULTIPLY", silt_fan, 0.013))  # banked silt stands out of the water
    micro = _math(nt, "ADD", micro, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", stone_value, 0.5), _math(nt, "MULTIPLY", SETT_JITTER_M, _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", track_cov, 0.8)))))  # each sett stands a little higher or lower, so a pool's rim follows the stones
    depth = _math(nt, "ADD", _math(nt, "SUBTRACT", water_m, micro),
                  _math(nt, "ADD", _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, pos, 40.0, 2.0, "2D"), 0.5), 0.005),
                       _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, pos, 9.0, 2.0, "2D"), 0.5), 0.006)))
    puddle = _range(nt, depth, 0.0002, 0.0035, smooth=True)  # 1 under water
    deep = _range(nt, depth, 0.008, 0.06, smooth=True)  # water gets black as it gets deep
    fringe = _math(nt, "MULTIPLY", _range(nt, depth, -0.018, 0.0, smooth=True), _math(nt, "SUBTRACT", 1.0, puddle))
    soak = _range(nt, depth, -0.06, -0.004, smooth=True)  # wet ground around water

    # ---- where it is muddy: joints, trodden paths, silt near water and walls, wet rims
    wet_spots = _noise(nt, pos, 0.9, 4.0, "2D", distortion=0.2)
    smear = _range(nt, _noise(nt, pos, 3.5, 3.0, "2D"), 0.3, 0.7, smooth=True)
    trodden = _math(nt, "MULTIPLY", traffic, _math(nt, "MULTIPLY_ADD", _range(nt, wet_spots, 0.3, 0.55), 0.3, 0.7))
    joint_full = _math(nt, "ADD", _math(nt, "MULTIPLY", sunk, 0.007), _math(nt, "ADD", 0.008, _math(nt, "ADD", _math(nt, "MULTIPLY", traffic, 0.005),
                                              _math(nt, "ADD", _math(nt, "MULTIPLY", silt, 0.004), _math(nt, "MULTIPLY", lane, 0.005)))))
    joint = _range(nt, edge, 0.0, joint_full, 1.0, 0.0, smooth=True)  # mud in the joint, 1 at the outline of a sett
    mud = _math(nt, "MULTIPLY", trodden, _math(nt, "MULTIPLY_ADD", smear, 0.25, 0.75))
    silt_cover = _math(nt, "MULTIPLY", silt, _range(nt, _noise(nt, pos, 22.0, 3.0, "2D"), 0.25, 0.5, 0.7, 1.0))
    mud = _math(nt, "MAXIMUM", mud, _math(nt, "MAXIMUM", silt_cover, _math(nt, "MULTIPLY", fringe, 0.9)))
    mud = _math(nt, "MAXIMUM", mud, _math(nt, "MULTIPLY", ruts, 0.9))
    lane_mud = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", lane, 0.7), _range(nt, _noise(nt, pos, 2.2, 3.0, "2D"), 0.35, 0.7, 0.45, 1.0))
    mud = _math(nt, "MAXIMUM", mud, lane_mud)

    # ---- dung: a share of the cells of a coarse Voronoi hold a pile, more where animals stand
    cell = _node(nt, "ShaderNodeTexVoronoi", {"Vector": pos, "Scale": 1.5, "Randomness": 0.6}, voronoi_dimensions="2D", feature="F1")
    cell_rnd = _node(nt, "ShaderNodeSeparateColor", {"Color": cell.outputs["Color"]})
    chance = _math(nt, "MULTIPLY", dung_zone, 0.95)
    present = _range(nt, cell_rnd.outputs["Red"], _math(nt, "SUBTRACT", chance, 0.04), chance, 1.0, 0.0)
    size = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY_ADD", cell_rnd.outputs["Green"], 0.08, 0.115),
                 _range(nt, _noise(nt, pos, 20.0, 2.0, "2D"), 0.3, 0.7, 0.7, 1.3))  # meters; no two piles alike
    dist_m = _math(nt, "DIVIDE", cell.outputs["Distance"], 1.5)
    pile = _math(nt, "MULTIPLY", present, _range(nt, dist_m, size, _math(nt, "MULTIPLY", size, 0.45), 0.0, 1.0, smooth=True))
    dung_smear = _math(nt, "MULTIPLY", present, _range(nt, dist_m, _math(nt, "MULTIPLY", size, 2.4), size, 0.0, 1.0, smooth=True))

    # ---- color ----
    ramp = _node(nt, "ShaderNodeValToRGB", {"Fac": stone_value})
    ramp.color_ramp.elements[0].position = STONE_COLORS[0][0]
    ramp.color_ramp.elements[0].color = (*STONE_COLORS[0][1], 1)
    ramp.color_ramp.elements[1].position = STONE_COLORS[-1][0]
    ramp.color_ramp.elements[1].color = (*STONE_COLORS[-1][1], 1)
    for p, c in STONE_COLORS[1:-1]:
        ramp.color_ramp.elements.new(p).color = (*c, 1)
    grain = _range(nt, _noise(nt, pos, 34.0, 3.0, "2D"), 0.25, 0.75, 0.7, 1.2)
    worn = _range(nt, edge, 0.0, 0.03, 0.74, 1.10, smooth=True)  # crowns are lighter, shoulders darker
    patina = _range(nt, _noise(nt, pos, 0.5, 4.0, "2D", rough=0.55), 0.3, 0.7, PATINA[0], PATINA[1])  # wet and dry washes, a few meters wide
    patina = _math(nt, "MULTIPLY", patina, _range(nt, _noise(nt, pos, 0.17, 3.0, "2D"), 0.3, 0.7, 0.9, 1.1))
    lift = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", _math(nt, "ADD", 1.0, _math(nt, "MULTIPLY", dry, DRY_LIFT)),
                                      _math(nt, "SUBTRACT", 1.0, _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", traffic, WEAR_DARKEN),
                                                                      _math(nt, "MULTIPLY", trail, TRAIL_DARKEN)))),
                _math(nt, "MULTIPLY", patina, _math(nt, "MULTIPLY_ADD", paving["region"], REGION_LIGHT[1] - REGION_LIGHT[0], REGION_LIGHT[0])))
    stone = _mix(nt, 1.0, _mix(nt, 1.0, ramp.outputs["Color"], grain, "MULTIPLY"), worn, "MULTIPLY")
    stone = _mix(nt, _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", traffic, WEAR_FLATTEN), _math(nt, "MULTIPLY", trail, 0.8)), stone, MEAN_STONE)  # worn setts look alike
    stone = _mix(nt, _math(nt, "MULTIPLY", moss, MOSS_TINT_AMOUNT), stone, MOSS_TINT, "MULTIPLY")  # damp green on the stone at the wall feet
    stone = _mix(nt, 1.0, stone, _node(nt, "ShaderNodeCombineColor", {"Red": lift, "Green": lift, "Blue": lift}).outputs["Color"], "MULTIPLY")
    stone = _mix(nt, 1.0, stone, _mix(nt, dry, DAMP_TINT, DRY_TINT), "MULTIPLY")  # rain darkens the stone, more where it is drier
    stone = _mix(nt, _math(nt, "MULTIPLY", track_film, 0.55), stone, _mix(nt, 0.5, TRACK_MUD, MEAN_STONE))  # a film of mud over the tops
    stone = _mix(nt, 1.0, stone, (STONE_GAIN, STONE_GAIN, STONE_GAIN), "MULTIPLY")

    mud_fac = _math(nt, "ADD", _math(nt, "MULTIPLY", _noise(nt, pos, 2.2, 3.0, "2D"), 0.5), _math(nt, "MULTIPLY", _noise(nt, pos, 10.0, 4.0, "2D"), 0.5))
    mud_fac = _range(nt, mud_fac, 0.25, 0.75)  # more contrast: pale dried crust, dark wet mud
    mud_tone = _node(nt, "ShaderNodeValToRGB", {"Fac": mud_fac})
    mud_tone.color_ramp.elements[0].color = (*MUD_DARK, 1)
    mud_tone.color_ramp.elements[1].color = (*MUD_LIGHT, 1)
    silt_tone = _mix(nt, _math(nt, "MULTIPLY", silt, 0.45), mud_tone.outputs["Color"], (0.7, 0.68, 0.64), "MULTIPLY")  # silt is the darkest mud
    grit = _range(nt, _noise(nt, pos, 110.0, 2.0, "2D"), 0.42, 0.62, 0.7, 1.6)  # sand and grit in the mud
    grit_rgb = _node(nt, "ShaderNodeCombineColor", {"Red": grit, "Green": grit, "Blue": grit}).outputs["Color"]
    joint_color = _mix(nt, 1.0, _mix(nt, 0.3, JOINT_MUD, mud_tone.outputs["Color"]), grit_rgb, "MULTIPLY")
    earth_tone = _node(nt, "ShaderNodeValToRGB", {"Fac": _noise(nt, pos, 20.0, 4.0, "2D", rough=0.6)})
    earth_tone.color_ramp.elements[0].color = (*EARTH_DARK, 1)
    earth_tone.color_ramp.elements[1].color = (*EARTH_LIGHT, 1)
    pebbles = _range(nt, _noise(nt, pos, 90.0, 2.0, "2D"), 0.5, 0.65, 0.75, 1.7)  # grit in the packed earth
    earth_color = _mix(nt, 1.0, earth_tone.outputs["Color"], _node(nt, "ShaderNodeCombineColor", {"Red": pebbles, "Green": pebbles, "Blue": pebbles}).outputs["Color"], "MULTIPLY")
    track_color = _mix(nt, 1.0, _mix(nt, _range(nt, _noise(nt, pos, 6.0, 3.0, "2D"), 0.3, 0.7), TRACK_MUD, mud_tone.outputs["Color"]), grit_rgb, "MULTIPLY")
    wet_patch = _range(nt, _noise(nt, pos, 1.4, 3.0, "2D"), 0.44, 0.66, smooth=True)  # stretches of mud that lie wetter and darker than the rest
    track_color = _mix(nt, _math(nt, "MULTIPLY", wet_patch, 0.5), track_color, (0.5, 0.48, 0.44), "MULTIPLY")
    color = _mix(nt, joint, stone, joint_color)
    color = _mix(nt, mud, color, silt_tone)
    color = _mix(nt, earth, color, earth_color)
    color = _mix(nt, track_cov, color, track_color)
    color = _mix(nt, _math(nt, "MULTIPLY", prints, 0.6), color, _mix(nt, 1.0, color, (0.45, 0.43, 0.40), "MULTIPLY"))  # a print holds water: darker

    straw = _math(nt, "MAXIMUM", _strands(nt, pos, 3.6, 0.34, 0.019, 0.7),
                  _strands(nt, _vec(nt, "ADD", pos, (3.7, 1.3, 0.0)), 5.5, 0.22, 0.013, 0.6))
    straw_density = _math(nt, "MAXIMUM", straw_density, _math(nt, "MULTIPLY", track_cov, 0.22))  # a little straw lies in every patch of mud
    straw = _math(nt, "MULTIPLY", straw, _range(nt, straw_density, 0.06, 0.45, smooth=True))
    matted = _math(nt, "MULTIPLY", straw_density, _range(nt, _noise(nt, pos, 3.0, 3.0, "2D"), 0.35, 0.65, 0.15, 0.5, smooth=True))
    color = _mix(nt, matted, color, _mix(nt, 0.5, STRAW_COLOR, mud_tone.outputs["Color"]))  # straw trodden into the mud
    straw_color = _mix(nt, _range(nt, _noise(nt, pos, 8.0, 2.0, "2D"), 0.35, 0.65), STRAW_COLOR, STRAW_WET)  # some stalks soaked dark
    color = _mix(nt, _math(nt, "MULTIPLY", straw, 0.9), color, straw_color)
    dung_color = _mix(nt, _range(nt, _noise(nt, pos, 60.0, 3.0, "2D"), 0.5, 0.75, 0.0, 0.5), DUNG_COLOR, STRAW_WET)  # fibers of undigested hay
    color = _mix(nt, _math(nt, "MULTIPLY", dung_smear, 0.55), color, _mix(nt, 0.6, DUNG_COLOR, mud_tone.outputs["Color"]))
    color = _mix(nt, pile, color, dung_color)
    sand = _range(nt, _noise(nt, pos, 150.0, 1.0, "2D"), 0.60, 0.68, 0.0, 1.0)
    silt_color = _mix(nt, _math(nt, "MULTIPLY", sand, 0.35), SILT_COLOR, (0.13, 0.115, 0.09))  # silt with specks of sand
    color = _mix(nt, silt_fan, color, silt_color)
    color = _mix(nt, _math(nt, "MULTIPLY", soak, 0.25), color, (0.72, 0.70, 0.66), "MULTIPLY")  # the ground around a puddle is wetter
    color = _mix(nt, 1.0, color, (FLOOR_GAIN, FLOOR_GAIN, FLOOR_GAIN), "MULTIPLY")
    shallow = _mix(nt, 1.0, color, WATER_SHALLOW, "MULTIPLY")
    turbid = _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", traffic, 0.85), _math(nt, "MAXIMUM", ruts, _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", silt, 0.6), _math(nt, "MULTIPLY", track_cov, 0.7))))
    water_base = _mix(nt, turbid, WATER_BASE, TURBID_WATER)
    water_color = _mix(nt, deep, shallow, water_base)
    color = _mix(nt, puddle, color, water_color)
    nt.links.new(color, bsdf.inputs["Base Color"])

    # ---- roughness and specular: damp tops of varied gloss, wet joints, mud, dung, silt, mirror water ----
    top_rough = _math(nt, "MULTIPLY_ADD", paving["gloss"], ROUGH_TOP[1] - ROUGH_TOP[0], ROUGH_TOP[0])
    top_rough = _math(nt, "ADD", top_rough, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, pos, 26.0, 2.0, "2D"), 0.5), 0.12))
    top_rough = _math(nt, "ADD", top_rough, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", paving["region"], 0.5), 0.18))  # some regions shine, others are matte
    rough_stone = _range(nt, crown_mask, 0.0, 1.0, ROUGH_SHOULDER, top_rough)
    rough = _range(nt, dry, 0.0, 1.0, rough_stone, ROUGH_DRY)
    rough = _range(nt, track_film, 0.0, 1.0, rough, 0.30)  # mud film on the tops makes them wetter
    rough = _range(nt, joint, 0.0, 1.0, rough, _math(nt, "ADD", ROUGH_JOINT, _math(nt, "ADD", _math(nt, "MULTIPLY", dry, 0.28), _math(nt, "MULTIPLY", sunk, 0.38))))
    rough = _range(nt, mud, 0.0, 1.0, rough, ROUGH_MUD)
    rough = _range(nt, earth, 0.0, 1.0, rough, ROUGH_EARTH)
    mud_rough = _range(nt, _noise(nt, pos, 5.0, 3.0, "2D"), 0.35, 0.65, ROUGH_MUD - 0.10, ROUGH_MUD + 0.24)  # wet in places, drying in others
    mud_rough = _math(nt, "SUBTRACT", mud_rough, _math(nt, "MULTIPLY", wet_patch, 0.30))
    rough = _range(nt, track_cov, 0.0, 1.0, rough, mud_rough)
    rough = _range(nt, prints, 0.0, 1.0, rough, 0.10)
    rough = _range(nt, _math(nt, "MULTIPLY", straw, 0.7), 0.0, 1.0, rough, 0.85)
    rough = _range(nt, pile, 0.0, 1.0, rough, ROUGH_DUNG)
    rough = _range(nt, silt_fan, 0.0, 1.0, rough, ROUGH_SILT)
    rough = _range(nt, fringe, 0.0, 1.0, rough, ROUGH_FRINGE)
    rough = _range(nt, puddle, 0.0, 1.0, rough, ROUGH_WATER)
    nt.links.new(rough, bsdf.inputs["Roughness"])
    spec = _range(nt, _math(nt, "MAXIMUM", dry, 0.0), 0.0, 1.0, DAMP_SPECULAR, 0.5)
    spec = _range(nt, track_cov, 0.0, 1.0, spec, MUD_SPECULAR)  # matte mud takes less sky than stone
    spec = _range(nt, puddle, 0.0, 1.0, spec, PUDDLE_SPECULAR)
    nt.links.new(spec, bsdf.inputs["Specular IOR Level"])

    # ---- relief: worn paths are smoother, ruts and earth lie lower, mud buries the stones, water is flat and rippled ----
    smooth_stone = _math(nt, "MULTIPLY", stone_height, _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", traffic, 0.75)))
    earth_height = _math(nt, "MULTIPLY_ADD", _noise(nt, pos, 45.0, 2.0, "2D"), 0.12, 0.28)
    height = _math(nt, "ADD", _math(nt, "MULTIPLY", smooth_stone, _math(nt, "SUBTRACT", 1.0, earth)),
                   _math(nt, "MULTIPLY", earth_height, earth))
    height = _math(nt, "SUBTRACT", height, _math(nt, "MULTIPLY", ruts, 1.2))
    height = _math(nt, "SUBTRACT", height, _math(nt, "MULTIPLY", hooves, 1.2))
    height = _math(nt, "SUBTRACT", height, _math(nt, "MULTIPLY", traffic, 0.35))
    mud_height = _math(nt, "ADD", _math(nt, "MULTIPLY_ADD", _noise(nt, pos, 30.0, 3.0, "2D"), 0.35, 0.12),
                       _math(nt, "ADD", _math(nt, "MULTIPLY", _noise(nt, pos, 9.0, 3.0, "2D"), 1.0),
                             _math(nt, "MULTIPLY", _noise(nt, pos, 3.5, 3.0, "2D"), 1.2)))  # clods and ridges of mud
    mud_height = _math(nt, "SUBTRACT", mud_height, _math(nt, "MULTIPLY", prints, 1.6))
    height = _mix_float(nt, _math(nt, "MULTIPLY", track_cov, 0.85), height, mud_height)
    height = _mix_float(nt, _math(nt, "MULTIPLY", silt_fan, 0.9), height, _math(nt, "MULTIPLY_ADD", _noise(nt, pos, 60.0, 2.0, "2D"), 0.05, 0.1))
    lumps = _math(nt, "MULTIPLY_ADD", _noise(nt, pos, 45.0, 3.0, "2D"), 1.0, 2.2)  # a pile stands 2 to 3 cm proud of the stones
    height = _math(nt, "ADD", height, _math(nt, "MULTIPLY", pile, lumps))
    height = _math(nt, "ADD", height, _math(nt, "MULTIPLY", straw, 0.12))
    stone_normal = _node(nt, "ShaderNodeBump", {"Height": height, "Distance": STONE_RELIEF, "Strength": 1.0}).outputs["Normal"]
    water_normal = _node(nt, "ShaderNodeBump", {"Height": water_ripples(nt, pos), "Distance": 0.03,
                                                 "Strength": 1.0}).outputs["Normal"]
    normal = _mix_vec(nt, _range(nt, puddle, 0.2, 0.8, smooth=True), stone_normal, water_normal)
    normal = _vec(nt, "NORMALIZE", normal)
    nt.links.new(normal, bsdf.inputs["Normal"])

    # ---- the water film is a second glossy layer over the dark silt, which doubles the sheen of the sky ----
    nt.links.new(_math(nt, "MULTIPLY", puddle, WATER_COAT), bsdf.inputs["Coat Weight"])
    bsdf.inputs["Coat Roughness"].default_value = ROUGH_WATER
    bsdf.inputs["Coat IOR"].default_value = COAT_IOR
    nt.links.new(normal, bsdf.inputs["Coat Normal"])

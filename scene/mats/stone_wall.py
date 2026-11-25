"""Wet garrison masonry: nearly flush coursed rubble on walls, wet flagstones on tops.

Texture coordinates come from the object-space face normal. A wall face uses the position along
the wall and the world height, so the courses of a merlon continue those of the parapet and the
wall below it. A horizontal face uses the position along the box axes in the world frame, so the
paving follows a rotated wall and runs on across neighbouring boxes with the same orientation.
Object coordinates are meters because kit.py keeps object scale at 1.

A material copy with the `dressed` value node set to 1 shows single chiseled stones
instead of the course pattern (used by the gate arch and the door cases).

Layers, bottom to top:
  1. course pattern: level beds 19-36 cm high, blocks 22-100 cm long (mostly 30-60). Faces are
     almost flat, joints are 1-2 cm wide and filled flush with lime pointing close in value to the
     stone. Only some stretches have eroded: wider, recessed and dark. Arrises are slightly worn
     and chipped in places, never a uniform bright rim.
  2. flagstones on horizontal faces: rectangular slabs in rows 55-85 cm wide and 55-115 cm long
     with narrow dirt joints, some slabs dished so they hold water; merlon and cap tops are
     single stones
  3. repair patches: rectangles of other stone with their own coursing and a fresh mortar outline
  4. stone color: per-stone variation is small; metre-scale zones carry the value changes
     (dark and light areas, cool and warm areas, leeward faces drier, patches)
  5. damage: a few fallen stones, broken faces, cracks; putlog holes in scaffold rows
  6. water: streaks only where a cause exists: crenel gaps (clustered, uneven in length and
     width, a few long ones from spouts), arrow slits, window sills, door cases. A streak is the
     same stone, damp and somewhat darker, with soft edges, green algae and pale lime strands
     in it, never a black stripe; a damp band under the wall top; soot above torches, lanterns,
     windows and the chimney
  7. foot of the wall: contact soil, splash, rising damp, mud spatter, green-black algae, moss
  8. wetness: every face is darker and glossier where rain reaches it; tops are darkest

Object extents are read from the Generated coordinates. A centered box has half its height
at z / (2 gz - 1), so the distance below its own top edge needs no plan data.
Merlons, parapets and caps are small boxes. They are darker than the wall below them.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _scan  # noqa: E402
import location  # noqa: E402

PERIOD = 1.4  # height in m of one set of courses
COURSES = 5  # courses per period: 28 cm on average
COURSE_VAR = 0.9  # a course weighs 1 + COURSE_VAR x random, so heights run about 19-36 cm
BLOCK_LEN = (0.22, 1.05)  # nominal block length per course in m
BLOCK_LEN_POWER = 1.5  # bends the length distribution toward the short end
SPLIT = 0.26  # share of blocks longer than SPLIT_MIN that are cut in two by a vertical joint
SPLIT_MIN = 0.50
JITTER = 0.42  # how far vertical joints wander from the nominal spacing, as a share of the length
JOINT_HALF = (0.0055, 0.0105)  # half width of a joint in m: 1.1 to 2.1 cm wide
JOINT_SOFT = 0.0025  # soft edge of the joint in m
ERODE_RANGE = (0.55, 0.68)  # noise range where pointing has washed out: about a sixth of the joints
ERODE_HALF = 0.011  # an eroded stretch is this much wider on each side, in m
ARRIS = 0.035  # width of the worn arris along a joint in m
FACE_ROUND = 0.14  # distance from a joint over which the face rises to full height in m
CAVITY = 0.05  # distance from a joint over which a stone shades up from its recessed edge in m
CAVITY_DARK = 0.09  # how much darker the stone is right at the joint
EDGE_WOBBLE = (0.040, 0.010)  # high-frequency edge wobble (along, up) in m
EDGE_WARP = (0.060, 0.025)  # low-frequency warp (along, up) in m: stones are not rectangles
SLAB_PERIOD = 2.1  # height in m of one set of slab rows
SLAB_ROWS = 3  # rows per period: 0.55-0.85 m
SLAB_ROW_VAR = 0.55  # a row weighs 1 + SLAB_ROW_VAR x random
SLAB_LEN = (0.55, 1.15)  # slab length per row in m
SLAB_JITTER = 0.30  # how far the joints between slabs wander from the nominal spacing, as a share of the length
SLAB_JOINT = (0.008, 0.018)  # half width of a dirt joint between slabs in m
CAP_SCALE = 0.35  # small tops (merlons, caps) are one stone: the pattern is this much larger
QUOIN_ZONE = (1.1, 0.5)  # distance from a tower corner where long-and-short quoin work starts and is full
QUOIN_LEN = (0.46, 0.98)  # quoin stone lengths in m: short header, long stretcher
PLINTH_LEN = 1.45  # the plinth course has longer stones
PLINTH_OUT_Z = (-1.6, -0.9)  # outer faces: plinth below this world z
PLINTH_IN_Z = (0.6, 1.1)  # courtyard faces: plinth below this world z
COURTYARD = (-1.5, -3.5)  # x, y of the courtyard center: faces turned toward it are courtyard faces
YARD_Z, WARD_Z = 0.0, -3.0  # ground level of courtyard faces and of outer faces
RAIN_FROM = (-0.92, -0.38)  # horizontal direction the rain comes from (layout.json rain wind is +x, +y)
MOON_FROM = (-0.93, 0.16)  # horizontal direction toward the moon (layout.json moon direction)

CRENEL_STEP = 1.3  # merlon width + gap in plan.json: crenel gaps repeat at this pitch
PARAPET = 1.0  # parapet height: a gap track starts this far above the wall top
TRACK_SHARE = 0.46  # share of crenel gaps that carry a track (clustered along the wall)
TRACK_LEN = (0.9, 6.2)  # shortest and longest ordinary track in m
TRACK_LEN_POWER = 2.0  # bends track lengths toward the short end
SPOUT_SHARE = 0.10  # share of crenel gaps that are a spout: one long, dark, wide track
SPOUT_LEN = (5.0, 9.0)  # spout track length in m
RUN_COLUMNS = 2.2  # fine wet runs per meter along the wall
RUN_LENGTH = (0.5, 2.4)  # shortest and longest fine run in m

# Repairs, few and deliberate, each on one wall face. `from` and `to` are world (x, y) points on the
# face, walked with the wall body on the left; `z` is the world height range (for `blocked`, the
# bottom and the crown of the arch). `stone` picks from PATCH_STONES, `size` from PATCH_SCALE.
REPAIRS = [
    # gatehouse, courtyard face: a stretch above the arch relaid in squared brown-grey stone
    {"kind": "rebuild", "from": (-0.3, 3.0), "to": (1.9, 3.0), "z": (5.5, 6.85), "stone": 0.45, "size": 0.3},
    # east curtain, courtyard face: an old postern blocked up with small sandstone rubble
    {"kind": "blocked", "from": (8.22, -0.85), "to": (9.03, -1.73), "z": (0.0, 2.25), "stone": 0.0, "size": 1.0},
    # east curtain, courtyard face: the wall head rebuilt under the parapet in dark blue-grey stone
    {"kind": "rebuild", "from": (5.93, 1.66), "to": (7.01, 0.48), "z": (4.6, 6.0), "stone": 0.3, "size": 0.3},
    # south-east curtain, outer face: a stretch repointed in a pale, hard mortar
    {"kind": "repoint", "from": (9.01, -11.31), "to": (11.39, -10.26), "z": (3.6, 5.6)},
    # north-east tower, courtyard face: single stones replaced in buff sandstone
    {"kind": "odd", "from": (5.1, 2.6), "to": (6.9, 2.6), "z": (1.4, 3.8)},
]
NORTH_GROWTH = 0.8  # extra algae and moss on north-facing faces, as a share
SOUTH_LESS = 0.6  # less algae and moss on south-facing faces, as a share
STAIR_LINE = 0.12  # local y of the walking line on the wall stair: a little toward the wall, away from the drop
STAIR_POLISH = (1.55, 1.52, 1.45)  # worn tread stone is clean and paler than the dirty wet flags round it
JAMB = 0.20  # width of the dressed surround that stays round a blocked opening, in m
ODD_SHARE = 0.35  # share of the stones in an `odd` patch that were replaced
ODD_STONE = (0.150, 0.128, 0.092)  # buff sandstone
REPOINT = (0.230, 0.226, 0.210)  # hard pale mortar, smeared over the stone edges
PATCH_SCALE = (0.80, 1.40)  # block size inside a patch relative to the wall: large squared to small neat
PUTLOG_PITCH = (1.5, 1.2)  # putlog holes: along the wall and between scaffold lifts, in m
PUTLOG_FIRST = 1.1  # height above the ground where the first lift starts
PUTLOG_HOLE = (0.078, 0.075)  # half width and half height of a hole: about 15 cm square
PUTLOG_ROWS = 0.75  # share of scaffold lifts that left holes
PUTLOG_OPEN = 0.50  # share of holes in such a lift that were never filled in
DAMP_BAND = (0.78, 0.40)  # ragged damp band: mean top height above the ground and its swing in m
CORNER_CHIP = 0.10  # share of stones that lost a corner

ALBEDO = (1.24, 1.15, 1.21)  # overall value of the masonry: sets how bright walls read in the blue-hour light
# Colors are linear, before ALBEDO.
STONE_FAMILIES = [  # ramp over the per-stone random value: close to one another
    (0.00, (0.098, 0.101, 0.108)),  # cool grey
    (0.17, (0.108, 0.104, 0.097)),  # warm grey
    (0.34, (0.094, 0.101, 0.092)),  # olive grey
    (0.50, (0.104, 0.098, 0.091)),  # brown grey
    (0.67, (0.092, 0.096, 0.104)),  # slate
    (0.84, (0.114, 0.109, 0.100)),  # pale sand
    (1.00, (0.100, 0.099, 0.097)),  # neutral
]
PATCH_STONES = [  # one stone per repair patch, chosen by its random pick
    (0.00, (0.150, 0.135, 0.100)),  # pale sandstone
    (0.25, (0.064, 0.070, 0.086)),  # dark blue-grey
    (0.50, (0.108, 0.086, 0.068)),  # rust brown
    (0.75, (0.140, 0.142, 0.138)),  # light limestone
]
STONE_GAIN = (0.91, 1.09)  # per-stone value multiplier: lowest, highest (the mean of two randoms)
OUTLIER = 0.025  # share of stones that are darker, and the same share paler
OUTLIER_GAIN = 0.10  # how far an outlier is off
PATCH_GAIN = (0.95, 1.05)  # stones inside a patch stay close to each other
MOTTLE = (0.94, 1.06)  # soft variation inside a stone
GRAIN = (0.95, 1.05)  # fine pits and pale grains
ZONE_BIG = (0.58, 1.42)  # areas of several metres that are darker or lighter
ZONE_MID = (0.85, 1.15)  # areas of one to two metres
HUE_COOL = (0.93, 0.99, 1.08)  # whole areas lean cool or warm
HUE_WARM = (1.08, 1.0, 0.92)
LOWER_DARK = 0.72  # value of the wall between the splash band and about 3 m up, against the wall above
LEEWARD_LIGHT = 1.10  # faces turned away from the rain are drier and lighter
REPLACED = 0.02  # share of stones that are newer and paler
REPLACED_GAIN = (1.12, 1.10, 1.05)
RUST = (1.12, 0.95, 0.80)  # iron-stained stones
RUST_SHARE = 0.03
DRESSED_GAIN = 1.08  # dressed stone (arch, jambs) is paler than the rubble around it
COOL = (1.09, 1.0, 0.89)
LIME = (0.108, 0.108, 0.102)  # wet lime pointing, close in value to the stone
LIME_NEW = (0.120, 0.119, 0.112)  # pointing of a repair patch
MORTAR = (0.066, 0.068, 0.066)  # eroded joint: darker and recessed
MUD = (0.050, 0.046, 0.039)  # dirt between flagstones, before the top is darkened
CHIP = (0.125, 0.122, 0.116)  # fresh broken stone along chipped edges
HOLE = (0.012, 0.011, 0.010)  # inside of a putlog hole
HOLE_SILL = (0.050, 0.046, 0.040)  # the bottom of the hole catches some sky

TOP_TINT = (0.36, 0.38, 0.42)  # wet horizontal stone is darker than the wall face
TOP_GRIME = (0.62, 0.62, 0.60)  # grime and grit in patches on the tops
LICHEN_BLACK = (0.018, 0.019, 0.016)  # crusts of black lichen on exposed tops
SMALL_TINT = (0.88, 0.89, 0.92)  # merlons, parapets and caps are wetter than the wall below
WET_TINT = (0.66, 0.69, 0.75)  # multiplier on fully wet vertical stone
TRACK_TINT = (0.70, 0.71, 0.72)  # under crenel tracks and runs: the same stone, damp and a little darker
TRACK_LIME = (1.22, 1.21, 1.15)  # pale lime washed out of the pointing, in fine strands inside a track
DRY_TINT = (1.12, 1.11, 1.08)  # sheltered stone under ledges and sills
SPOUT_LIME = (1.30, 1.28, 1.20)  # lime deposit where a spout runs
SPLASH_TINT = (0.27, 0.29, 0.31)  # foot of the wall, in the splash zone
DAMP_TINT = (0.56, 0.60, 0.61)  # rising damp above the splash band
BAND_TINT = (0.44, 0.47, 0.47)  # the damp band
SOIL = (0.030, 0.026, 0.020)  # dirt packed into the corner where the wall meets the ground
MUD_SPLASH = (0.074, 0.056, 0.038)  # mud thrown up by rain and boots
FOOT_TINT = (0.50, 0.64, 0.46)  # green-black algae on the lowest stones
ALGAE_TINT = (0.66, 0.88, 0.60)  # green wash on shaded wall areas
ALGAE_BLACK = (0.024, 0.036, 0.020)  # green-black algae in the joints
STAIN_TINT = (0.66, 0.68, 0.72)  # blotches of old grime
SOOT_MAX = 0.74  # darkest a soot fan gets, as a share of the stone color
PLINTH_TINT = (0.58, 0.66, 0.58)  # plinth stones: darker with a green-black damp
MOSS = (0.070, 0.100, 0.040)
MOSS_DRY = (0.095, 0.108, 0.054)
CORE_COLORS = ((0.058, 0.054, 0.048), (0.115, 0.105, 0.092))  # exposed rubble core
MISSING = 0.008  # share of wall stones that have fallen out, leaving a dark hole
BREACH = (0.76, 0.10)  # noise level where a collapsed area starts, and how far single stones push it either way
SPALLED = (0.93, 0.985)  # damage range of stones with a broken face
CRACK_WIDTH = 0.010  # half width of a crack line in noise units
BUMP = 0.02  # relief in m of a height value of 1
ROCK = "rock_05"  # scanned rock (scene/textures): pitting and relief on every stone face
ROCK_TILE = 0.75  # meters of stone face covered by one tile of the scan
ROCK_ALBEDO = 0.55  # how much of the scan's light and dark the stone colour takes (0..1)
ROCK_MEDIAN = 0.153  # median linear luminance of the scan: the neutral value
ROCK_RELIEF = 0.9  # scanned height (0..1) in height units on top of the procedural relief
ROCK_NORMAL = 0.8  # strength of the scanned normal map


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


def _range(nt, value, lo, hi, to_lo=0.0, to_hi=1.0, smooth=False):
    n = _node(nt, "ShaderNodeMapRange",
              {"Value": value, "From Min": lo, "From Max": hi, "To Min": to_lo, "To Max": to_hi},
              interpolation_type="SMOOTHSTEP" if smooth else "LINEAR")
    return n.outputs["Result"]


def _smooth(nt, value, lo, hi, to_lo=0.0, to_hi=1.0):
    return _range(nt, value, lo, hi, to_lo, to_hi, smooth=True)


def _mix(nt, fac, a, b, blend="MIX"):
    n = _node(nt, "ShaderNodeMix", data_type="RGBA", blend_type=blend)
    _link(nt, n.inputs[0], fac)
    _link(nt, n.inputs[6], a)
    _link(nt, n.inputs[7], b)
    return n.outputs[2]


def _lerp(nt, fac, a, b):
    """Float mix: a where fac is 0, b where fac is 1."""
    n = _node(nt, "ShaderNodeMix", data_type="FLOAT")
    _link(nt, n.inputs[0], fac)
    _link(nt, n.inputs[2], a)
    _link(nt, n.inputs[3], b)
    return n.outputs[0]


def _combine(nt, x, y, z=0.0):
    return _node(nt, "ShaderNodeCombineXYZ", {"X": x, "Y": y, "Z": z}).outputs[0]


def _split(nt, vec):
    return _node(nt, "ShaderNodeSeparateXYZ", {"Vector": vec}).outputs


def _dot(nt, a, b):
    return _node(nt, "ShaderNodeVectorMath", {0: a, 1: b}, operation="DOT_PRODUCT").outputs["Value"]


def _noise(nt, vec, scale, detail=2.0, dims="3D", rough=0.5, color=False):
    n = _node(nt, "ShaderNodeTexNoise", {"Scale": scale, "Detail": detail, "Roughness": rough},
              noise_dimensions=dims)
    _link(nt, n.inputs["W" if dims == "1D" else "Vector"], vec)
    return n.outputs["Color" if color else "Fac"]


def _hash(nt, x, y, z=0.0):
    """Random value in 0..1 from three numbers."""
    return _node(nt, "ShaderNodeTexWhiteNoise", {"Vector": _combine(nt, x, y, z)},
                 noise_dimensions="3D").outputs["Value"]


def _scaled(nt, vec, scale, location=(0.0, 0.0, 0.0)):
    """Vector times a per-axis scale, shifted by a location."""
    return _node(nt, "ShaderNodeMapping", {"Vector": vec, "Scale": scale, "Location": location}).outputs[0]


def _max_of(nt, values):
    out = None
    for v in values:
        out = v if out is None else _math(nt, "MAXIMUM", out, v)
    return out if out is not None else 0.0


def _ramp(nt, fac, stops, constant=False):
    """Color ramp through (position, rgb) stops."""
    n = _node(nt, "ShaderNodeValToRGB", {"Fac": fac})
    els = n.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1)
    els[1].position, els[1].color = stops[-1][0], (*stops[-1][1], 1)
    for p, c in stops[1:-1]:
        e = els.new(p)
        e.color = (*c, 1)
    if constant:
        n.color_ramp.interpolation = "CONSTANT"
    return n.outputs["Color"]


def _plan():
    try:
        return location.plan()
    except (OSError, ValueError):
        return {}


def _soot_sources(plan):
    """World points (x, y, z, rise, strength) above which a real flame leaves a soot fan."""
    flames = {"torch_sconce": (0.5, 2.6, 1.0), "lantern_hanging": (0.1, 1.2, 0.35),
              "lit_window": (0.5, 1.4, 0.35)}  # lift above the mount, rise of the fan, relative strength
    out = []
    for key, m in plan.get("mounted", {}).items():
        if key.split("#")[0] in flames and "pos" in m:
            lift, rise, strength = flames[key.split("#")[0]]
            x, y, z = m["pos"]
            out.append((x, y, z + lift, rise, strength))
    # the cookhouse stack climbs the tower face: its crown stands 7.25 m up, 0.5 m right of the shed center
    shed = plan.get("props", {}).get("shed")
    if isinstance(shed, dict) and "pos" in shed:
        out.append((shed["pos"][0] + 0.5, shed["pos"][1] + 2.16, 7.45, 3.2, 0.7))
    return out


def _runoff_sources(plan):
    """World points (x, y, z, width, spread, length, strength) where water runs down the wall:
    below arrow slits on unrotated blocks, off both ends of window sills and off door cases.
    Length and width differ from source to source."""
    out = []
    for b in plan.get("blocks", {}).values():
        if not isinstance(b, dict) or "slits" not in b or b.get("rot_z", 0) != 0 or "center" not in b:
            continue
        cx, cy = b["center"]
        w, d = b["size"]
        for face, off, z in b["slits"]:
            x, y = {"-y": (cx + off, cy - d / 2), "+y": (cx + off, cy + d / 2),
                    "-x": (cx - w / 2, cy + off), "+x": (cx + w / 2, cy + off)}[face]
            r = random.Random(f"{x:.2f}{y:.2f}{z:.2f}")
            out.append((x, y, z, r.uniform(0.05, 0.11), r.uniform(0.03, 0.08), r.uniform(1.6, 4.4), r.uniform(0.5, 0.85)))
    for key, m in plan.get("mounted", {}).items():
        kind = key.split("#")[0]
        if kind == "lit_window" and "pos" in m and m.get("rot_z", 0) == 0:
            x, y, z = m["pos"]  # the 0.8 m sill sheds water off both ends
            for side in (-1, 1):
                r = random.Random(f"{x:.2f}{y:.2f}{z:.2f}{side}")
                out.append((x + side * 0.42, y, z - 0.44, r.uniform(0.04, 0.08), r.uniform(0.02, 0.05),
                            r.uniform(1.2, 3.6), r.uniform(0.45, 0.8)))
        if kind == "lit_door" and "pos" in m and m.get("rot_z", 0) == 0:
            x, y, z = m["pos"]
            k = m.get("scale", 1.0)  # the drip course above the door case sheds water at both ends
            for side in (-1, 1):
                r = random.Random(f"{x:.2f}{y:.2f}{z:.2f}{side}")
                out.append((x + side * 0.95 * k, y, z + 2.45 * k, r.uniform(0.07, 0.14), r.uniform(0.03, 0.07),
                            r.uniform(1.4, 3.2), r.uniform(0.45, 0.75)))
    return out


def _dry_sources(plan):
    """World points (x, y, z, half width, depth) under a ledge: the stone below stays drier and lighter."""
    out = []
    for key, m in plan.get("mounted", {}).items():
        kind = key.split("#")[0]
        if kind == "lit_window" and "pos" in m and m.get("rot_z", 0) == 0:
            x, y, z = m["pos"]
            out.append((x, y, z - 0.44, 0.34, 0.95))
    return out


def _stair_wear(nt, wx, wy, wz, plan):
    """1 in the worn hollow of the wall stair's treads, from its plan entry and the tread layout of
    assets/wall_stair.py: the flight climbs along its local +x, the wall is at local y = +0.6."""
    st = plan.get("props", {}).get("wall_stair")
    if not isinstance(st, dict) or "pos" not in st:
        return 0.0
    import math
    px, py = st["pos"]
    r = math.radians(st.get("rot_z", 0.0))
    c, s = math.cos(r), math.sin(r)
    dx, dy = _math(nt, "SUBTRACT", wx, px), _math(nt, "SUBTRACT", wy, py)
    lx = _math(nt, "ADD", _math(nt, "MULTIPLY", dx, c), _math(nt, "MULTIPLY", dy, s))
    ly = _math(nt, "SUBTRACT", _math(nt, "MULTIPLY", dy, c), _math(nt, "MULTIPLY", dx, s))
    x0, rise, run = -3.6 + 0.03, 0.25, 0.28
    inside = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", _math(nt, "GREATER_THAN", lx, x0 - 0.05), _math(nt, "LESS_THAN", lx, 3.6)),
                   _math(nt, "MULTIPLY", _math(nt, "LESS_THAN", _math(nt, "ABSOLUTE", ly), 0.62), _math(nt, "LESS_THAN", wz, 6.1)))
    # tread k (top at k x rise) starts at x0 + run (k - 1) - nose: f is 0 at its nosing, 1 at its back
    k = _math(nt, "ROUND", _math(nt, "DIVIDE", wz, rise))
    front = _math(nt, "MULTIPLY_ADD", _math(nt, "SUBTRACT", k, 1.0), run, x0 - 0.03)
    f = _math(nt, "DIVIDE", _math(nt, "SUBTRACT", lx, front), run)
    along = _range(nt, f, 0.0, 1.0, 1.0, 0.35, smooth=True)
    wander = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, _combine(nt, lx, wz), 1.5, 1.0), 0.5), 0.12)
    across = _range(nt, _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", ly, _math(nt, "ADD", STAIR_LINE, wander))), 0.10, 0.36, 1.0, 0.0, smooth=True)
    return _math(nt, "MULTIPLY", inside, _math(nt, "MULTIPLY", across, along))


def _tower_rects(plan):
    """(cx, cy, half width, half depth) of the unrotated towers and the gatehouse."""
    out = []
    for name, b in plan.get("blocks", {}).items():
        if isinstance(b, dict) and "center" in b and b.get("rot_z", 0) == 0 and ("tower" in name or "gatehouse" in name):
            out.append((*b["center"], b["size"][0] / 2, b["size"][1] / 2))
    return out


def _plume(nt, wxy, wz, src, rise, width0, spread, length):
    """1 on a vertical plume that starts at src and rises (rise=1) or runs down (rise=-1)."""
    dh = _node(nt, "ShaderNodeVectorMath", {0: wxy, 1: (src[0], src[1], 0.0)}, operation="DISTANCE").outputs["Value"]
    dz = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", wz, src[2]), float(rise))
    width = _math(nt, "MULTIPLY_ADD", _math(nt, "MAXIMUM", dz, 0.0), spread, width0)
    across = _range(nt, _math(nt, "DIVIDE", dh, width), 0.0, 1.0, 1.0, 0.0, smooth=True)
    along = _math(nt, "MULTIPLY", _range(nt, dz, -0.05, 0.2), _range(nt, dz, length * 0.35, length, 1.0, 0.0, smooth=True))
    return _math(nt, "MULTIPLY", across, along)


def _quoin_zone(nt, wx, wy, rects):
    """1 within a metre of a vertical tower corner, where long-and-short quoin work goes."""
    zones = []
    for cx, cy, hx, hy in rects:
        ax = _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", wx, cx)), hx))
        ay = _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", wy, cy)), hy))
        zones.append(_smooth(nt, _math(nt, "ADD", ax, ay), *QUOIN_ZONE, 0.0, 1.0))
    return _max_of(nt, zones)


def _half_extent(nt, p, g):
    """Half the extent of a centered box along one axis, from its object and Generated coordinate."""
    d = _math(nt, "SUBTRACT", _math(nt, "MULTIPLY", g, 2.0), 1.0)
    return _math(nt, "DIVIDE", _math(nt, "ABSOLUTE", p), _math(nt, "MAXIMUM", _math(nt, "ABSOLUTE", d), 1e-4))


def _fine_runs(nt, u, below, wet):
    """Narrow wet runs below the top edge, in stretches where `wet` is high. Each column along the
    wall may carry one run."""
    cols = _math(nt, "MULTIPLY_ADD", _noise(nt, _combine(nt, u, below), 0.7, 2.0), 0.35,
                 _math(nt, "MULTIPLY", u, RUN_COLUMNS))
    cid = _math(nt, "FLOOR", cols)
    r = [_hash(nt, cid, 32.0, 3.0 * k) for k in range(4)]
    present = _math(nt, "GREATER_THAN", _math(nt, "ADD", r[0], _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", wet, 0.5), 0.9)), 0.62)
    lo, hi = RUN_LENGTH
    length = _math(nt, "MULTIPLY_ADD", _math(nt, "POWER", r[1], 1.8), hi - lo, lo)
    centre = _math(nt, "MULTIPLY_ADD", r[2], 0.34, 0.33)
    half = _math(nt, "MULTIPLY_ADD", r[3], 0.12, 0.06)
    lateral = _range(nt, _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", _math(nt, "FRACT", cols), centre)),
                     _math(nt, "MULTIPLY", half, 0.4), _math(nt, "ADD", half, 0.10), 1.0, 0.0, smooth=True)
    along = _math(nt, "MULTIPLY", _range(nt, below, -0.05, 0.12),
                  _range(nt, below, _math(nt, "MULTIPLY", length, 0.25), length, 1.0, 0.0, smooth=True))
    broken = _range(nt, _noise(nt, _combine(nt, cid, below), 1.8, 2.0), 0.28, 0.62, 0.45, 1.0)
    return _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", present, lateral), _math(nt, "MULTIPLY", along, broken))


def _crenel_tracks(nt, g, s, seed):
    """Dark water tracks below the crenel gaps, and the spouts among them.

    `g` is the position along the wall in gap pitches, whole numbers at the gap centers.
    `s` is the distance in m below the crenel sill. Only some gaps carry a track, in clusters
    along the wall. Width and length differ from gap to gap: wide at the gap, narrower below,
    wandering sideways, with breaks and finer streaks inside. A spout is the longest, darkest and
    widest kind and leaves a pale lime deposit at its head.
    Returns (tracks, spout_lime).
    """
    k = _math(nt, "FLOOR", _math(nt, "ADD", g, 0.5))
    lateral = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", g, k), CRENEL_STEP)
    # the track leans with the wind and wanders from stone to stone
    drift = _math(nt, "MULTIPLY", _noise(nt, _combine(nt, _math(nt, "MULTIPLY", k, 5.3), _math(nt, "MULTIPLY", s, 0.35)), 1.0, 2.0), 0.32)
    wander = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, _combine(nt, _math(nt, "MULTIPLY", g, 3.1), _math(nt, "MULTIPLY", s, 1.1)), 3.0, 2.0), 0.5), 0.14)
    lateral = _math(nt, "ABSOLUTE", _math(nt, "ADD", _math(nt, "ADD", lateral, wander), _math(nt, "MULTIPLY", _math(nt, "ADD", drift, -0.16), _range(nt, s, 0.0, 4.0, 0.0, 1.0))))
    r = [_hash(nt, k, seed, 3.0 * i + 1.0) for i in range(5)]
    cluster = _noise(nt, _math(nt, "ADD", _math(nt, "MULTIPLY", k, 0.42), _math(nt, "MULTIPLY", seed, 0.173)), 1.0, 2.0, dims="1D")
    score = _math(nt, "ADD", r[0], _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", cluster, 0.5), 1.1))
    present = _math(nt, "GREATER_THAN", score, 1.0 - TRACK_SHARE)
    spout = _math(nt, "MULTIPLY", _math(nt, "GREATER_THAN", r[4], 1.0 - SPOUT_SHARE), present)
    lo, hi = TRACK_LEN
    slo, shi = SPOUT_LEN
    length = _lerp(nt, spout, _math(nt, "MULTIPLY_ADD", _math(nt, "POWER", r[1], TRACK_LEN_POWER), hi - lo, lo),
                   _math(nt, "MULTIPLY_ADD", r[1], shi - slo, slo))
    half_base = _math(nt, "MULTIPLY_ADD", _math(nt, "POWER", r[2], 1.5), 0.22, 0.06)
    half = _math(nt, "ADD", _math(nt, "ADD", half_base, _math(nt, "MULTIPLY", spout, 0.045)), _smooth(nt, s, 0.0, 1.2, 0.10, 0.0))
    # soft edges: the damp spreads into the stone beside the run, more in some courses than others
    edge_n = _range(nt, _noise(nt, _combine(nt, _math(nt, "MULTIPLY", g, 4.0), _math(nt, "MULTIPLY", s, 2.5)), 1.0, 3.0), 0.3, 0.7, 1.05, 1.6)
    across = _range(nt, _math(nt, "DIVIDE", lateral, _math(nt, "MULTIPLY", half, edge_n)), 0.0, 1.0, 1.0, 0.0, smooth=True)
    along = _math(nt, "MULTIPLY", _range(nt, s, -0.05, 0.15),
                  _range(nt, s, _math(nt, "MULTIPLY", length, 0.3), length, 1.0, 0.0, smooth=True))
    broken = _range(nt, _noise(nt, _combine(nt, _math(nt, "MULTIPLY", g, 1.3), _math(nt, "MULTIPLY", s, 0.9)), 2.2, 3.0),
                    0.30, 0.60, 0.30, 1.0)
    fibres = _range(nt, _noise(nt, _combine(nt, _math(nt, "MULTIPLY", g, 9.0), _math(nt, "MULTIPLY", s, 0.5)), 1.0, 2.0), 0.30, 0.70, 0.55, 1.0)
    strength = _math(nt, "MULTIPLY_ADD", r[3], 0.45, 0.55)
    strength = _math(nt, "ADD", strength, _math(nt, "MULTIPLY", spout, 0.3))
    tracks = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", present, across),
                   _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", along, broken), _math(nt, "MULTIPLY", fibres, strength)), clamp=True)
    lime_across = _range(nt, _math(nt, "DIVIDE", lateral, 0.05), 0.2, 1.0, 1.0, 0.0, smooth=True)
    lime_along = _math(nt, "MULTIPLY", _range(nt, s, 0.0, 0.1), _range(nt, s, 0.4, 1.9, 1.0, 0.0, smooth=True))
    return tracks, _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", spout, lime_across), lime_along)


def _repairs(nt, wx, wy, wz, wnx, wny):
    """Masks of the REPAIRS list, from the world position and normal.

    Returns a dict: `rebuild` is 1 where stones were relaid (rebuild and blocked kinds), `edge` is
    1 on their fresh mortar outline, `pick` and `size` are the stone and block size of the patch
    under the pixel, `jamb` is 1 on the dressed surround of a blocked opening, `repoint` and `odd`
    are 1 inside the patches of those kinds.
    """
    out = {k: [] for k in ("rebuild", "edge", "pick", "size", "jamb", "repoint", "odd")}
    for i, r in enumerate(REPAIRS):
        (x0, y0), (x1, y1) = r["from"], r["to"]
        length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        ux, uy = (x1 - x0) / length, (y1 - y0) / length
        nx, ny = uy, -ux  # outward normal: the face is walked with the wall body on the left
        rx, ry = _math(nt, "SUBTRACT", wx, x0), _math(nt, "SUBTRACT", wy, y0)
        t = _math(nt, "ADD", _math(nt, "MULTIPLY", rx, ux), _math(nt, "MULTIPLY", ry, uy))
        off = _math(nt, "ADD", _math(nt, "MULTIPLY", rx, nx), _math(nt, "MULTIPLY", ry, ny))
        facing = _math(nt, "ADD", _math(nt, "MULTIPLY", wnx, nx), _math(nt, "MULTIPLY", wny, ny))
        on = _math(nt, "MULTIPLY", _math(nt, "LESS_THAN", _math(nt, "ABSOLUTE", off), 0.08),
                   _math(nt, "GREATER_THAN", facing, 0.7))
        half = length / 2
        dx = _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", t, half))
        z0, z1 = r["z"]
        if r["kind"] == "blocked":
            # an arched opening: straight jambs up to the springing, a round head of the full width
            rise = _math(nt, "SQRT", _math(nt, "MAXIMUM", _math(nt, "SUBTRACT", half * half, _math(nt, "MULTIPLY", dx, dx)), 0.0))
            top = _math(nt, "ADD", z1 - half, rise)
            d = _math(nt, "MAXIMUM", _math(nt, "SUBTRACT", dx, half),
                      _math(nt, "MAXIMUM", _math(nt, "SUBTRACT", wz, top), _math(nt, "SUBTRACT", z0, wz)))
        else:
            d = _math(nt, "MAXIMUM", _math(nt, "SUBTRACT", dx, half),
                      _math(nt, "SUBTRACT", _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", wz, (z0 + z1) / 2)), (z1 - z0) / 2))
            # the outline follows stones, not a ruler
            d = _math(nt, "ADD", d, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, _combine(nt, t, wz), 3.0 + i, 2.0), 0.5), 0.30))
        inside = _math(nt, "MULTIPLY", _math(nt, "LESS_THAN", d, 0.0), on)
        if r["kind"] in ("rebuild", "blocked"):
            out["rebuild"].append(inside)
            out["edge"].append(_math(nt, "MULTIPLY", _range(nt, _math(nt, "ABSOLUTE", d), 0.0, 0.03, 1.0, 0.0, smooth=True), on))
            out["pick"].append(_math(nt, "MULTIPLY", inside, r["stone"]))
            out["size"].append(_math(nt, "MULTIPLY", inside, r["size"]))
        if r["kind"] == "blocked":
            out["jamb"].append(_math(nt, "MULTIPLY", _math(nt, "MULTIPLY", _math(nt, "GREATER_THAN", d, 0.0),
                                                        _math(nt, "LESS_THAN", d, JAMB)), on))
        if r["kind"] in ("repoint", "odd"):
            out[r["kind"]].append(inside)
    res = {}
    for k, v in out.items():
        res[k] = v[0] if len(v) == 1 else (_max_of(nt, v) if v else 0.0)
        if k in ("pick", "size") and len(v) > 1:
            acc = v[0]
            for x in v[1:]:
                acc = _math(nt, "ADD", acc, x)
            res[k] = acc
    return res


def _putlogs(nt, u, hg, seed):
    """Putlog holes: square recesses where scaffold poles once stood, in rows at lift height.

    Returns (hole, lip, low): `hole` is 1 inside a hole, `lip` is 1 just outside it and
    `low` is 1 at the bottom of the hole and 0 at the top.
    """
    pu, pv = PUTLOG_PITCH
    lu = _math(nt, "ADD", u, _math(nt, "MULTIPLY", _hash(nt, seed, 7.5, 1.5), pu))
    iu = _math(nt, "FLOOR", _math(nt, "DIVIDE", lu, pu))
    cu = _math(nt, "SUBTRACT", lu, _math(nt, "MULTIPLY", _math(nt, "ADD", iu, 0.5), pu))
    h0 = _math(nt, "SUBTRACT", hg, PUTLOG_FIRST)
    kz = _math(nt, "FLOOR", _math(nt, "DIVIDE", h0, pv))
    cz = _math(nt, "SUBTRACT", h0, _math(nt, "MULTIPLY", _math(nt, "ADD", kz, 0.5), pv))
    key = _math(nt, "ADD", iu, _math(nt, "MULTIPLY", seed, 0.71))
    lift = _math(nt, "MULTIPLY", _math(nt, "GREATER_THAN", _hash(nt, kz, seed, 8.5), 1.0 - PUTLOG_ROWS),
                 _math(nt, "GREATER_THAN", kz, -0.5))
    open_ = _math(nt, "GREATER_THAN", _hash(nt, key, kz, 9.5), 1.0 - PUTLOG_OPEN)
    present = _math(nt, "MULTIPLY", lift, open_)
    jx = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _hash(nt, key, kz, 10.5), 0.5), 0.05)
    jz = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _hash(nt, key, kz, 11.5), 0.5), 0.04)
    grow = _math(nt, "MULTIPLY_ADD", _hash(nt, key, kz, 12.5), 0.3, 0.88)
    nx = _math(nt, "DIVIDE", _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", cu, jx)), _math(nt, "MULTIPLY", grow, PUTLOG_HOLE[0]))
    nz_signed = _math(nt, "DIVIDE", _math(nt, "SUBTRACT", cz, jz), _math(nt, "MULTIPLY", grow, PUTLOG_HOLE[1]))
    dd = _math(nt, "MAXIMUM", nx, _math(nt, "ABSOLUTE", nz_signed))
    dd = _math(nt, "ADD", dd, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, _combine(nt, u, hg), 38.0, 1.0), 0.5), 0.30))
    hole = _math(nt, "MULTIPLY", _range(nt, dd, 0.86, 1.0, 1.0, 0.0, smooth=True), present)
    lip = _math(nt, "MULTIPLY", _range(nt, dd, 1.0, 1.5, 1.0, 0.0, smooth=True), present)
    low = _range(nt, nz_signed, 0.7, -0.9, 0.0, 1.0, smooth=True)
    return hole, lip, low


def _rows(nt, v, period_len, count, var, salt):
    """Rows of random height, `count` per period of `period_len` m with random shares of the period.

    Returns (period, t, start, end, row): the period index, the position in the period (0..1), the
    lower and upper edge of the row under it in the same units, and a running row number.
    """
    t_full = _math(nt, "MULTIPLY", v, 1.0 / period_len)
    period = _math(nt, "FLOOR", t_full)
    t = _math(nt, "SUBTRACT", t_full, period)
    w = [_math(nt, "MULTIPLY_ADD", _hash(nt, period, salt + k), var, 1.0) for k in range(count)]
    total = w[0]
    for x in w[1:]:
        total = _math(nt, "ADD", total, x)
    cum, acc = [], None
    for x in w:
        acc = x if acc is None else _math(nt, "ADD", acc, x)
        cum.append(_math(nt, "DIVIDE", acc, total))
    above = [_math(nt, "GREATER_THAN", t, c) for c in cum[:-1]]  # above[k]: t is past the end of row k
    start, end, row = 0.0, cum[0], _math(nt, "MULTIPLY", period, float(count))
    for k, a in enumerate(above):
        lower = cum[k - 1] if k else 0.0
        start = _math(nt, "ADD", start, _math(nt, "MULTIPLY", a, _math(nt, "SUBTRACT", cum[k], lower)))
        end = _math(nt, "ADD", end, _math(nt, "MULTIPLY", a, _math(nt, "SUBTRACT", cum[k + 1], cum[k])))
        row = _math(nt, "ADD", row, a)
    return period, t, start, end, row


def _slabs(nt, wx, wy):
    """Flagstone paving: rectangular slabs 0.5-0.9 m across, laid in rows along the first coordinate.

    Returns a dict with `joint` (1 in the narrow dirt joints), `arris` (1 just outside a joint,
    fading), `cavity` (0 at a joint, 1 inside the slab), `face` (0 at the edge, 1 inside),
    `inner` (1 away from the edges), `bowl` (1 in the middle of the slab), and per-slab randoms
    `rand`, `tone`, `wear`, `wear2`.
    """
    wob = _split(nt, _noise(nt, _combine(nt, wx, wy), 5.0, 2.0, color=True))
    u1 = _math(nt, "MULTIPLY_ADD", _math(nt, "SUBTRACT", wob[0], 0.5), 0.05, wx)
    v1 = _math(nt, "MULTIPLY_ADD", _math(nt, "SUBTRACT", wob[1], 0.5), 0.04, wy)
    period, t, start, end, row = _rows(nt, v1, SLAB_PERIOD, SLAB_ROWS, SLAB_ROW_VAR, 60.0)
    length = _math(nt, "MULTIPLY_ADD", _hash(nt, row, 61.5), SLAB_LEN[1] - SLAB_LEN[0], SLAB_LEN[0])
    p = _math(nt, "MULTIPLY_ADD", _hash(nt, row, 62.5), 9.0, u1)
    c = _math(nt, "FLOOR", _math(nt, "DIVIDE", p, length))

    def joint_x(i):
        return _math(nt, "MULTIPLY", length, _math(nt, "MULTIPLY_ADD", _math(nt, "SUBTRACT", _hash(nt, i, row, 63.5), 0.5),
                                                    SLAB_JITTER, i))

    block = _math(nt, "ADD", _math(nt, "SUBTRACT", c, _math(nt, "LESS_THAN", p, joint_x(c))),
                  _math(nt, "GREATER_THAN", p, joint_x(_math(nt, "ADD", c, 1.0))))
    x0, x1 = joint_x(block), joint_x(_math(nt, "ADD", block, 1.0))
    height = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", end, start), SLAB_PERIOD)
    du = _math(nt, "MINIMUM", _math(nt, "SUBTRACT", p, x0), _math(nt, "SUBTRACT", x1, p))
    dv = _math(nt, "MULTIPLY", _math(nt, "MINIMUM", _math(nt, "SUBTRACT", t, start), _math(nt, "SUBTRACT", end, t)), SLAB_PERIOD)
    de = _math(nt, "MINIMUM", du, dv)  # meters to the nearest joint line
    # position in the slab: 0 at an edge, 1 in the middle
    mid = _math(nt, "MINIMUM", _math(nt, "DIVIDE", _math(nt, "MULTIPLY", du, 2.0), _math(nt, "MAXIMUM", _math(nt, "SUBTRACT", x1, x0), 0.05)),
                _math(nt, "DIVIDE", _math(nt, "MULTIPLY", dv, 2.0), _math(nt, "MAXIMUM", height, 0.05)))
    wide = _range(nt, _noise(nt, _combine(nt, wx, wy), 6.0, 2.0), 0.25, 0.75, 0.0, 1.0)
    half = _math(nt, "MULTIPLY_ADD", wide, SLAB_JOINT[1] - SLAB_JOINT[0], SLAB_JOINT[0])
    joint = _range(nt, de, _math(nt, "ADD", half, 0.004), _math(nt, "SUBTRACT", half, 0.004), 0.0, 1.0, smooth=True)

    def slab_hash(k):
        return _hash(nt, block, row, k)

    return {
        "joint": joint,
        "arris": _range(nt, de, half, _math(nt, "ADD", half, ARRIS), 1.0, 0.0, smooth=True),
        "cavity": _range(nt, de, half, _math(nt, "ADD", half, CAVITY), 0.0, 1.0, smooth=True),
        "face": _range(nt, de, half, _math(nt, "ADD", half, FACE_ROUND), 0.0, 1.0, smooth=True),
        "inner": _range(nt, de, 0.05, 0.22, 0.0, 1.0, smooth=True),
        "bowl": _range(nt, mid, 0.0, 1.0, 0.0, 1.0, smooth=True),
        "rand": slab_hash(64.5), "tone": slab_hash(65.5), "wear": slab_hash(66.5), "wear2": slab_hash(67.5),
    }


def _courses(nt, u, v, quoin, plinth_of, wz, side, scale, fresh):
    """Level courses of random height, each with its own block length and wandering joints.

    `quoin` is 1 where long-and-short corner work starts; its edge is a mortar line.
    `plinth_of(z)` is 1 where the plinth begins at world height z; it is read at the course center,
    so a course keeps one block length. `wz` is the world height at the pixel, `side` is 1 on wall
    faces, `scale` is the pattern scale. `fresh` is 1 where the pointing is new and tight (repair patches).
    """
    # edges are not straight lines: a fast wobble and a slow warp, small across the beds
    wob = _split(nt, _noise(nt, _combine(nt, u, v), 11.0, 2.0, color=True))
    warp = _split(nt, _noise(nt, _combine(nt, u, v), 3.7, 2.0, color=True))
    u1 = _math(nt, "MULTIPLY_ADD", _math(nt, "SUBTRACT", wob[0], 0.5), EDGE_WOBBLE[0],
               _math(nt, "MULTIPLY_ADD", _math(nt, "SUBTRACT", warp[0], 0.5), EDGE_WARP[0], u))
    v1 = _math(nt, "MULTIPLY_ADD", _math(nt, "SUBTRACT", wob[1], 0.5), EDGE_WOBBLE[1],
               _math(nt, "MULTIPLY_ADD", _math(nt, "SUBTRACT", warp[1], 0.5), EDGE_WARP[1], v))

    # COURSES courses per period, with random shares of the period height
    period, t, start, end, row = _rows(nt, v1, PERIOD, COURSES, COURSE_VAR, 10.0)
    dv = _math(nt, "MULTIPLY", _math(nt, "MINIMUM", _math(nt, "SUBTRACT", t, start),
                                      _math(nt, "SUBTRACT", end, t)), PERIOD)

    # blocks along the course: nominal length, vertical joints jittered per joint
    length = _math(nt, "MULTIPLY_ADD", _math(nt, "POWER", _hash(nt, row, 1.5), BLOCK_LEN_POWER),
                   BLOCK_LEN[1] - BLOCK_LEN[0], BLOCK_LEN[0])
    # near a tower corner the courses alternate short headers and long stretchers: a hard change of
    # block length, so the zone edge carries a mortar line
    quoin_on = _math(nt, "GREATER_THAN", quoin, 0.5)
    parity = _math(nt, "MULTIPLY", _math(nt, "FRACT", _math(nt, "MULTIPLY", row, 0.5)), 2.0)
    quoin_len = _math(nt, "MULTIPLY_ADD", parity, QUOIN_LEN[1] - QUOIN_LEN[0], QUOIN_LEN[0])
    length = _lerp(nt, quoin_on, length, quoin_len)
    # the plinth course is read at the course center
    z_row = _math(nt, "ADD", wz, _math(nt, "DIVIDE", _math(nt, "SUBTRACT", _math(
        nt, "MULTIPLY", _math(nt, "ADD", period, _math(nt, "MULTIPLY", _math(nt, "ADD", start, end), 0.5)), PERIOD), v1), scale))
    plinth_row = _math(nt, "MULTIPLY", plinth_of(z_row), side)
    length = _math(nt, "MULTIPLY", length, _math(nt, "MULTIPLY_ADD", plinth_row, PLINTH_LEN - 1.0, 1.0))
    p = _math(nt, "MULTIPLY_ADD", _hash(nt, row, 2.5), 9.0, u1)
    c = _math(nt, "FLOOR", _math(nt, "DIVIDE", p, length))

    def joint_x(i):
        return _math(nt, "MULTIPLY", length, _math(nt, "MULTIPLY_ADD", _math(nt, "SUBTRACT", _hash(nt, i, row, 5.5), 0.5),
                                                    JITTER, i))

    # index of the block under p: jittered joints can move into the neighbouring slot either way
    block = _math(nt, "ADD", _math(nt, "SUBTRACT", c, _math(nt, "LESS_THAN", p, joint_x(c))),
                  _math(nt, "GREATER_THAN", p, joint_x(_math(nt, "ADD", c, 1.0))))
    x0, x1 = joint_x(block), joint_x(_math(nt, "ADD", block, 1.0))
    du = _math(nt, "MINIMUM", _math(nt, "SUBTRACT", p, x0), _math(nt, "SUBTRACT", x1, p))
    width = _math(nt, "SUBTRACT", x1, x0)
    # long blocks are sometimes cut in two by a vertical joint
    cut_v = _math(nt, "MULTIPLY", _math(nt, "GREATER_THAN", _hash(nt, block, row, 7.5), 1.0 - SPLIT),
                  _math(nt, "MULTIPLY", _math(nt, "GREATER_THAN", width, SPLIT_MIN), _math(nt, "SUBTRACT", 1.0, quoin_on)))
    mid_u = _math(nt, "ADD", _math(nt, "MULTIPLY", _math(nt, "ADD", x0, x1), 0.5),
                  _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _hash(nt, block, row, 6.5), 0.5),
                        _math(nt, "MULTIPLY", width, 0.25)))
    du = _math(nt, "MINIMUM", du, _lerp(nt, cut_v, 9.0, _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", p, mid_u))))
    piece = _math(nt, "MULTIPLY", _math(nt, "GREATER_THAN", p, mid_u), cut_v)
    stone_id = _math(nt, "MULTIPLY_ADD", piece, 0.37, block)
    # extent of the single stone under p, after the optional cut
    px0 = _math(nt, "ADD", x0, _math(nt, "MULTIPLY", piece, _math(nt, "SUBTRACT", mid_u, x0)))
    px1 = _math(nt, "SUBTRACT", x1, _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", cut_v, _math(nt, "SUBTRACT", 1.0, piece)),
                                           _math(nt, "SUBTRACT", x1, mid_u)))
    lx = _math(nt, "DIVIDE", _math(nt, "SUBTRACT", p, px0), _math(nt, "MAXIMUM", _math(nt, "SUBTRACT", px1, px0), 0.05), clamp=True)

    def stone_hash(k):
        return _hash(nt, stone_id, row, k)

    rand = stone_hash(9.5)
    tone = _math(nt, "MULTIPLY", _math(nt, "ADD", stone_hash(13.5), stone_hash(14.5)), 0.5)  # most stones sit mid-range
    outlier = stone_hash(16.5)
    damage = stone_hash(15.5)
    rust = stone_hash(19.5)
    wear = stone_hash(21.5)
    wear2 = stone_hash(23.5)
    tilt_u = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", stone_hash(25.5), 0.5), 2.0)
    tilt_v = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", stone_hash(27.5), 0.5), 2.0)
    replaced = _math(nt, "GREATER_THAN", stone_hash(11.5), 1.0 - REPLACED)
    # where the stone sits between its lower (0) and upper (1) edge
    vfrac = _math(nt, "DIVIDE", _math(nt, "SUBTRACT", t, start), _math(nt, "MAXIMUM", _math(nt, "SUBTRACT", end, start), 0.02),
                  clamp=True)

    # joints: narrow, filled to the face; each stretch of joint has its own width, and where the
    # pointing has eroded the joint is wider and deeper. Distances are in pattern units.
    mind = _math(nt, "MINIMUM", du, dv)
    grid = _combine(nt, p, v1)
    wide = _range(nt, _noise(nt, grid, 14.0, 2.0), 0.25, 0.75, 0.0, 1.0)
    erode = _math(nt, "MULTIPLY", _range(nt, _noise(nt, grid, 2.3, 3.0), *ERODE_RANGE, 0.0, 1.0, smooth=True),
                  _math(nt, "SUBTRACT", 1.0, fresh))
    half = _math(nt, "MULTIPLY", _math(nt, "ADD", _math(nt, "MULTIPLY_ADD", wide, JOINT_HALF[1] - JOINT_HALF[0], JOINT_HALF[0]),
                                       _math(nt, "MULTIPLY", erode, ERODE_HALF)), scale)
    soft = _math(nt, "MULTIPLY", scale, JOINT_SOFT)
    joint = _range(nt, mind, _math(nt, "ADD", half, soft), _math(nt, "SUBTRACT", half, soft), 0.0, 1.0, smooth=True)
    joint = _math(nt, "MAXIMUM", joint, _range(nt, _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", quoin, 0.5)), 0.0, 0.03, 1.0, 0.0, smooth=True))
    # the worn arris, the shade in the recessed joint and the barely rounded face
    arris = _range(nt, mind, half, _math(nt, "ADD", half, _math(nt, "MULTIPLY", scale, ARRIS)), 1.0, 0.0, smooth=True)
    cavity = _range(nt, mind, half, _math(nt, "ADD", half, _math(nt, "MULTIPLY", scale, CAVITY)), 0.0, 1.0, smooth=True)
    face = _range(nt, mind, half, _math(nt, "ADD", half, _math(nt, "MULTIPLY", scale, FACE_ROUND)), 0.0, 1.0, smooth=True)

    # a corner of some stones has broken off: the break line is a diagonal with a ragged edge
    right = _math(nt, "GREATER_THAN", stone_hash(29.5), 0.5)
    topc = _math(nt, "GREATER_THAN", stone_hash(31.5), 0.5)
    dxc = _lerp(nt, right, _math(nt, "SUBTRACT", p, px0), _math(nt, "SUBTRACT", px1, p))
    dyc = _math(nt, "MULTIPLY", _lerp(nt, topc, _math(nt, "SUBTRACT", t, start), _math(nt, "SUBTRACT", end, t)), PERIOD)
    ca = _math(nt, "MULTIPLY_ADD", stone_hash(33.5), 0.20, 0.07)
    cb = _math(nt, "MULTIPLY_ADD", stone_hash(35.5), 0.10, 0.05)
    cm = _math(nt, "ADD", _math(nt, "ADD", _math(nt, "DIVIDE", dxc, ca), _math(nt, "DIVIDE", dyc, cb)),
               _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, grid, 19.0, 2.0), 0.5), 0.7))
    chip_on = _math(nt, "GREATER_THAN", stone_hash(37.5), 1.0 - CORNER_CHIP)
    corner = _math(nt, "MULTIPLY", _math(nt, "LESS_THAN", cm, 1.0), chip_on)
    corner_line = _math(nt, "MULTIPLY", _range(nt, _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", cm, 1.02)), 0.0, 0.2, 1.0, 0.0, smooth=True),
                        chip_on)
    return {"joint": joint, "arris": arris, "cavity": cavity, "face": face, "rand": rand, "tone": tone,
            "grid": grid, "replaced": replaced, "vfrac": vfrac, "damage": damage,
            "outlier": outlier, "rust": rust, "wear": wear, "wear2": wear2, "lx": lx,
            "tilt_u": tilt_u, "tilt_v": tilt_v, "erode": erode, "corner": corner, "corner_line": corner_line}


def build(mat, nt, bsdf):
    tc = _node(nt, "ShaderNodeTexCoord")
    pos, gen = tc.outputs["Object"], tc.outputs["Generated"]

    # ---- coordinates picked by face normal ----
    ax, ay, az = _split(nt, _node(
        nt, "ShaderNodeVectorMath", {0: tc.outputs["Normal"]}, operation="ABSOLUTE").outputs[0])
    x, y, z = _split(nt, pos)
    gx, gy, gz = _split(nt, gen)
    # along-wall: x on faces turned toward y or z, y on faces turned toward x
    u = _math(nt, "MULTIPLY_ADD", y, ax, _math(nt, "MULTIPLY", x, _math(nt, "ADD", ay, az)))
    gu = _math(nt, "MULTIPLY_ADD", gy, ax, _math(nt, "MULTIPLY", gx, _math(nt, "ADD", ay, az)))
    top = _smooth(nt, az, 0.55, 0.80)  # 1 on horizontal faces
    side = _math(nt, "SUBTRACT", 1.0, top)

    # world position and normal: macro weathering uses them, so no two wall areas look alike
    geo = _node(nt, "ShaderNodeNewGeometry")
    wp = geo.outputs["Position"]
    wx, wy, wz = _split(nt, wp)
    wxy = _combine(nt, wx, wy)
    wnx, wny, wnz = _split(nt, geo.outputs["Normal"])
    # the course pattern runs along the wall and up the world z axis, so every box of a wall shares it
    axis_x = _node(nt, "ShaderNodeVectorTransform", {"Vector": (1.0, 0.0, 0.0)},
                   vector_type="VECTOR", convert_from="OBJECT", convert_to="WORLD").outputs[0]
    axis_y = _node(nt, "ShaderNodeVectorTransform", {"Vector": (0.0, 1.0, 0.0)},
                   vector_type="VECTOR", convert_from="OBJECT", convert_to="WORLD").outputs[0]
    along_x, along_y = _dot(nt, wp, axis_x), _dot(nt, wp, axis_y)
    uw = _math(nt, "MULTIPLY_ADD", along_y, ax, _math(nt, "MULTIPLY", along_x, _math(nt, "ADD", ay, az)))
    vw = _lerp(nt, top, wz, wy)

    # ---- the object's own extents: distance below its top edge, size class, crenel pitch ----
    half_h = _math(nt, "MINIMUM", _math(nt, "MAXIMUM", _half_extent(nt, z, gz), 0.02), 25.0)
    below = _math(nt, "MAXIMUM", _math(nt, "SUBTRACT", half_h, z), 0.0)
    height_total = _math(nt, "MULTIPLY", half_h, 2.0)
    small = _range(nt, height_total, 1.2, 2.4, 1.0, 0.0, smooth=True)  # merlons, parapets, caps, loose stones
    thin = _range(nt, height_total, 0.14, 0.30, 1.0, 0.0, smooth=True)  # coping and cap stones: one stone each
    tall = _smooth(nt, height_total, 2.0, 3.2)  # wall boxes: a track continues below the parapet
    half_l = _math(nt, "MINIMUM", _math(nt, "MAXIMUM", _half_extent(nt, u, gu), 0.1), 40.0)
    long_wall = _smooth(nt, half_l, 1.0, 1.7)
    gaps = _math(nt, "FLOOR", _math(nt, "DIVIDE", _math(nt, "ADD", _math(nt, "MULTIPLY", half_l, 2.0), 0.55), CRENEL_STEP))
    gap_pos = _math(nt, "SUBTRACT", _math(nt, "DIVIDE", u, CRENEL_STEP), _math(nt, "FRACT", _math(nt, "MULTIPLY", gaps, 0.5)))

    up = _smooth(nt, wnz, 0.80, 0.95)  # 1 on faces that look at the sky
    topup = _math(nt, "MAXIMUM", top, up)
    north = _range(nt, wny, 0.2, 0.8)  # faces that look north stay damp
    south = _range(nt, wny, -0.2, -0.8)  # faces that look south dry out between showers
    aspect = _math(nt, "SUBTRACT", _math(nt, "MULTIPLY_ADD", north, NORTH_GROWTH, 1.0), _math(nt, "MULTIPLY", south, SOUTH_LESS))
    shade = _range(nt, _math(nt, "ADD", _math(nt, "MULTIPLY", wnx, MOON_FROM[0]), _math(nt, "MULTIPLY", wny, MOON_FROM[1])),
                   0.7, -0.7, 0.5, 1.0)  # more algae on faces turned away from the moon
    # rain comes from the south-west: those faces are wetter
    windward = _range(nt, _math(nt, "ADD", _math(nt, "MULTIPLY", wnx, RAIN_FROM[0]), _math(nt, "MULTIPLY", wny, RAIN_FROM[1])),
                      -0.8, 0.8, 0.0, 1.0)
    # courtyard faces look toward the courtyard center; they stand on z 0, the others on the lower ward
    to_yard = _node(nt, "ShaderNodeVectorMath", {0: (*COURTYARD, 0.0), 1: wxy}, operation="SUBTRACT").outputs[0]
    dx, dy, _ = _split(nt, _node(nt, "ShaderNodeVectorMath", {0: to_yard}, operation="NORMALIZE").outputs[0])
    facing = _math(nt, "ADD", _math(nt, "MULTIPLY", dx, wnx), _math(nt, "MULTIPLY", dy, wny))
    inward = _smooth(nt, facing, -0.1, 0.3)
    ground = _lerp(nt, inward, WARD_Z, YARD_Z)
    hg = _math(nt, "SUBTRACT", wz, ground)  # height above the ground this face stands on

    # one seed per wall face: the plane the face lies in and the length of its box
    face_plane = _math(nt, "ADD", _math(nt, "MULTIPLY", wnx, wx), _math(nt, "MULTIPLY", wny, wy))
    seed = _math(nt, "ADD", _math(nt, "FLOOR", _math(nt, "MULTIPLY_ADD", half_l, 20.0, 0.5)),
                 _math(nt, "MULTIPLY", _math(nt, "FLOOR", _math(nt, "MULTIPLY_ADD", face_plane, 4.0, 0.5)), 1.13))

    plan = _plan()
    quoin = _math(nt, "MULTIPLY", _quoin_zone(nt, wx, wy, _tower_rects(plan)), side)
    # plinth: the lowest stones, larger and darker
    def plinth_of(z):
        low = _range(nt, z, *PLINTH_OUT_Z, 1.0, 0.0, smooth=True)
        yard = _math(nt, "MULTIPLY", _range(nt, z, *PLINTH_IN_Z, 1.0, 0.0, smooth=True), _range(nt, z, -0.6, -0.3))
        return _lerp(nt, inward, low, yard)

    plinth = _math(nt, "MULTIPLY", plinth_of(wz), side)
    scale = _lerp(nt, top, 1.0, CAP_SCALE)

    # ---- pattern: coursed stone on side faces, flagstones on tops ----
    # `dressed` is 1 on stones that are single chiseled pieces (arch ring, jambs): no course
    # pattern, a paler tone and a random tone per object. Callers copy the material and set it.
    sw = nt.nodes.new("ShaderNodeValue")
    sw.name = "dressed"
    dressed = sw.outputs[0]
    plain = _math(nt, "SUBTRACT", 1.0, dressed)
    obj_rand = _node(nt, "ShaderNodeObjectInfo").outputs["Random"]
    wall_only = _math(nt, "MULTIPLY", side, plain)
    walls = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", wall_only, tall), _math(nt, "SUBTRACT", 1.0, small))  # big rubble walls
    courses_on = _math(nt, "MULTIPLY", plain, _math(nt, "SUBTRACT", 1.0, thin))
    flag_on = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", top, courses_on), _math(nt, "SUBTRACT", 1.0, small))

    # repair patches: another stone in a block size of its own, outlined by new mortar
    rep = _repairs(nt, wx, wy, wz, wnx, wny)
    p_pick, p_size = rep["pick"], rep["size"]
    pm = _math(nt, "MULTIPLY", rep["rebuild"], walls)
    p_line = _math(nt, "MULTIPLY", rep["edge"], walls)
    repoint = _math(nt, "MULTIPLY", rep["repoint"], walls)
    jamb = _math(nt, "MULTIPLY", rep["jamb"], walls)
    p_scale = _math(nt, "MULTIPLY", scale, _lerp(nt, pm, 1.0, _math(nt, "MULTIPLY_ADD", p_size, PATCH_SCALE[1] - PATCH_SCALE[0], PATCH_SCALE[0])))
    p_shift = _math(nt, "MULTIPLY", pm, _math(nt, "MULTIPLY_ADD", p_pick, 7.0, 1.3))
    pat = _courses(nt, _math(nt, "ADD", _math(nt, "MULTIPLY", uw, p_scale), p_shift),
                   _math(nt, "ADD", _math(nt, "MULTIPLY", vw, p_scale), _math(nt, "MULTIPLY", p_shift, 0.43)),
                   quoin, plinth_of, wz, side, p_scale, _math(nt, "MAXIMUM", pm, repoint))
    fl = _slabs(nt, along_x, along_y)

    def pick(wall, flag):
        return _lerp(nt, flag_on, wall, flag)

    wall_face = _math(nt, "MULTIPLY", courses_on, _math(nt, "SUBTRACT", 1.0, top))  # top faces have no course joints
    joint = _math(nt, "MAXIMUM", _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", pat["joint"], wall_face),
                                       _math(nt, "MULTIPLY", fl["joint"], flag_on)), p_line)
    arris = _math(nt, "MULTIPLY", pick(pat["arris"], fl["arris"]), _math(nt, "MULTIPLY", courses_on, _math(nt, "MAXIMUM", flag_on, side)))
    rim = _math(nt, "MULTIPLY", arris, _math(nt, "SUBTRACT", 1.0, joint))
    cavity = pick(_lerp(nt, wall_face, 1.0, pat["cavity"]), fl["cavity"])
    rand = _lerp(nt, dressed, pick(pat["rand"], fl["rand"]), obj_rand)
    tone_r = _lerp(nt, dressed, pick(pat["tone"], fl["tone"]), _hash(nt, obj_rand, 3.0, 3.0))
    wear = pick(pat["wear"], fl["wear"])
    wear2 = pick(pat["wear2"], fl["wear2"])
    new = _math(nt, "MULTIPLY", pat["replaced"], wall_only)  # newer stones, wall faces only
    grid = pat["grid"]
    # some slabs have sunk and hold water: the dish of a flag, a lower-lying wall top or a worn cap
    f_worn = _lerp(nt, flag_on, _math(nt, "MULTIPLY", pat["face"], _range(nt, rand, 0.4, 0.7)),
                   _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", fl["inner"], fl["bowl"]), _range(nt, wear2, 0.50, 0.80, 0.0, 1.0)))

    # putlog holes: rows at scaffold height on the big walls
    hole, hole_lip, hole_low = _putlogs(nt, u, hg, seed)
    below_ok = _range(nt, below, 0.6, 1.1)
    hole_gate = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", walls, below_ok), _math(nt, "SUBTRACT", 1.0, quoin))
    hole = _math(nt, "MULTIPLY", hole, hole_gate)
    hole_lip = _math(nt, "MULTIPLY", hole_lip, hole_gate)

    # ---- large zones: areas of metres that are darker, lighter, cooler, warmer ----
    zone = _range(nt, _noise(nt, _scaled(nt, wp, (0.16, 0.16, 0.24)), 1.0, 2.0), 0.35, 0.65, *ZONE_BIG)
    zone = _math(nt, "MULTIPLY", zone, _range(nt, _noise(nt, _scaled(nt, wp, (0.55, 0.55, 0.65), (3.0, 7.0, 1.0)), 1.0, 2.0), 0.35, 0.65, *ZONE_MID))
    zone = _math(nt, "MULTIPLY", zone, _lerp(nt, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, windward), side), 1.0, LEEWARD_LIGHT))
    # the lower wall is damper and darker; the upper wall dries
    zone = _math(nt, "MULTIPLY", zone, _range(nt, hg, 3.2, 0.8, 1.0, LOWER_DARK, smooth=True))
    hue = _range(nt, _noise(nt, _scaled(nt, wp, (0.14, 0.14, 0.20), (8.0, 1.0, 15.0)), 1.0, 2.0), 0.30, 0.70)
    # sheltered stone under a sill stays pale
    dry = _max_of(nt, [_math(nt, "MULTIPLY", _plume(nt, wxy, wz, (s[0], s[1], s[2]), -1, s[3], 0.12, s[4]), 0.9)
                       for s in _dry_sources(plan)])

    # ---- stone color: per-stone family and tone, mottling, grain, chipped arrises ----
    fam = _mix(nt, pm, _ramp(nt, rand, STONE_FAMILIES), _ramp(nt, p_pick, PATCH_STONES, constant=True))
    # an `odd` patch: some of its stones were replaced one by one in another stone
    odd = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", rep["odd"], walls), _math(nt, "GREATER_THAN", pat["outlier"], 1.0 - ODD_SHARE))
    fam = _mix(nt, odd, fam, ODD_STONE)
    outlier = pat["outlier"]
    pale = _math(nt, "GREATER_THAN", outlier, 1.0 - OUTLIER)
    dark = _math(nt, "MULTIPLY", _math(nt, "GREATER_THAN", outlier, 1.0 - 2.0 * OUTLIER), _math(nt, "SUBTRACT", 1.0, pale))
    outlier_gain = _lerp(nt, plain, 1.0, _math(nt, "ADD", _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", dark, OUTLIER_GAIN)),
                                               _math(nt, "MULTIPLY", pale, OUTLIER_GAIN)))
    gain = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY_ADD", tone_r, STONE_GAIN[1] - STONE_GAIN[0], STONE_GAIN[0]), outlier_gain)
    gain = _lerp(nt, pm, gain, _math(nt, "MULTIPLY_ADD", pat["tone"], PATCH_GAIN[1] - PATCH_GAIN[0], PATCH_GAIN[0]))
    gain = _math(nt, "MULTIPLY", gain, _lerp(nt, flag_on, 1.0, _math(nt, "MULTIPLY_ADD", fl["tone"], 0.40, 0.80)))  # slabs differ a little more than stones
    mottle_k = _math(nt, "MULTIPLY_ADD", wear, 1.1, 0.5)  # some stones are plain, some cloudy
    mottle = _math(nt, "MULTIPLY_ADD", _math(nt, "SUBTRACT", _range(nt, _noise(nt, grid, 5.5, 5.0, rough=0.6), 0.25, 0.75, *MOTTLE), 1.0),
                   mottle_k, 1.0)
    grain = _range(nt, _noise(nt, pos, 40.0, 3.0), 0.35, 0.65, *GRAIN)
    # scanned rock: each stone shows its own patch of the scan (shifted by the stone's random value),
    # so the pitting changes at every joint; side faces sample along the wall and up, tops in plan
    rock = _scan.planar(nt, ROCK, _lerp(nt, top, uw, along_x), _lerp(nt, top, vw, along_y), ROCK_TILE,
                        offset=_math(nt, "MULTIPLY", rand, 5.37))
    rock_lum = _math(nt, "DIVIDE", _scan.luminance(nt, rock["diff"]), ROCK_MEDIAN)
    grain = _math(nt, "MULTIPLY", grain, _math(nt, "MULTIPLY_ADD", _math(nt, "SUBTRACT", rock_lum, 1.0), ROCK_ALBEDO, 1.0))
    pit = _range(nt, rock["disp"], 0.55, 0.30)  # 1 in the deepest pits
    # the stone shades up from its recessed edge; there is no lit rim and no per-stone light and shade
    relief = _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, cavity), CAVITY_DARK))
    relief = _lerp(nt, plain, 1.0, relief)
    stone = _mix(nt, 1.0, fam, _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", mottle, grain),
                                     _math(nt, "MULTIPLY", gain, relief)), "MULTIPLY")
    stone = _mix(nt, 1.0, stone, COOL, "MULTIPLY")
    stone = _mix(nt, dressed, stone, _mix(nt, 1.0, stone, (DRESSED_GAIN,) * 3, "MULTIPLY"))
    rust = _math(nt, "MULTIPLY", _math(nt, "GREATER_THAN", pat["rust"], 1.0 - RUST_SHARE),
                 _math(nt, "MULTIPLY", _range(nt, _noise(nt, grid, 3.5, 3.0), 0.30, 0.65), _math(nt, "SUBTRACT", 1.0, pm)))
    stone = _mix(nt, _math(nt, "MULTIPLY", rust, plain), stone, _mix(nt, 1.0, stone, RUST, "MULTIPLY"))
    # arrises are chipped here and there: small irregular pale spots, not a rim
    chip_k = _math(nt, "MULTIPLY_ADD", wear, 1.2, 0.2)
    chip = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", rim, _range(nt, _noise(nt, pos, 30.0, 3.0), 0.60, 0.72)), chip_k)
    stone = _mix(nt, _math(nt, "MULTIPLY", chip, 0.35), stone, CHIP)
    stone = _mix(nt, 1.0, stone, zone, "MULTIPLY")
    stone = _mix(nt, 1.0, stone, _mix(nt, hue, HUE_COOL, HUE_WARM), "MULTIPLY")
    stone = _mix(nt, _math(nt, "MULTIPLY", dry, side), stone, _mix(nt, 1.0, stone, DRY_TINT, "MULTIPLY"))
    stone = _mix(nt, new, stone, _mix(nt, 1.0, stone, REPLACED_GAIN, "MULTIPLY"))
    stone = _mix(nt, jamb, stone, _mix(nt, 1.0, stone, (DRESSED_GAIN * 1.35,) * 3, "MULTIPLY"))  # jambs of a blocked opening
    # mortar: lime pointing close in value to the stone where it holds, darker where it has eroded;
    # dirt between flags
    lime = _mix(nt, pm, LIME, LIME_NEW)
    lime = _mix(nt, 1.0, lime, _range(nt, _noise(nt, grid, 3.0, 2.0), 0.3, 0.7, 0.9, 1.1), "MULTIPLY")
    joint_col = _mix(nt, top, _mix(nt, pat["erode"], lime, MORTAR), MUD)
    color = _mix(nt, joint, stone, joint_col)
    # repointing in a hard pale mortar, smeared over the stone edges
    smear = _math(nt, "MULTIPLY", _math(nt, "MAXIMUM", joint, _math(nt, "MULTIPLY", arris, 0.6)), repoint)
    color = _mix(nt, smear, color, REPOINT)
    # a corner broke off some stones: fresh stone in the break, a dark line along the edge
    corner = _math(nt, "MULTIPLY", pat["corner"], walls)
    color = _mix(nt, _math(nt, "MULTIPLY", corner, 0.45), color, CHIP)
    color = _mix(nt, _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", pat["corner_line"], walls), 0.32), color, (0.62, 0.62, 0.64), "MULTIPLY")

    # ---- damage: fallen stones, collapsed areas, broken faces, cracks ----
    dmg = pat["damage"]
    breach_noise = _noise(nt, _scaled(nt, wp, (0.30, 0.30, 0.30), (2.0, 13.0, 6.0)), 1.0, 2.0)
    breach = _range(nt, _math(nt, "MULTIPLY_ADD", _math(nt, "SUBTRACT", dmg, 0.5), BREACH[1], breach_noise), BREACH[0], BREACH[0] + 0.01)
    gone = _math(nt, "MULTIPLY", _math(nt, "MAXIMUM", _math(nt, "GREATER_THAN", dmg, 1.0 - MISSING), breach), wall_only)
    gone = _math(nt, "MULTIPLY", gone, _math(nt, "SUBTRACT", 1.0, pm))  # a repair is sound
    gone = _math(nt, "MULTIPLY", gone, _math(nt, "SUBTRACT", 1.0, thin))
    spall_zone = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", _math(nt, "GREATER_THAN", dmg, SPALLED[0]), _math(nt, "LESS_THAN", dmg, SPALLED[1])),
                       _math(nt, "SUBTRACT", 1.0, gone))
    spall_noise = _noise(nt, pos, 4.0, 1.0)
    spall = _math(nt, "MULTIPLY", _range(nt, spall_noise, 0.52, 0.56), _math(nt, "MULTIPLY", spall_zone, wall_only))
    core_col = _mix(nt, _range(nt, _noise(nt, pos, 9.0, 4.0), 0.3, 0.7), CORE_COLORS[0], CORE_COLORS[1])
    color = _mix(nt, gone, color, core_col)
    color = _mix(nt, _math(nt, "MULTIPLY", spall, 0.35), color, (1.20, 1.20, 1.18), "MULTIPLY")  # fresh stone is paler
    crack_region = _range(nt, _noise(nt, _scaled(nt, wp, (0.35, 0.35, 0.35), (5.0, 7.0, 1.0)), 1.0, 2.0), 0.62, 0.72)
    crack_n = _noise(nt, _scaled(nt, pos, (2.0, 2.0, 2.0), (4.0, 1.0, 9.0)), 1.0, 2.0, rough=0.5)
    crack = _math(nt, "MULTIPLY", _range(nt, _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", crack_n, 0.5)), CRACK_WIDTH, CRACK_WIDTH * 0.25, 0.0, 1.0),
                  _math(nt, "MULTIPLY", crack_region, wall_only))
    color = _mix(nt, _math(nt, "MULTIPLY", crack, 0.55), color, (0.45, 0.45, 0.48), "MULTIPLY")
    # putlog holes: a dark square, a little sky on its sill, a smudge of grime round it
    color = _mix(nt, _math(nt, "MULTIPLY", hole_lip, 0.35), color, (0.55, 0.57, 0.58), "MULTIPLY")
    color = _mix(nt, hole, color, _mix(nt, hole_low, HOLE, HOLE_SILL))

    # ---- water: only where something sheds it ----
    # how wet this stretch of wall is: streaks, runs and stains cluster where the coping leaks
    wet_zone = _noise(nt, _scaled(nt, wp, (0.28, 0.28, 0.30), (6.0, 3.0, 5.0)), 1.0, 2.0)
    # a wall box continues the track that starts on the parapet above it
    sill_dist = _math(nt, "MULTIPLY_ADD", tall, PARAPET, below)
    track_raw, spout_lime = _crenel_tracks(nt, gap_pos, sill_dist, seed)
    on_wall = _math(nt, "MULTIPLY", long_wall, side)
    tracks = _math(nt, "MULTIPLY", track_raw, on_wall)
    spout_lime = _math(nt, "MULTIPLY", spout_lime, _math(nt, "MULTIPLY", on_wall, tall))
    fine = _math(nt, "MULTIPLY", _fine_runs(nt, u, sill_dist, wet_zone), _math(nt, "MULTIPLY", side, _math(nt, "SUBTRACT", 1.0, small)))
    runoff = _max_of(nt, [_math(nt, "MULTIPLY", _plume(nt, wxy, wz, src, -1, *src[3:6]), src[6]) for src in _runoff_sources(plan)])
    runs = _math(nt, "MAXIMUM", _math(nt, "MAXIMUM", tracks, _math(nt, "MULTIPLY", fine, 0.38)), _math(nt, "MULTIPLY", runoff, side))
    color = _mix(nt, _math(nt, "MINIMUM", runs, 1.0), color, TRACK_TINT, "MULTIPLY")
    # lime leached from the pointing dries to pale strands inside the run
    lime_n = _range(nt, _noise(nt, _scaled(nt, wp, (9.0, 9.0, 0.6), (2.0, 5.0, 1.0)), 1.0, 2.0), 0.56, 0.72)
    color = _mix(nt, _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", _math(nt, "MINIMUM", runs, 1.0), lime_n), 0.6),
                 color, TRACK_LIME, "MULTIPLY")
    color = _mix(nt, _math(nt, "MULTIPLY", spout_lime, 0.55), color, SPOUT_LIME, "MULTIPLY")
    # wet band under the top edge, where the coping drips: patchy, heavier in the wet stretches
    top_patch = _range(nt, _noise(nt, _scaled(nt, wp, (0.9, 0.9, 1.0), (2.0, 4.0, 0.0)), 1.0, 2.0), 0.30, 0.65, 0.35, 1.0)
    top_band = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", _range(nt, below, 0.7, 0.0, 0.0, 0.30, smooth=True), top_patch), side)
    color = _mix(nt, top_band, color, WET_TINT, "MULTIPLY")
    # blotches of old grime in the wet stretches; long stains only below a track or a sill
    big_sv = _scaled(nt, wp, (0.5, 0.5, 0.22))
    stain = _math(nt, "MULTIPLY", _range(nt, _noise(nt, big_sv, 1.0, 4.0, rough=0.55), 0.52, 0.70, 0.0, 1.0, smooth=True),
                  _math(nt, "MULTIPLY", side, _range(nt, wet_zone, 0.35, 0.65, 0.3, 1.0)))
    track_halo = _math(nt, "MULTIPLY", _math(nt, "MINIMUM", runs, 1.0), 0.3)
    vert = _range(nt, _noise(nt, _scaled(nt, wp, (1.6, 1.6, 0.22)), 1.0, 3.0), 0.40, 0.60, 0.0, 1.0, smooth=True)
    stain = _math(nt, "MAXIMUM", stain, _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", vert, side), track_halo))
    stain = _math(nt, "MULTIPLY", stain, _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", _math(nt, "MAXIMUM", new, pm), 0.7)))
    color = _mix(nt, _math(nt, "MULTIPLY", stain, 0.8), color, STAIN_TINT, "MULTIPLY")
    # soot: a narrow fan that widens as it rises, and a fainter haze round it
    soot_src = _soot_sources(plan)
    soot = _max_of(nt, [_math(nt, "MULTIPLY", _plume(nt, wxy, wz, src, 1, 0.20, 0.24, src[3]), src[4]) for src in soot_src])
    haze = _max_of(nt, [_math(nt, "MULTIPLY", _plume(nt, wxy, wz, src, 1, 0.40, 0.32, src[3] * 1.5), src[4] * 0.35) for src in soot_src])
    soot = _math(nt, "MAXIMUM", soot, haze)
    color = _mix(nt, _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", soot, side), SOOT_MAX), color, (0.0, 0.0, 0.0))

    # ---- foot of the wall: contact soil, splash, rising damp, mud spatter, algae ----
    ragged = _math(nt, "SUBTRACT", _noise(nt, _scaled(nt, wp, (1.3, 1.3, 1.6)), 1.0, 3.0), 0.5)
    ragged_fine = _math(nt, "SUBTRACT", _noise(nt, _scaled(nt, wp, (5.0, 5.0, 6.0), (2.0, 7.0, 1.0)), 1.0, 3.0), 0.5)
    hg_r = _math(nt, "ADD", hg, _math(nt, "ADD", _math(nt, "MULTIPLY", ragged, 0.40), _math(nt, "MULTIPLY", ragged_fine, 0.14)))
    # dirt packed into the corner, with narrow tongues that run up where mud ran down the wall
    drip_n = _range(nt, _noise(nt, _scaled(nt, wp, (14.0, 14.0, 2.5), (1.0, 5.0, 2.0)), 1.0, 2.0), 0.50, 0.72)
    contact_top = _math(nt, "MULTIPLY_ADD", drip_n, 0.30, 0.10)
    contact = _math(nt, "MULTIPLY", _range(nt, hg_r, _math(nt, "SUBTRACT", contact_top, 0.05), _math(nt, "ADD", contact_top, 0.04), 1.0, 0.0, smooth=True), side)
    splash = _math(nt, "MULTIPLY", _range(nt, hg_r, 0.42, 0.78, 1.0, 0.0, smooth=True), side)
    rising = _math(nt, "MULTIPLY", _range(nt, _math(nt, "ADD", hg, _math(nt, "MULTIPLY", ragged, 1.4)), 0.6, 1.7, 1.0, 0.0, smooth=True), side)
    # the band's top edge wanders between about 0.4 and 1.2 m, follows single stones, and sends tongues upward
    band_n = _range(nt, _noise(nt, _scaled(nt, wp, (1.1, 1.1, 1.0), (3.0, 6.0, 0.0)), 1.0, 3.0), 0.30, 0.70, -1.0, 1.0)
    band_fine = _noise(nt, _scaled(nt, wp, (4.0, 4.0, 2.2), (1.0, 2.0, 5.0)), 1.0, 3.0)
    band_top = _math(nt, "ADD", _math(nt, "MULTIPLY_ADD", band_n, DAMP_BAND[1], DAMP_BAND[0]),
                     _math(nt, "MULTIPLY", _math(nt, "ADD", _math(nt, "SUBTRACT", band_fine, 0.5), _math(nt, "SUBTRACT", rand, 0.5)), 0.40))
    band = _math(nt, "MULTIPLY", _range(nt, hg, _math(nt, "SUBTRACT", band_top, 0.10), _math(nt, "ADD", band_top, 0.08), 1.0, 0.0, smooth=True), side)
    tongue_n = _range(nt, _noise(nt, _scaled(nt, wp, (2.8, 2.8, 0.30), (4.0, 1.0, 3.0)), 1.0, 3.0), 0.44, 0.62)
    tongue = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", tongue_n, _range(nt, hg, _math(nt, "ADD", band_top, 0.05),
                                                                         _math(nt, "ADD", band_top, 1.0), 1.0, 0.0, smooth=True)), side)
    damp = _math(nt, "MAXIMUM", band, _math(nt, "MULTIPLY", tongue, 0.8))
    damp_deep = _math(nt, "MULTIPLY", damp, _range(nt, hg, 1.0, 0.0, 0.55, 1.0, smooth=True))  # darkest at the ground
    # a faint pale tide mark where the damp stops, broken up
    tide = _math(nt, "MULTIPLY", _range(nt, _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", hg, band_top)), 0.0, 0.05, 1.0, 0.0, smooth=True), side)
    tide = _math(nt, "MULTIPLY", tide, _range(nt, _noise(nt, _scaled(nt, wp, (3.0, 3.0, 3.0), (5.0, 1.0, 2.0)), 1.0, 2.0), 0.45, 0.62))
    color = _mix(nt, _math(nt, "MULTIPLY", rising, 0.85), color, DAMP_TINT, "MULTIPLY")
    color = _mix(nt, _math(nt, "MULTIPLY", damp_deep, 0.85), color, BAND_TINT, "MULTIPLY")
    color = _mix(nt, _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", tide, band), 0.18), color, (0.70, 0.72, 0.72), "MULTIPLY")
    color = _mix(nt, splash, color, SPLASH_TINT, "MULTIPLY")
    # green-black algae on the lowest stones, in clusters a metre or so across
    foot_algae = _math(nt, "MULTIPLY", _range(nt, hg_r, _math(nt, "MULTIPLY_ADD", north, 0.7, 0.80), 0.08, 0.0, 1.0, smooth=True),
                       _math(nt, "MULTIPLY", side, aspect))
    algae_blot = _range(nt, _noise(nt, _scaled(nt, wp, (1.0, 1.0, 1.6), (5.0, 3.0, 2.0)), 1.0, 4.0, rough=0.6), 0.44, 0.60)
    foot_patch = _range(nt, _noise(nt, _scaled(nt, wp, (1.1, 1.1, 0.8), (9.0, 1.0, 3.0)), 1.0, 3.0), 0.36, 0.56, 0.35, 1.0)
    color = _mix(nt, _math(nt, "MULTIPLY", _math(nt, "MAXIMUM", splash, _math(nt, "MULTIPLY", rising, 0.5)), _math(nt, "MULTIPLY", foot_patch, 0.8)),
                 color, FOOT_TINT, "MULTIPLY")
    color = _mix(nt, _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", foot_algae, algae_blot), 0.5), color, ALGAE_BLACK)
    plinth_damp = _math(nt, "MULTIPLY", plinth, _range(nt, _noise(nt, _scaled(nt, wp, (1.4, 1.4, 1.0), (1.0, 4.0, 7.0)), 1.0, 4.0), 0.3, 0.6, 0.4, 1.0))
    color = _mix(nt, plinth_damp, color, PLINTH_TINT, "MULTIPLY")
    # mud thrown up from the ground: specks that get sparser with height, a few blotches, short
    # upward flicks, and mud packed into the joints
    speck_cut = _math(nt, "MULTIPLY_ADD", _range(nt, hg_r, 0.0, 0.9), 0.10, 0.52)
    specks = _range(nt, _noise(nt, pos, 55.0, 0.0), speck_cut, _math(nt, "ADD", speck_cut, 0.05))
    blots = _range(nt, _noise(nt, pos, 9.0, 2.0), 0.60, 0.68)
    flicks = _range(nt, _noise(nt, _scaled(nt, pos, (20.0, 20.0, 5.0)), 1.0, 1.0), 0.58, 0.68)
    spatter_zone = _math(nt, "MULTIPLY", _range(nt, hg_r, 1.00, 0.02, 0.0, 1.0, smooth=True), side)
    blot_zone = _math(nt, "MULTIPLY", _range(nt, hg_r, 0.50, 0.05, 0.0, 1.0, smooth=True), side)
    spatter = _math(nt, "MAXIMUM", _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", specks, spatter_zone), _math(nt, "MULTIPLY", flicks, _math(nt, "MULTIPLY", blot_zone, 0.8))),
                    _math(nt, "MULTIPLY", blots, _math(nt, "MULTIPLY", blot_zone, 0.8)))
    color = _mix(nt, _math(nt, "MULTIPLY", spatter, 0.85), color, MUD_SPLASH)
    mud_joint = _math(nt, "MULTIPLY", joint, _range(nt, hg_r, 1.2, 0.1, 0.0, 1.0, smooth=True))
    color = _mix(nt, _math(nt, "MULTIPLY", mud_joint, _math(nt, "MULTIPLY", side, 0.8)), color, MUD)
    color = _mix(nt, _math(nt, "MULTIPLY", contact, _range(nt, _noise(nt, _scaled(nt, wp, (3.0, 3.0, 8.0)), 1.0, 3.0), 0.25, 0.55, 0.70, 1.0)), color, SOIL)

    # ---- growth: algae on faces turned away from the moon, green-black joints, moss ----
    # tops hold water and moss where they meet a parapet or a step: within 35 cm of the slab edge
    edge_dist = _math(nt, "MINIMUM", _math(nt, "SUBTRACT", _half_extent(nt, x, gx), _math(nt, "ABSOLUTE", x)),
                      _math(nt, "SUBTRACT", _half_extent(nt, y, gy), _math(nt, "ABSOLUTE", y)))
    corner_zone = _math(nt, "MULTIPLY", _range(nt, edge_dist, 0.05, 0.40, 1.0, 0.0, smooth=True), _math(nt, "SUBTRACT", 1.0, small))
    algae_sv = _scaled(nt, wp, (0.7, 0.7, 0.45), (3.0, 9.0, 2.0))
    algae = _math(nt, "MULTIPLY", _range(nt, _noise(nt, algae_sv, 1.0, 4.0), 0.42, 0.60, 0.0, 1.0, smooth=True),
                  _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", shade, side), _range(nt, hg, 7.0, 0.5, 0.2, 1.0)))
    streak_algae = _math(nt, "MULTIPLY", _math(nt, "MINIMUM", runs, 1.0),
                         _range(nt, _noise(nt, _scaled(nt, wp, (1.3, 1.3, 0.5), (7.0, 2.0, 5.0)), 1.0, 3.0), 0.38, 0.60, 0.25, 1.0))
    color = _mix(nt, _math(nt, "MULTIPLY", algae, 0.55), color, ALGAE_TINT, "MULTIPLY")
    color = _mix(nt, _math(nt, "MULTIPLY", streak_algae, 0.5), color, ALGAE_TINT, "MULTIPLY")
    cover_sv = _noise(nt, pos, 2.2, 5.0, rough=0.6)
    mpatch = _range(nt, cover_sv, 0.54, 0.72)
    fuzz = _range(nt, _noise(nt, pos, 16.0, 3.0), 0.30, 0.70)
    in_joint = _math(nt, "MAXIMUM", joint, _math(nt, "MULTIPLY", rim, 0.5))
    foot_moss = _math(nt, "MULTIPLY", _range(nt, hg_r, 0.30, 0.03, 0.0, 1.0, smooth=True),
                      _range(nt, _noise(nt, _scaled(nt, wp, (2.5, 2.5, 4.0), (3.0, 8.0, 1.0)), 1.0, 3.0), 0.36, 0.56, 0.2, 1.0))
    cover = _math(nt, "MAXIMUM", _math(nt, "MAXIMUM", _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", splash, _math(nt, "MULTIPLY_ADD", shade, 0.20, 0.17)),
                                                            _math(nt, "MULTIPLY", plinth, 0.25)),
                                        _math(nt, "MULTIPLY", algae, 0.35)),
                  _math(nt, "MULTIPLY", foot_moss, _math(nt, "MULTIPLY", side, 0.8)))
    cover = _math(nt, "MAXIMUM", cover, _math(nt, "MULTIPLY", mpatch, 0.6))
    cover = _math(nt, "MULTIPLY", cover, _lerp(nt, side, 1.0, aspect))
    cover = _math(nt, "MAXIMUM", cover, _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", top, corner_zone), _range(nt, cover_sv, 0.25, 0.45)))
    clump = _range(nt, _noise(nt, pos, 5.0, 3.0), 0.42, 0.62, 0.3, 1.0)  # moss grows in clumps, not as a speckle
    moss = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", cover, clump), _math(nt, "MULTIPLY_ADD", in_joint, 0.8, _math(nt, "MULTIPLY", fuzz, 0.35)), clamp=True)
    moss = _range(nt, moss, 0.05, 0.45, 0.0, 1.0, smooth=True)
    moss_col = _mix(nt, _range(nt, _noise(nt, pos, 7.0, 2.0), 0.3, 0.7), MOSS, MOSS_DRY)
    # green-black algae fills the joints low on the wall and under every run
    low_zone = _math(nt, "MULTIPLY", _range(nt, hg, 1.3, 0.1, 0.0, 0.8, smooth=True),
                     _range(nt, _noise(nt, _scaled(nt, wp, (1.3, 1.3, 1.0), (6.0, 2.0, 8.0)), 1.0, 3.0), 0.34, 0.58, 0.15, 1.0))
    joint_zone = _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", low_zone, aspect), _math(nt, "MULTIPLY", _math(nt, "MINIMUM", runs, 1.0), 0.25))
    joint_zone = _math(nt, "MULTIPLY", joint_zone, _math(nt, "MULTIPLY", side, _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", pm, 0.8))))
    joint_algae = _range(nt, _math(nt, "MULTIPLY", in_joint, joint_zone), 0.12, 0.60, 0.0, 1.0, smooth=True)
    color = _mix(nt, _math(nt, "MULTIPLY", joint_algae, 0.9), color, ALGAE_BLACK)
    moss = _math(nt, "MAXIMUM", moss, _math(nt, "MULTIPLY", joint_algae, _range(nt, fuzz, 0.40, 0.70, 0.0, 0.7)))
    # dirt collects where a top meets a parapet or a step
    color = _mix(nt, _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", top, corner_zone), 0.45), color, MUD)
    color = _mix(nt, moss, color, moss_col)

    # ---- wetness: rain-facing and high stone is darker, tops darkest, small stones wetter ----
    wet_n = _noise(nt, _scaled(nt, wp, (0.35, 0.35, 0.5), (4.0, 2.0, 0.0)), 1.0, 3.0)
    wet = _math(nt, "MULTIPLY", _math(nt, "ADD", _math(nt, "MULTIPLY_ADD", windward, 0.7, 0.10), _math(nt, "MULTIPLY", runs, 0.4)),
                _range(nt, wet_n, 0.25, 0.60, 0.7, 1.0))
    wet = _math(nt, "MULTIPLY", wet, _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", dry, 0.6)))
    wet = _math(nt, "MAXIMUM", wet, _math(nt, "MAXIMUM", _math(nt, "MAXIMUM", splash, _math(nt, "MULTIPLY", damp, 0.8)), _math(nt, "MULTIPLY", small, 0.4)), clamp=True)
    color = _mix(nt, _math(nt, "MULTIPLY", wet, side), color, WET_TINT, "MULTIPLY")
    color = _mix(nt, _math(nt, "MULTIPLY", small, wall_only), color, SMALL_TINT, "MULTIPLY")
    top_wet = _range(nt, _noise(nt, pos, 0.9, 3.0), 0.25, 0.50, 0.6, 1.0, smooth=True)  # some flags have dried a little
    color = _mix(nt, _math(nt, "MULTIPLY", topup, top_wet), color, TOP_TINT, "MULTIPLY")
    # exposed tops carry grime, dark lichen crusts and grit: they are never one flat tone
    top_grime = _range(nt, _noise(nt, _scaled(nt, wp, (1.0, 1.0, 1.0), (7.0, 2.0, 3.0)), 2.6, 4.0, rough=0.6), 0.40, 0.68, 0.0, 0.75, smooth=True)
    color = _mix(nt, _math(nt, "MULTIPLY", topup, top_grime), color, TOP_GRIME, "MULTIPLY")
    crust = _range(nt, _noise(nt, _scaled(nt, wp, (1.0, 1.0, 1.0), (1.0, 8.0, 4.0)), 9.0, 3.0, rough=0.65), 0.58, 0.66)
    crust = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", crust, topup), _range(nt, _noise(nt, wp, 1.4, 2.0), 0.40, 0.62))
    color = _mix(nt, _math(nt, "MULTIPLY", crust, 0.8), color, LICHEN_BLACK)
    # puddles stand in the low parts of a top, deepest in the dished middle of the slabs that have sunk
    pud_sv = _scaled(nt, wp, (0.8, 0.8, 0.8), (5.0, 1.0, 4.0))
    puddle = _range(nt, _math(nt, "MULTIPLY_ADD", f_worn, 0.18, _noise(nt, pud_sv, 1.0, 3.0)), 0.575, 0.615, 0.0, 1.0, smooth=True)
    puddle = _math(nt, "MULTIPLY", puddle, _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", up, plain), flag_on))
    color = _mix(nt, _math(nt, "MULTIPLY", puddle, 0.35), color, (0.8, 0.86, 0.95), "MULTIPLY")
    # stair treads worn hollow along the walking line, most at the nosing: clean, polished, wet
    worn = _math(nt, "MULTIPLY", _stair_wear(nt, wx, wy, wz, plan), up)
    color = _mix(nt, _math(nt, "MULTIPLY", worn, 0.85), color, STAIR_POLISH, "MULTIPLY")
    color = _mix(nt, 1.0, color, ALBEDO, "MULTIPLY")
    nt.links.new(color, bsdf.inputs["Base Color"])

    # ---- surface: glossy where wet, rough in dry joints, moss and broken faces ----
    # stones differ in how much water they hold: smoother ones shine, rougher ones stay matt
    sheen = _math(nt, "MULTIPLY_ADD", wear, 0.6, 0.7)
    gloss = _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", wet, 0.8), sheen), _math(nt, "MULTIPLY", topup, top_wet))
    rough = _range(nt, gloss, 0.0, 1.0, 0.78, 0.36)
    rough = _math(nt, "MULTIPLY_ADD", _math(nt, "SUBTRACT", rock["rough"], 0.51), 1.5, rough)  # scanned roughness
    rough = _lerp(nt, _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", pit, wet), 0.5), rough, 0.15)  # water stands in the pits
    top_rough = _range(nt, _noise(nt, _scaled(nt, wp, (1.0, 1.0, 1.0), (3.0, 3.0, 9.0)), 3.5, 3.0), 0.30, 0.70, 0.18, 0.50)
    rough = _lerp(nt, topup, rough, _math(nt, "ADD", _range(nt, top_wet, 0.6, 1.0, 0.18, 0.0), top_rough))
    rough = _lerp(nt, _math(nt, "MULTIPLY", topup, _math(nt, "MAXIMUM", crust, top_grime)), rough, 0.7)
    rough = _lerp(nt, joint, rough, 0.85)
    rough = _lerp(nt, gone, rough, 1.0)
    rough = _lerp(nt, moss, rough, 0.9)
    rough = _lerp(nt, puddle, rough, 0.06)
    rough = _lerp(nt, worn, rough, 0.10)
    rough = _lerp(nt, hole, rough, 1.0)
    rough = _lerp(nt, _math(nt, "MULTIPLY", soot, side), rough, 0.92)  # soot is dry and matt
    nt.links.new(rough, bsdf.inputs["Roughness"])
    # a thin water film reflects the sky at grazing angles; it is stronger on tops and where rain runs
    # under the film on a top the stone itself reflects little: the water surface does the work
    nt.links.new(_lerp(nt, topup, 0.22, 0.12), bsdf.inputs["Specular IOR Level"])
    top_film = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY_ADD", top_wet, 0.35, 0.08),
                     _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", _math(nt, "MAXIMUM", crust, top_grime), 0.8)))
    film = _lerp(nt, topup, _math(nt, "MULTIPLY_ADD", gloss, 0.30, 0.08), top_film)
    film = _math(nt, "MULTIPLY", film, _math(nt, "SUBTRACT", 1.0, _math(nt, "MAXIMUM", _math(nt, "MAXIMUM", moss, joint), _math(nt, "MAXIMUM", hole, _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", plinth, 0.6), _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", soot, side), 0.9))))))
    nt.links.new(film, bsdf.inputs["Coat Weight"])
    nt.links.new(_lerp(nt, topup, 0.12, _math(nt, "MULTIPLY", top_rough, 0.6)), bsdf.inputs["Coat Roughness"])
    bsdf.inputs["Coat IOR"].default_value = 1.33  # water

    # ---- relief: nearly flat faces, flush or slightly recessed joints, dished flags, fuzzy moss, grain ----
    grain_h = _noise(nt, pos, 17.0, 5.0, rough=0.62)
    grain_k = _math(nt, "MULTIPLY_ADD", wear2, 0.30, 0.22)  # faces are smooth or pitted
    rustic = _math(nt, "MULTIPLY", _noise(nt, pos, 6.0, 3.0), plinth)  # coarse, rusticated face
    face = pick(pat["face"], fl["face"])
    dome_k = _math(nt, "MULTIPLY_ADD", wear2, 0.30, 0.15)  # crisp stones are flat, worn ones are a little rounded
    form = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", face, dome_k), plain)
    form = _math(nt, "SUBTRACT", form, _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", fl["bowl"], flag_on), _math(nt, "MULTIPLY_ADD", wear2, 0.30, 0.10)))  # dished slab
    # every stone leans a very little differently
    tilt = _math(nt, "MULTIPLY", _math(nt, "ADD", _math(nt, "MULTIPLY", pat["tilt_u"], _math(nt, "SUBTRACT", pat["lx"], 0.5)),
                                       _math(nt, "MULTIPLY", pat["tilt_v"], _math(nt, "SUBTRACT", pat["vfrac"], 0.5))),
                 _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, joint), _math(nt, "MULTIPLY", walls, 0.40)))
    height = _math(nt, "ADD", _math(nt, "ADD", _math(nt, "MULTIPLY_ADD", grain_h, grain_k, _math(nt, "ADD", form, _math(nt, "MULTIPLY", rustic, 0.4))), tilt),
                   _math(nt, "MULTIPLY", moss, 0.35))
    # joints sit a few mm below the face; eroded ones are much deeper
    depth = _math(nt, "MULTIPLY", joint, _math(nt, "MULTIPLY_ADD", pat["erode"], 0.80, 0.30))
    height = _math(nt, "SUBTRACT", height, depth)
    height = _math(nt, "MULTIPLY", height, _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", puddle, 0.8)))  # still water is flat
    height = _math(nt, "SUBTRACT", height, _math(nt, "ADD", _math(nt, "MULTIPLY", gone, 2.0),
                                                  _math(nt, "ADD", _math(nt, "MULTIPLY", spall, 1.3),
                                                        _math(nt, "ADD", _math(nt, "MULTIPLY", crack, 0.75),
                                                              _math(nt, "ADD", _math(nt, "MULTIPLY", corner, 1.5),
                                                                    _math(nt, "MULTIPLY", hole, 2.4))))))  # missing and broken stone sits low
    height = _math(nt, "SUBTRACT", height, _math(nt, "MULTIPLY", worn, 1.6))  # the hollow of a worn tread
    # scanned pitting on sound stone faces; joints, puddles and moss keep their own surface
    sound = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, joint), _math(nt, "SUBTRACT", 1.0, _math(nt, "MAXIMUM", puddle, moss)))
    height = _math(nt, "ADD", height, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", rock["disp"], 0.59), _math(nt, "MULTIPLY", sound, ROCK_RELIEF)))
    # scanned normal map in the frame of the scan: along the wall (or plan x), up (or plan y), out of the face
    t_side = _node(nt, "ShaderNodeMix", {0: ax, 4: axis_x, 5: axis_y}, data_type="VECTOR").outputs[1]
    t_ax = _node(nt, "ShaderNodeMix", {0: top, 4: t_side, 5: axis_x}, data_type="VECTOR").outputs[1]
    b_ax = _node(nt, "ShaderNodeMix", {0: top, 4: (0.0, 0.0, 1.0), 5: axis_y}, data_type="VECTOR").outputs[1]
    n_scan = _scan.tangent_normal(nt, rock["nor_gl"], t_ax, b_ax, geo.outputs["Normal"])
    n_scan = _node(nt, "ShaderNodeVectorMath", {0: n_scan}, operation="NORMALIZE").outputs[0]
    n_mix = _node(nt, "ShaderNodeMix", {0: _math(nt, "MULTIPLY", sound, ROCK_NORMAL), 4: geo.outputs["Normal"], 5: n_scan},
                  data_type="VECTOR").outputs[1]
    n_mix = _node(nt, "ShaderNodeVectorMath", {0: n_mix}, operation="NORMALIZE").outputs[0]
    bump = _node(nt, "ShaderNodeBump", {"Height": height, "Strength": 1.0, "Distance": BUMP, "Normal": n_mix})
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

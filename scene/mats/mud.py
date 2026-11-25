"""Trodden mud outside the walls: lumpy dark earth, dead grass, standing water, cart ruts.

Meshes inside the courtyard (the mud banked against the walls, the wet gutter at their feet, see
assets/ground_dressing.py) use the same material through two vertex attributes. `dress` is 1 on mud
that wears the colors of the courtyard floor, without standing water or grass; `gutter` is 1 on a
ribbon of standing water. Both are 0 on the terrain, which looks as it always did.

One height field drives everything. Water is rare: it stands only in the
ruts of a cart track that runs north-south and in the lowest hollows, so most
of the ground is damp trodden earth, dead grass and stones. Puddles look like
the ones in cobble_wet.py: a dark base, a mirror with the same ripples and rain
rings, a thin second glossy water layer, and a wet rim of mud around them.

Object coordinates are meters; the terrain mesh sits at the origin, so they
are world coordinates.
"""

from mats.cobble_wet import MUD_DARK as YARD_MUD_DARK
from mats.cobble_wet import MUD_LIGHT as YARD_MUD_LIGHT
from mats.cobble_wet import TRACK_MUD as YARD_TRACK_MUD
from mats.cobble_wet import _math, _mix, _mix_vec, _node, _noise, _range, _vec, _xyz, water_ripples

LUMP_SCALE = 0.32  # big lumps are about 1 / this meters across
PUDDLE_SCALE = 0.11  # standing water pools are about 1 / this meters across
PUDDLE_LEVEL = 0.61  # raise for fewer pools
GRASS_SCALE = 0.45  # dead grass patches are about 1 / this meters across
GRASS_LEVEL = 0.42  # raise for less grass
TRACK_X = 17.0  # center of the cart track, meters east
TRACK_WANDER = 4.0  # how far the track meanders, meters
RUT_GAUGE = 1.4  # distance between the two ruts
RUT_WIDTH = 0.16  # half-width of a rut
RELIEF = 0.2  # meters of bump height for the lumps
PEBBLES_PER_M = 4.0  # stone cells per meter
PEBBLE_COVER = 0.14  # share of cells holding a stone
PEBBLE_COLOR = (0.085, 0.080, 0.070)

MUD_DARK = (0.042, 0.031, 0.016)
MUD_LIGHT = (0.118, 0.086, 0.045)  # the same olive-brown as the mud tracked into the courtyard
GRASS_DARK = (0.090, 0.070, 0.028)
GRASS_LIGHT = (0.220, 0.170, 0.070)  # bleached straw
WATER_TINT = (0.30, 0.28, 0.23)  # earth seen through the water
WATER_COLOR = (0.019, 0.021, 0.023)  # silt suspended in the water: nearly black, the mirror does the rest
TURBIDITY = 0.6  # how much of the water color is silt rather than the earth below
YARD_ROUGH, YARD_SPECULAR = 0.62, 0.30  # courtyard mud is matte, like the mud of the floor
ROUGH_DRY, ROUGH_WET, ROUGH_WATER = 0.74, 0.42, 0.06  # in steady rain even the higher ground is damp
ROUGH_SPREAD = 0.14  # patches of the ground drain and dry faster than their neighbors
WATER_SPECULAR = 1.0  # Specular IOR Level in standing water (0.5 is the neutral default)
DAMP_SPECULAR = 0.65  # Specular IOR Level of wet ground
WATER_COAT = 0.3  # weight of the water film's own reflection over the silt; low, since the haze behind the ruts is bright


def build(mat, nt, bsdf):
    pos = _node(nt, "ShaderNodeTexCoord").outputs["Object"]
    x, y, _ = _xyz(nt, pos)

    # ---- ground height: broad lumps, small clods, grit ----
    lumps = _noise(nt, pos, LUMP_SCALE, 5.0, "2D", rough=0.55, distortion=0.2)
    clods = _noise(nt, pos, 3.2, 4.0, "2D")
    grit = _noise(nt, pos, 30.0, 3.0, "2D")
    height = _math(nt, "ADD", _math(nt, "MULTIPLY_ADD", lumps, 0.72, _math(nt, "MULTIPLY", clods, 0.22)),
                   _math(nt, "MULTIPLY", grit, 0.06))

    # ---- stones: a share of Voronoi cells hold a pebble of random size ----
    cell = _node(nt, "ShaderNodeTexVoronoi", {"Vector": pos, "Scale": PEBBLES_PER_M, "Randomness": 1.0},
                 voronoi_dimensions="2D", feature="F1")
    rnd = _node(nt, "ShaderNodeSeparateColor", {"Color": cell.outputs["Color"]})
    radius = _math(nt, "MULTIPLY_ADD", rnd.outputs["Green"], 0.35, 0.15)  # cell units
    pebble = _math(nt, "MULTIPLY", _range(nt, rnd.outputs["Red"], 1.0 - PEBBLE_COVER - 0.02, 1.0 - PEBBLE_COVER),
                   _range(nt, cell.outputs["Distance"], _math(nt, "MULTIPLY", radius, 0.7), radius, 1.0, 0.0, smooth=True))
    height = _math(nt, "MULTIPLY_ADD", pebble, 0.3, height)

    # ---- cart ruts: two channels along y, following a slow wander ----
    wander = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, _math_to_vec(nt, y, 0.04), 1.0, 2.0, "2D"), 0.5),
                   TRACK_WANDER * 2)
    across = _math(nt, "SUBTRACT", _math(nt, "SUBTRACT", x, TRACK_X), wander)
    offset = _math(nt, "SUBTRACT", _math(nt, "ABSOLUTE", across), RUT_GAUGE / 2)
    ruts = _range(nt, _math(nt, "ABSOLUTE", offset), RUT_WIDTH * 0.5, RUT_WIDTH * 1.6, 1.0, 0.0, smooth=True)
    ruts = _math(nt, "MULTIPLY", ruts, _range(nt, _noise(nt, _math_to_vec(nt, y, 0.15), 1.0, 2.0, "2D"), 0.3, 0.6))
    height = _math(nt, "SUBTRACT", height, _math(nt, "MULTIPLY", ruts, 0.35))

    # ---- standing water: pools plus low ground ----
    pools = _noise(nt, pos, PUDDLE_SCALE, 4.0, "2D", rough=0.55, distortion=0.3)
    wetness = _math(nt, "SUBTRACT", _math(nt, "MULTIPLY_ADD", pools, 0.5, 0.25),
                    _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", height, 0.5), 0.5))
    water = _range(nt, wetness, PUDDLE_LEVEL - 0.03, PUDDLE_LEVEL + 0.03, smooth=True)
    water = _math(nt, "MAXIMUM", water, _math(nt, "MULTIPLY", ruts, _range(nt, pools, 0.52, 0.62)))
    wet = _range(nt, wetness, PUDDLE_LEVEL - 0.10, PUDDLE_LEVEL, smooth=True)  # glossy trodden mud around pools
    dress = _node(nt, "ShaderNodeAttribute", attribute_name="dress", attribute_type="GEOMETRY").outputs["Fac"]
    gutter = _node(nt, "ShaderNodeAttribute", attribute_name="gutter", attribute_type="GEOMETRY").outputs["Fac"]
    not_dress = _math(nt, "SUBTRACT", 1.0, dress)
    water = _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", water, not_dress), gutter)
    wet = _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", wet, not_dress), gutter)

    # ---- color: mud, dead grass on the higher dry ground ----
    tone = _node(nt, "ShaderNodeValToRGB", {"Fac": _math(nt, "ADD", _math(nt, "MULTIPLY", clods, 0.6),
                                                          _math(nt, "MULTIPLY", grit, 0.4))})
    tone.color_ramp.elements[0].color = (*MUD_DARK, 1)
    tone.color_ramp.elements[1].color = (*MUD_LIGHT, 1)
    blades = _node(nt, "ShaderNodeValToRGB", {"Fac": _noise(nt, pos, 70.0, 3.0, "2D", rough=0.7)})
    blades.color_ramp.elements[0].color = (*GRASS_DARK, 1)
    blades.color_ramp.elements[1].color = (*GRASS_LIGHT, 1)
    grass_field = _noise(nt, pos, GRASS_SCALE, 4.0, "2D", distortion=0.2)
    grass = _math(nt, "MULTIPLY", _range(nt, grass_field, GRASS_LEVEL - 0.05, GRASS_LEVEL + 0.08, smooth=True),
                  _math(nt, "MULTIPLY", _range(nt, wetness, PUDDLE_LEVEL - 0.10, PUDDLE_LEVEL - 0.30), 0.85))
    grass = _math(nt, "MULTIPLY", grass, _range(nt, grit, 0.35, 0.6, 0.5, 1.0))
    grass = _math(nt, "MULTIPLY", grass, not_dress)
    color = _mix(nt, grass, tone.outputs["Color"], blades.outputs["Color"])
    pebble_color = _mix(nt, 1.0, PEBBLE_COLOR, _range(nt, grit, 0.3, 0.7, 0.6, 1.3), "MULTIPLY")
    color = _mix(nt, pebble, color, pebble_color)
    yard_tone = _node(nt, "ShaderNodeValToRGB", {"Fac": _math(nt, "ADD", _math(nt, "MULTIPLY", _noise(nt, pos, 2.2, 3.0, "2D"), 0.5),
                                                              _math(nt, "MULTIPLY", _noise(nt, pos, 10.0, 4.0, "2D"), 0.5))})
    yard_tone.color_ramp.elements[0].color = (*YARD_MUD_DARK, 1)
    yard_tone.color_ramp.elements[1].color = (*YARD_MUD_LIGHT, 1)
    color = _mix(nt, dress, color, _mix(nt, 0.4, yard_tone.outputs["Color"], YARD_TRACK_MUD))
    color = _mix(nt, wet, color, (0.7, 0.68, 0.62), "MULTIPLY")
    submerged = _mix(nt, 1.0, color, WATER_TINT, "MULTIPLY")
    color = _mix(nt, water, color, _mix(nt, TURBIDITY, submerged, WATER_COLOR))
    nt.links.new(color, bsdf.inputs["Base Color"])

    patches = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, pos, 2.4, 3.0, "2D"), 0.5), ROUGH_SPREAD * 2)
    rough = _math(nt, "ADD", _range(nt, wet, 0.0, 1.0, ROUGH_DRY, ROUGH_WET), _math(nt, "MULTIPLY", patches, _math(nt, "SUBTRACT", 1.0, water)))
    rough = _range(nt, dress, 0.0, 1.0, rough, YARD_ROUGH)
    rough = _range(nt, water, 0.0, 1.0, rough, ROUGH_WATER)
    nt.links.new(rough, bsdf.inputs["Roughness"])
    spec = _range(nt, dress, 0.0, 1.0, DAMP_SPECULAR, YARD_SPECULAR)
    nt.links.new(_range(nt, water, 0.0, 1.0, spec, WATER_SPECULAR), bsdf.inputs["Specular IOR Level"])

    # ---- relief: lumpy ground, flat rippled water ----
    ground = _node(nt, "ShaderNodeBump", {"Height": height, "Distance": RELIEF,
                                           "Strength": _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", dress, 0.85))}).outputs["Normal"]
    ripples = _node(nt, "ShaderNodeBump", {"Height": water_ripples(nt, pos), "Distance": 0.03,
                                            "Strength": 1.0}).outputs["Normal"]
    normal = _vec(nt, "NORMALIZE", _mix_vec(nt, _range(nt, water, 0.2, 0.8, smooth=True), ground, ripples))
    nt.links.new(normal, bsdf.inputs["Normal"])

    nt.links.new(_math(nt, "MULTIPLY", water, WATER_COAT), bsdf.inputs["Coat Weight"])
    bsdf.inputs["Coat Roughness"].default_value = ROUGH_WATER
    bsdf.inputs["Coat IOR"].default_value = 1.4
    nt.links.new(normal, bsdf.inputs["Coat Normal"])


def _math_to_vec(nt, value, scale):
    """Vector (value * scale, 0, 0): a 1D coordinate for a noise that varies along one axis only."""
    return _node(nt, "ShaderNodeCombineXYZ", {"X": _math(nt, "MULTIPLY", value, scale)}).outputs[0]

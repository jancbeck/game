"""The map of the march, painted on a board: contour lines, the river, the road and the garrison.

Drawn procedurally on the UV square of a flat quad (u east, v north on the board): parchment
paint over grey boards, brown contour lines from a noise height, a blue-grey river, a muddy red
road with pin holes pricked along it, a black tower where road and river nearly cross, a dark
border. The south (low v) is rubbed pale, where the thumbs of the commander have been.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood as w  # noqa: E402


def band(nt, value, width, soft=0.002):
    """1 where |value| < width, with a soft edge."""
    a = w.math(nt, "ABSOLUTE", value)
    return w.map_range(nt, a, width, width + soft, 1.0, 0.0)


def build(mat, nt, bsdf):
    uv = nt.nodes.new("ShaderNodeTexCoord").outputs["UV"]
    u, v, _ = w.sep(nt, uv)
    grain = w.noise(nt, uv, 9.0, 5.0, 0.6)
    paint = w.ramp(nt, grain, [(0.3, (0.17, 0.145, 0.10)), (0.7, (0.30, 0.255, 0.18))])
    # contour lines: iso-lines of a noise height
    height = w.noise(nt, uv, 2.6, 4.0, 0.55)
    iso = w.math(nt, "PINGPONG", w.math(nt, "MULTIPLY", height, 14.0), 1.0)
    contour = w.map_range(nt, iso, 0.07, 0.13, 1.0, 0.0)
    worn = w.map_range(nt, v, 0.0, 0.35, 0.25, 1.0)
    colour = w.mix_color(nt, w.math(nt, "MULTIPLY", contour, w.math(nt, "MULTIPLY", worn, 0.55)), paint, (0.07, 0.05, 0.035))
    # river: x = 0.56 + 0.09 sin(9 v) + 0.03 (noise - 0.5)
    wob = w.math(nt, "MULTIPLY", w.noise(nt, w.combine(nt, v, 3.1, 0.0), 3.0, 2.0), 0.06)
    river_x = w.math(nt, "ADD", w.math(nt, "ADD", 0.53, w.math(nt, "MULTIPLY", w.math(nt, "SINE", w.math(nt, "MULTIPLY", v, 9.0)), 0.09)), wob)
    river = band(nt, w.math(nt, "SUBTRACT", u, river_x), 0.013, 0.004)
    colour = w.mix_color(nt, w.math(nt, "MULTIPLY", river, worn), colour, (0.05, 0.085, 0.12))
    # road: v = 0.12 + 0.72 u + 0.035 sin(15 u)
    road_v = w.math(nt, "ADD", w.math(nt, "ADD", 0.12, w.math(nt, "MULTIPLY", u, 0.72)),
                    w.math(nt, "MULTIPLY", w.math(nt, "SINE", w.math(nt, "MULTIPLY", u, 15.0)), 0.035))
    road_d = w.math(nt, "SUBTRACT", v, road_v)
    road = band(nt, road_d, 0.010, 0.003)
    colour = w.mix_color(nt, w.math(nt, "MULTIPLY", road, worn), colour, (0.26, 0.035, 0.022))
    # pin holes along the road
    dots = w.map_range(nt, w.math(nt, "PINGPONG", w.math(nt, "MULTIPLY", u, 31.0), 1.0), 0.0, 0.18, 1.0, 0.0)
    pins = w.math(nt, "MULTIPLY", band(nt, road_d, 0.009, 0.002), dots)
    colour = w.mix_color(nt, pins, colour, (0.01, 0.008, 0.006))
    # the garrison: a small black tower on the road, east of the river
    du = w.math(nt, "SUBTRACT", u, 0.585)
    dv = w.math(nt, "SUBTRACT", v, w.math(nt, "ADD", 0.12 + 0.72 * 0.585, w.math(nt, "MULTIPLY", w.math(nt, "SINE", 15.0 * 0.585), 0.035)))
    tower = w.math(nt, "MULTIPLY", band(nt, du, 0.022, 0.003), band(nt, w.math(nt, "SUBTRACT", dv, 0.025), 0.034, 0.003))
    colour = w.mix_color(nt, tower, colour, (0.012, 0.01, 0.01))
    # border
    edge = w.math(nt, "MAXIMUM", w.math(nt, "ABSOLUTE", w.math(nt, "SUBTRACT", u, 0.5)),
                  w.math(nt, "ABSOLUTE", w.math(nt, "SUBTRACT", v, 0.5)))
    border = w.map_range(nt, w.math(nt, "ABSOLUTE", w.math(nt, "SUBTRACT", edge, 0.455)), 0.012, 0.016, 1.0, 0.0)
    colour = w.mix_color(nt, border, colour, (0.04, 0.03, 0.02))
    nt.links.new(colour, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.78
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.15
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(grain, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

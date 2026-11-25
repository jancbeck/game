"""Scrubbed flagstones of a kitchen floor: irregular grey-brown slabs in rows, dark narrow joints.

The floor is dry and kept clean, so nothing on it is wet or glossy. Each slab has its own tone, stands
at its own height, and shows its own patch of a scanned rock (pitting and grain, as the walls do);
the joints are narrow, dirty and recessed. Slabs are worn smoother (and a little paler) in patches
where feet go, and dusted with soot near the hearth. Roughness stays between 0.6 and 0.95
everywhere, so firelight pools on the floor as a soft glow and never as a highlight.

Texture coordinates are the world XY position in metres (the floor mesh sits at the origin with
unit scale); the rows are warped by noise so no slab is a rectangle.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _scan  # noqa: E402
import _wood as w  # noqa: E402

HEARTH = (-1.3, 1.9, 0.0)   # soot is thickest here
ROCK = "rock_05"
ROCK_TILE = 0.75            # metres of floor covered by one tile of the scan
ROCK_MEDIAN = 0.153         # median linear luminance of the scan: the neutral value


def _brick(nt, vec, c1, c2, mortar):
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.42
    brick.offset_frequency = 2
    brick.squash = 0.78
    brick.squash_frequency = 3
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Brick Width"].default_value = 0.82
    brick.inputs["Row Height"].default_value = 0.56
    brick.inputs["Mortar Size"].default_value = 0.011
    brick.inputs["Mortar Smooth"].default_value = 0.5
    brick.inputs["Bias"].default_value = 0.0
    brick.inputs["Color1"].default_value = (*c1, 1.0)
    brick.inputs["Color2"].default_value = (*c2, 1.0)
    brick.inputs["Mortar"].default_value = (*mortar, 1.0)
    nt.links.new(vec, brick.inputs["Vector"])
    return brick


def build(mat, nt, bsdf, wet=0.0):
    """`wet` 0 is the dry kitchen floor; the yard paving (yard_paving.py) calls this with `wet` above 0:
    darker slabs, and glossy standing water in patches."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    ox, oy, _ = w.sep(nt, obj)
    # slabs are not rectangles: warp the position by a little low-frequency noise
    warp_n = nt.nodes.new("ShaderNodeTexNoise")
    warp_n.inputs["Scale"].default_value = 1.7
    warp_n.inputs["Detail"].default_value = 3.0
    nt.links.new(obj, warp_n.inputs["Vector"])
    warp = w.vm(nt, "MULTIPLY_ADD", w.vm(nt, "SUBTRACT", warp_n.outputs["Color"], 0.5).outputs[0], 0.18, None)
    warped = w.vm(nt, "ADD", obj, warp.outputs[0])

    # one brick node for the joints (and a dull per-slab mix), one that gives each slab a random number 0..1
    stone = _brick(nt, warped.outputs[0], (0.150, 0.140, 0.125), (0.085, 0.082, 0.078), (0.050, 0.045, 0.040))
    ids = _brick(nt, warped.outputs[0], (0.0, 0.0, 0.0), (1.0, 1.0, 1.0), (0.0, 0.0, 0.0))
    joint = stone.outputs["Fac"]                    # 1 in the joint
    rand = _scan.luminance(nt, ids.outputs["Color"])
    rand2 = w.math(nt, "FRACT", w.math(nt, "MULTIPLY", rand, 7.31))

    # the scanned rock, a different patch for every slab
    uv_u = w.math(nt, "ADD", ox, w.math(nt, "MULTIPLY", rand, 3.7))
    uv_v = w.math(nt, "ADD", oy, w.math(nt, "MULTIPLY", rand2, 2.9))
    rock = _scan.planar(nt, ROCK, uv_u, uv_v, ROCK_TILE, maps=("diff", "nor_gl", "disp"))
    rock_lum = w.math(nt, "DIVIDE", _scan.luminance(nt, rock["diff"]), ROCK_MEDIAN)

    # tone: a slab's own value and warmth, metre-sized zones, the rock's light and dark, paler worn patches
    zones = w.noise(nt, obj, 0.9, 3.0, 0.5)
    gain = w.math(nt, "MULTIPLY", w.map_range(nt, rand, 0.0, 1.0, 0.7, 1.35), w.map_range(nt, zones, 0.3, 0.7, 0.8, 1.15))
    gain = w.math(nt, "MULTIPLY", gain, w.math(nt, "MULTIPLY_ADD", w.math(nt, "SUBTRACT", rock_lum, 1.0), 0.6, 1.0))
    cool = w.mix_color(nt, rand2, _tint(nt, (1.0, 1.0, 1.02)), _tint(nt, (1.05, 1.0, 0.9)))
    colour = w.mix_color(nt, 1.0, stone.outputs["Color"], cool, "MULTIPLY")
    colour = w.mix_color(nt, 1.0, colour, _grey(nt, gain), "MULTIPLY")
    worn = w.map_range(nt, w.noise(nt, obj, 0.55, 3.0, 0.5), 0.5, 0.68)
    colour = w.mix_color(nt, w.math(nt, "MULTIPLY", worn, 0.3), colour, (0.20, 0.19, 0.17), "ADD")

    # soot near the hearth, damp-dark along the walls (ambient occlusion in the corners)
    wpos, _ = w.world(nt)
    to_hearth = w.vm(nt, "DISTANCE", wpos, HEARTH).outputs["Value"]
    soot = w.map_range(nt, to_hearth, 0.4, 2.0, 0.3, 0.0)
    colour = w.mix_color(nt, soot, colour, (0.03, 0.028, 0.026), "MULTIPLY")
    ao = w.occlusion(nt, 0.35)
    colour = w.mix_color(nt, w.map_range(nt, ao, 0.2, 1.0, 0.35, 0.0), colour, (0.4, 0.38, 0.36), "MULTIPLY")
    puddle = None
    if wet:
        # damp slabs are darker; patches of standing water are darker still and nearly a mirror
        puddle = w.map_range(nt, w.noise(nt, obj, 0.35, 3.0, 0.55), 0.5, 0.62)
        damp = w.map_range(nt, w.noise(nt, obj, 0.8, 3.0, 0.5), 0.3, 0.6, 0.5, 1.0)
        colour = w.mix_color(nt, w.math(nt, "MULTIPLY", damp, wet), colour, (0.5, 0.55, 0.65), "MULTIPLY")
        colour = w.mix_color(nt, w.math(nt, "MULTIPLY", puddle, wet), colour, (0.45, 0.5, 0.6), "MULTIPLY")
        colour = w.mix_color(nt, 0.7, colour, (0.42, 0.44, 0.5), "MULTIPLY")
    nt.links.new(colour, bsdf.inputs["Base Color"])

    # worn patches are smoother; the rest is matte; joints are dry dirt
    scuff = w.noise(nt, obj, 6.0, 4.0, 0.55)
    rough = w.lerp(nt, worn, w.map_range(nt, scuff, 0.3, 0.7, 0.74, 0.92), 0.62)
    if puddle is not None:
        rough = w.lerp(nt, w.math(nt, "MULTIPLY", puddle, wet), rough, 0.06)
    rough = w.lerp(nt, joint, rough, 0.97)
    nt.links.new(rough, bsdf.inputs["Roughness"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.3

    # relief: each slab at its own height, joints recessed, the scanned pitting on the slab faces
    level = w.math(nt, "MULTIPLY", w.math(nt, "SUBTRACT", 1.0, joint), w.map_range(nt, rand, 0.0, 1.0, 0.55, 1.0))
    pits = w.math(nt, "MULTIPLY", w.math(nt, "SUBTRACT", rock["disp"], 0.59), 0.5)
    height = w.math(nt, "ADD", level, w.math(nt, "MULTIPLY", pits, w.math(nt, "SUBTRACT", 1.0, joint)))
    n_scan = _scan.tangent_normal(nt, rock["nor_gl"], (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    n_scan = w.vm(nt, "NORMALIZE", n_scan).outputs[0]
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    n_mix = nt.nodes.new("ShaderNodeMix")
    n_mix.data_type = "VECTOR"
    n_mix.inputs[0].default_value = 0.7
    nt.links.new(geo.outputs["Normal"], n_mix.inputs[4])
    nt.links.new(n_scan, n_mix.inputs[5])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.01
    bump.inputs["Strength"].default_value = 1.0
    nt.links.new(height, bump.inputs["Height"])
    nt.links.new(w.vm(nt, "NORMALIZE", n_mix.outputs[1]).outputs[0], bump.inputs["Normal"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


def _grey(nt, value):
    """A grey colour socket from a float socket."""
    c = nt.nodes.new("ShaderNodeCombineColor")
    for name in ("Red", "Green", "Blue"):
        nt.links.new(value, c.inputs[name])
    return c.outputs[0]


def _tint(nt, rgb):
    """A constant colour socket."""
    n = nt.nodes.new("ShaderNodeRGB")
    n.outputs[0].default_value = (*rgb, 1.0)
    return n.outputs[0]

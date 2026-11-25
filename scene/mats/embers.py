"""Embers: charred crust cracked open to deep-orange glow, and flying sparks.

Coals and fuel (no `spark` attribute) show dark crust with glowing cracks, deep orange and never
brighter than 0.9, so the view transform keeps them orange and does not bleach them to white.
Meshes that carry the per-point float attribute `spark` (1 hot, 0 cold; see
assets/_fire.py) are flat glowing flakes: amber when hot, red as they cool.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood as w  # noqa: E402

SPARK_STRENGTH = 2.2


def build(mat, nt, bsdf):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    info = nt.nodes.new("ShaderNodeObjectInfo")
    seed = w.math(nt, "MULTIPLY", info.outputs["Random"], 30.0)

    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 24.0
    nt.links.new(obj, vor.inputs["Vector"])
    cracks = w.map_range(nt, vor.outputs["Distance"], 0.0, 0.11, 1.0, 0.0)
    hot = w.noise(nt, obj, 9.0, 4.0, 0.6, seed)
    # cracks glow everywhere; larger hot patches open the crust up as well
    glow = w.math(nt, "ADD", cracks, w.map_range(nt, hot, 0.52, 0.78, -0.2, 0.55), clamp=True)

    # nearly black and matte: the fire's own light sits a hand's width above the coals, and a normal
    # dark albedo would light up to a pale pink under it
    bsdf.inputs["Base Color"].default_value = (0.0025, 0.002, 0.0018, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.95
    bsdf.inputs["Specular IOR Level"].default_value = 0.0
    coal = nt.nodes.new("ShaderNodeValToRGB")
    coal.color_ramp.elements[0].color = (0.40, 0.020, 0.002, 1.0)
    coal.color_ramp.elements[1].color = (1.0, 0.17, 0.010, 1.0)
    nt.links.new(glow, coal.inputs["Fac"])
    coal_strength = w.map_range(nt, glow, 0.0, 1.0, 0.0, 0.9)

    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_type = "GEOMETRY"
    attr.attribute_name = "spark"
    heat = attr.outputs["Fac"]
    is_spark = w.math(nt, "GREATER_THAN", heat, 0.001)
    flake = nt.nodes.new("ShaderNodeValToRGB")
    cr = flake.color_ramp
    cr.elements[0].color = (0.9, 0.05, 0.004, 1.0)
    mid = cr.elements.new(0.5)
    mid.color = (1.0, 0.17, 0.010, 1.0)
    cr.elements[2].color = (1.0, 0.36, 0.030, 1.0)
    nt.links.new(heat, flake.inputs["Fac"])

    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(is_spark, mix.inputs[0])
    nt.links.new(coal.outputs["Color"], mix.inputs[6])
    nt.links.new(flake.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], bsdf.inputs["Emission Color"])

    strength = nt.nodes.new("ShaderNodeMix")
    strength.data_type = "FLOAT"
    nt.links.new(is_spark, strength.inputs[0])
    nt.links.new(coal_strength, strength.inputs[2])
    nt.links.new(w.math(nt, "MULTIPLY", heat, SPARK_STRENGTH), strength.inputs[3])
    nt.links.new(strength.outputs[0], bsdf.inputs["Emission Strength"])

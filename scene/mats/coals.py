"""Hearth and oven coals: a dark crust of charcoal and grey ash with orange spots where it has cracked open.

Only a few hot spots glow, in the middle of the bed, each a soft ember and not a network of lines.
The glow is deep orange and never above 0.9, so the view transform does not bleach it. The mesh's
material is named `embers.coals` by the props, so anim.py takes the bed for the fire's coals.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood as w  # noqa: E402


def build(mat, nt, bsdf):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    info = nt.nodes.new("ShaderNodeObjectInfo")
    seed = w.math(nt, "MULTIPLY", info.outputs["Random"], 30.0)

    # crust: charcoal with grey ash flecks
    fine = w.noise(nt, obj, 38.0, 5.0, 0.6, seed)
    flecks = w.map_range(nt, w.noise(nt, obj, 16.0, 3.0, 0.5, seed), 0.55, 0.75)
    crust = w.mix_color(nt, flecks, w.ramp(nt, fine, [(0.3, (0.006, 0.005, 0.005)), (0.7, (0.035, 0.030, 0.028))]),
                        (0.10, 0.095, 0.09))
    nt.links.new(crust, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    bsdf.inputs["Specular IOR Level"].default_value = 0.0
    _bump = nt.nodes.new("ShaderNodeBump")
    _bump.inputs["Strength"].default_value = 0.5
    _bump.inputs["Distance"].default_value = 0.01
    nt.links.new(fine, _bump.inputs["Height"])
    nt.links.new(_bump.outputs["Normal"], bsdf.inputs["Normal"])

    # hot spots: round soft cells of a Voronoi pattern, only where a slow noise opens the crust
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "F1"
    vor.inputs["Scale"].default_value = 11.0
    nt.links.new(obj, vor.inputs["Vector"])
    spot = w.map_range(nt, vor.outputs["Distance"], 0.10, 0.42, 1.0, 0.0)
    open_ = w.map_range(nt, w.noise(nt, obj, 5.0, 3.0, 0.6, seed), 0.38, 0.62)
    glow = w.math(nt, "MULTIPLY", w.math(nt, "MULTIPLY", spot, spot), open_, clamp=True)
    glow = w.math(nt, "MULTIPLY", glow, w.map_range(nt, fine, 0.25, 0.75, 0.6, 1.0))
    hot = w.ramp(nt, glow, [(0.0, (0.45, 0.025, 0.003)), (1.0, (1.0, 0.20, 0.012))])
    nt.links.new(hot, bsdf.inputs["Emission Color"])
    nt.links.new(w.map_range(nt, glow, 0.0, 1.0, 0.0, 0.9), bsdf.inputs["Emission Strength"])

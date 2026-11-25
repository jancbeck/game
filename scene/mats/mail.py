"""A mail shirt: riveted rings, oiled dark steel, rubbed bright where the straps and the arms wear it.

Each ring is a round Voronoi cell of about a centimetre with a dark gap between neighbours; the
cells give the bump, the gaps are darker. The metal is blue-black with a brown film of oil, and
a slow noise makes it lighter at the shoulders where it is rubbed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood as w  # noqa: E402


def build(mat, nt, bsdf):
    obj = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    rings = nt.nodes.new("ShaderNodeTexVoronoi")
    rings.feature = "F1"
    rings.inputs["Scale"].default_value = 95.0
    nt.links.new(obj, rings.inputs["Vector"])
    cell = w.map_range(nt, rings.outputs["Distance"], 0.15, 0.62, 1.0, 0.0)
    wear = w.map_range(nt, w.noise(nt, obj, 4.0, 3.0, 0.5), 0.35, 0.7, 0.0, 1.0)
    base = w.ramp(nt, cell, [(0.0, (0.008, 0.008, 0.01)), (1.0, (0.075, 0.07, 0.072))])
    colour = w.mix_color(nt, w.math(nt, "MULTIPLY", wear, 0.35), base, (0.16, 0.13, 0.10))
    nt.links.new(colour, bsdf.inputs["Base Color"])
    bsdf.inputs["Metallic"].default_value = 0.85
    nt.links.new(w.map_range(nt, cell, 0.0, 1.0, 0.65, 0.38), bsdf.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.7
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(cell, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

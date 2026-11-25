"""Cast iron of a cauldron or a pot: blue-black, sooted, dull, with a worn lighter edge.

Dry (a kitchen under a roof): no rust runs and no film of water. Soot is heavier on the underside
and the outside; the rim and the raised casting seams are rubbed bright and a little smoother, so
firelight finds a dull line along them and nowhere else.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood as w  # noqa: E402


def build(mat, nt, bsdf):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    seed, _ = w.seed_of(nt, 50.0)
    pitting = w.noise(nt, obj, 70.0, 5.0, 0.6, seed)
    blotch = w.noise(nt, obj, 5.0, 4.0, 0.55, seed)
    base = w.ramp(nt, pitting, [(0.3, (0.012, 0.012, 0.015)), (0.7, (0.040, 0.038, 0.040))])
    sooty = w.map_range(nt, blotch, 0.35, 0.7, 0.0, 0.7)
    colour = w.mix_color(nt, sooty, base, (0.2, 0.2, 0.2), "MULTIPLY")
    # edges rubbed bright: occlusion is 1 on convex edges and in the open
    ao = w.occlusion(nt, 0.03)
    worn = w.map_range(nt, ao, 0.85, 1.0, 0.0, 1.0)
    colour = w.mix_color(nt, w.math(nt, "MULTIPLY", worn, 0.35), colour, (0.20, 0.19, 0.18), "ADD")
    nt.links.new(colour, bsdf.inputs["Base Color"])
    nt.links.new(w.map_range(nt, pitting, 0.3, 0.7, 0.62, 0.82), bsdf.inputs["Metallic"])
    rough = w.lerp(nt, w.math(nt, "MULTIPLY", worn, 0.5), w.map_range(nt, blotch, 0.3, 0.7, 0.62, 0.8), 0.46)
    nt.links.new(rough, bsdf.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.004
    bump.inputs["Strength"].default_value = 0.4
    nt.links.new(pitting, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

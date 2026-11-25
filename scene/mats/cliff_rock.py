"""The cliff rock around the commander's chamber: dark bedded rock, cracked into blocks, with moss on its up-facing planes.

Dull and dark, with no sheen: it takes the moon's light as a pale wash only on the planes that face up. Object coordinates are
metres. Used by the tower_surround prop.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood as w  # noqa: E402


def build(mat, nt, bsdf):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    tone = w.noise(nt, obj, 1.1, 6.0, 0.55)
    grain = w.noise(nt, obj, 9.0, 8.0, 0.6)
    cell = nt.nodes.new("ShaderNodeTexVoronoi")
    cell.feature = "DISTANCE_TO_EDGE"
    cell.inputs["Scale"].default_value = 2.4
    nt.links.new(obj, cell.inputs["Vector"])
    cracks = w.map_range(nt, cell.outputs["Distance"], 0.0, 0.1, 0.0, 1.0)         # 0 in a crack
    shade = w.math(nt, "MULTIPLY", tone, w.map_range(nt, grain, 0.3, 0.7, 0.6, 1.1))
    stone = w.ramp(nt, shade, [(0.0, (0.014, 0.016, 0.018)), (0.5, (0.042, 0.044, 0.048)), (1.0, (0.095, 0.092, 0.088))])
    stone = w.mix_color(nt, cracks, (0.005, 0.005, 0.006), stone)
    # moss where the surface faces up, in patches
    _, nrm = w.world(nt)
    _, _, nz = w.sep(nt, nrm)
    up = w.map_range(nt, nz, 0.7, 0.95, 0.0, 1.0)
    patch = w.map_range(nt, w.noise(nt, obj, 1.8, 4.0, 0.5), 0.45, 0.65, 0.0, 1.0)
    moss = w.math(nt, "MULTIPLY", up, patch, clamp=True)
    colour = w.mix_color(nt, moss, stone, (0.022, 0.036, 0.015))
    nt.links.new(colour, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.93
    height = w.math(nt, "ADD", w.math(nt, "MULTIPLY", grain, 0.5), w.math(nt, "ADD", w.math(nt, "MULTIPLY", tone, 0.6),
                                                                          w.math(nt, "MULTIPLY", cracks, 0.5)))
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 1.2
    bump.inputs["Distance"].default_value = 0.15
    nt.links.new(height, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

"""Painted emblem on the soaked banner: dull wet ochre-grey paint, flaked to the dark cloth, red dye bled into it, grimy streaks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood as w  # noqa: E402

PAINT = [(0.0, (0.170, 0.148, 0.108)), (1.0, (0.300, 0.265, 0.200))]
STAIN = (0.082, 0.064, 0.042)
GRIME = (0.034, 0.030, 0.025)
DYE = (0.128, 0.060, 0.054)       # red dye that has bled into the wet paint
CLOTH = (0.040, 0.013, 0.016)     # soaked red cloth under worn-through paint


def build(mat, nt, bsdf):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    seed, _ = w.seed_of(nt)
    _, _, z = w.sep(nt, obj)
    hem = w.map_range(nt, z, -1.4, -0.4, 1.0, 0.0)

    flake = w.noise(nt, obj, 11.0, 6.0, 0.65, seed)
    worn = w.map_range(nt, flake, 0.54, 0.67)
    grain = w.noise(nt, obj, 80.0, 4.0, 0.55)
    blotch = w.noise(nt, obj, 4.0, 4.0, 0.6, seed)
    runoff = w.map_range(nt, w.noise(nt, w.vm(nt, "MULTIPLY", obj, (9.0, 9.0, 0.9)).outputs[0], 1.0, 4.0, 0.58, seed),
                         0.35, 0.65)
    paint = w.ramp(nt, grain, PAINT)
    # ochre-stained, blotchy paint; dirt streaks and grime toward the hem
    aged = w.mix_color(nt, w.map_range(nt, blotch, 0.4, 0.65, 0.0, 0.55), paint, STAIN)
    aged = w.mix_color(nt, w.math(nt, "MULTIPLY", w.math(nt, "SUBTRACT", 1.0, runoff), 0.45), aged, GRIME)
    aged = w.mix_color(nt, w.math(nt, "MULTIPLY", hem, 0.4), aged, GRIME)
    # the red dye bleeds into wet paint, in the runs and low on the cloth
    bleed = w.math(nt, "MULTIPLY", w.math(nt, "MAXIMUM", runoff, 0.3), w.map_range(nt, z, -1.3, -0.3, 0.9, 0.35))
    aged = w.mix_color(nt, w.math(nt, "MULTIPLY", bleed, 0.55), aged, DYE)
    # the paint is soaked too
    aged = w.darken(nt, aged, 0.30, (0.68, 0.66, 0.65))
    # worn through to the dark red cloth
    nt.links.new(w.mix_color(nt, worn, aged, CLOTH), bsdf.inputs["Base Color"])
    nt.links.new(w.lerp(nt, hem, 0.80, 0.68), bsdf.inputs["Roughness"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.25
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(flake, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

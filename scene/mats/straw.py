"""Straw: grey-gold stalks, bleached in patches, dark and muddy where it lies damp on the floor."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood as w  # noqa: E402


OVERALL = 0.8  # how much the whole straw is pulled toward dark, wet, trodden


def build(mat, nt, bsdf):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    seed, rnd = w.seed_of(nt)
    wpos, wnrm = w.world(nt)
    _, _, wz = w.sep(nt, wpos)

    fine = w.noise(nt, obj, 40.0, 4.0, 0.55)
    # each stalk its own tone; patches of old grey straw and fresher gold
    patch = w.noise(nt, wpos, 1.6, 4.0, 0.6, seed)
    tone = w.math(nt, "ADD", w.lerp(nt, 0.35, patch, fine),
                  w.math(nt, "MULTIPLY", w.math(nt, "SUBTRACT", rnd, 0.5), 0.5), clamp=True)
    base = w.ramp(nt, tone, [(0.2, (0.090, 0.077, 0.050)), (0.8, (0.235, 0.205, 0.140))])
    grey = w.map_range(nt, w.noise(nt, wpos, 3.0, 3.0, 0.55, seed), 0.42, 0.62)
    base = w.mix_color(nt, w.math(nt, "MULTIPLY", grey, 0.65), base, (0.185, 0.170, 0.135))

    # damp lower layers and mud splashed up from the floor
    ragged = w.noise(nt, wpos, 6.0, 3.0, 0.6)
    low = w.map_range(nt, w.math(nt, "DIVIDE", wz, w.math(nt, "MULTIPLY_ADD", ragged, 0.30, 0.08)), 0.0, 1.0, 1.0, 0.0)
    damp = w.math(nt, "MAXIMUM", low, w.map_range(nt, w.noise(nt, wpos, 2.2, 3.0, 0.6, seed), 0.52, 0.7, 0.0, 0.5))
    base = w.mix_color(nt, w.math(nt, "MULTIPLY", low, 0.5), base, (0.060, 0.048, 0.030))
    base = w.darken(nt, base, damp, (0.40, 0.37, 0.30))
    # trodden into the wet yard: straw on the ground is dull and dark, not pale gold
    base = w.darken(nt, base, OVERALL, (0.5, 0.48, 0.42))
    nt.links.new(base, bsdf.inputs["Base Color"])

    nt.links.new(w.lerp(nt, damp, 0.85, 0.6), bsdf.inputs["Roughness"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.3
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(fine, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

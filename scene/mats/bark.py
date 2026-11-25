"""Tree bark: deep grey-brown furrows along the trunk, wet ridges, runoff streaks and pale lichen."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood as w  # noqa: E402


def build(mat, nt, bsdf):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    seed, rnd = w.seed_of(nt)
    wpos, wnrm = w.world(nt)
    # furrows run along the long axis of the trunk or branch
    _, _, _, stretched = w.grain_axes(nt, 1.6, 9.0)

    fur = w.noise(nt, stretched, 1.0, 5.0, 0.62, seed)
    # distance from the ridge crest: 0 in the furrow, 1 on top of a plate
    plate = w.map_range(nt, w.math(nt, "ABSOLUTE", w.math(nt, "SUBTRACT", fur, 0.5)), 0.0, 0.17)
    tone = w.noise(nt, obj, 1.8, 4.0, 0.6, seed)
    tone = w.math(nt, "ADD", tone, w.math(nt, "MULTIPLY", w.math(nt, "SUBTRACT", rnd, 0.5), 0.3), clamp=True)

    ridge = w.ramp(nt, w.map_range(nt, tone, 0.25, 0.75),
                   [(0.0, (0.075, 0.068, 0.058)), (1.0, (0.190, 0.172, 0.146))])
    base = w.mix_color(nt, plate, (0.010, 0.009, 0.008), ridge)
    # lichen on the plates, mostly low and in patches
    spots = w.math(nt, "MULTIPLY", w.map_range(nt, w.noise(nt, obj, 6.0, 5.0, 0.62, seed), 0.58, 0.64),
                   w.map_range(nt, w.noise(nt, obj, 1.2, 2.0, 0.5, seed), 0.45, 0.6))
    base = w.mix_color(nt, w.math(nt, "MULTIPLY", spots, plate), base, (0.115, 0.125, 0.085))

    # wet: dark soaked bark low down and in runoff streaks
    wet, film, _ = w.rain_wetness(nt, wpos, wnrm, seed, ground=1.2, streaks=0.65, film=0.4)
    base = w.darken(nt, base, wet, (0.42, 0.38, 0.34))
    base = w.darken(nt, base, 1.0, (0.6, 0.6, 0.62))  # soaked bark reads as a dark silhouette in the mist
    nt.links.new(base, bsdf.inputs["Base Color"])

    nt.links.new(w.lerp(nt, wet, w.map_range(nt, plate, 0.0, 1.0, 0.95, 0.8), 0.55), bsdf.inputs["Roughness"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.25
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.025
    nt.links.new(plate, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

"""Burlap: coarse open weave, water-stained and grimy, dark where it sits wet on the ground."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood as w  # noqa: E402

THREAD = 0.022   # thread pitch in meters


def build(mat, nt, bsdf):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj, nrm = tc.outputs["Object"], tc.outputs["Normal"]
    seed, rnd = w.seed_of(nt)
    wpos, wnrm = w.world(nt)
    _, _, wz = w.sep(nt, wpos)

    # weave: threads cross in the two axes lying in the surface; blend the three planes by the normal
    s = w.vm(nt, "SINE", w.vm(nt, "MULTIPLY", obj, 6.2832 / THREAD).outputs[0])
    sx, sy, sz = w.sep(nt, s.outputs[0])
    nx, ny, nz = w.sep(nt, w.vm(nt, "POWER", w.vm(nt, "ABSOLUTE", nrm).outputs[0], 4.0).outputs[0])
    total = w.math(nt, "ADD", w.math(nt, "ADD", nx, ny), nz)

    def plane(weight, a, b):
        return w.math(nt, "MULTIPLY", w.math(nt, "DIVIDE", weight, total), w.math(nt, "MULTIPLY", a, b))

    cross = w.math(nt, "ADD", w.math(nt, "ADD", plane(nx, sy, sz), plane(ny, sx, sz)), plane(nz, sx, sy))
    weave = w.map_range(nt, cross, -1.0, 1.0)

    # large tone changes survive the painterly filter: plain sacking, blotchy tide marks, grime
    fibre = w.noise(nt, obj, 60.0, 3.0, 0.55)
    tone = w.math(nt, "ADD", w.noise(nt, obj, 2.0, 4.0, 0.6, seed),
                  w.math(nt, "MULTIPLY", w.math(nt, "SUBTRACT", rnd, 0.5), 0.35), clamp=True)
    base = w.ramp(nt, w.lerp(nt, 0.15, tone, weave), [(0.2, (0.075, 0.062, 0.045)), (0.8, (0.170, 0.145, 0.108))])
    base = w.mix_color(nt, w.map_range(nt, w.noise(nt, obj, 5.0, 4.0, 0.6, seed), 0.46, 0.64, 0.0, 0.9),
                       base, (0.040, 0.032, 0.022))
    # dirty low down and wet along the ground
    ragged = w.noise(nt, wpos, 5.0, 3.0, 0.6)
    low = w.map_range(nt, w.math(nt, "DIVIDE", wz, w.math(nt, "MULTIPLY_ADD", ragged, 0.35, 0.12)), 0.0, 1.0, 1.0, 0.0)
    base = w.mix_color(nt, w.math(nt, "MULTIPLY", low, 0.6), base, (0.050, 0.042, 0.030))
    wet = w.math(nt, "MAXIMUM", low, w.map_range(nt, w.noise(nt, wpos, 1.8, 3.0, 0.55, seed), 0.55, 0.72, 0.0, 0.7))
    base = w.darken(nt, base, wet, (0.45, 0.40, 0.34))
    nt.links.new(base, bsdf.inputs["Base Color"])

    nt.links.new(w.lerp(nt, wet, 0.95, 0.7), bsdf.inputs["Roughness"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.2
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(w.math(nt, "ADD", weave, fibre), bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

"""Banner cloth: soaked wool, dark desaturated maroon, water streaks down the pleats, rust runs under the rings, muddy hem."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood as w  # noqa: E402

RING_DX = 0.144   # distance between the rings on the rod; ring i sits at x = (i - 2.5) * RING_DX
WOOL = [(0.0, (0.050, 0.011, 0.013)), (1.0, (0.112, 0.024, 0.026))]   # dry-dark to lit wool, wet and muted
RUST = (0.100, 0.046, 0.022)
MUD = (0.040, 0.031, 0.025)
MOULD = (0.024, 0.030, 0.022)
WATER_TINT = (0.46, 0.50, 0.53)    # multiplier under a water run
FOLD_TINT = (0.50, 0.50, 0.53)     # multiplier deep in a pleat


def build(mat, nt, bsdf):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    seed, _ = w.seed_of(nt)
    x, _, z = w.sep(nt, obj)
    # the banner hangs from z = 0 down to z = -2.4
    hem = w.map_range(nt, z, -2.4, -0.3, 1.0, 0.0)           # 1 at the hem
    top = w.map_range(nt, z, -1.0, 0.0, 0.0, 1.0)            # 1 at the rod

    weave = w.noise(nt, obj, 90.0, 3.0, 0.55)
    stain = w.noise(nt, obj, 2.2, 5.0, 0.6, seed)
    tone = w.lerp(nt, 0.45, weave, stain)
    base = w.ramp(nt, w.map_range(nt, tone, 0.3, 0.7), WOOL)

    # water runs down the pleats: dark vertical streaks, broad and fine
    runs = w.map_range(nt, w.noise(nt, w.vm(nt, "MULTIPLY", obj, (11.0, 11.0, 0.7)).outputs[0], 1.0, 4.0, 0.58, seed),
                       0.38, 0.66)
    base = w.darken(nt, base, w.math(nt, "MULTIPLY", runs, 0.6), WATER_TINT)
    fine = w.map_range(nt, w.noise(nt, w.vm(nt, "MULTIPLY", obj, (38.0, 38.0, 1.8)).outputs[0], 1.0, 2.0, 0.5, seed),
                       0.42, 0.64)
    base = w.darken(nt, base, w.math(nt, "MULTIPLY", fine, 0.3), WATER_TINT)

    # rust runs under every ring, long and narrow, strongest at the rod
    u = w.math(nt, "DIVIDE", w.math(nt, "ADD", x, 2.5 * RING_DX), RING_DX)
    nearest = w.math(nt, "MINIMUM", w.math(nt, "MAXIMUM", w.math(nt, "ROUND", u), 0.0), 5.0)
    dist = w.math(nt, "MULTIPLY", w.math(nt, "ABSOLUTE", w.math(nt, "SUBTRACT", u, nearest)), RING_DX)
    across = w.map_range(nt, dist, 0.0, 0.026, 1.0, 0.0)
    reach = w.math(nt, "MULTIPLY", w.map_range(nt, z, -1.1, -0.05, 0.0, 1.0),
                   w.map_range(nt, w.noise(nt, w.vm(nt, "MULTIPLY", obj, (4.0, 4.0, 1.2)).outputs[0], 1.0, 3.0, 0.55, seed),
                               0.30, 0.65, 0.35, 1.0))
    base = w.mix_color(nt, w.math(nt, "MULTIPLY", w.math(nt, "MULTIPLY", across, reach), 0.9), base, RUST)

    # mildew: dark grey-green specks, mostly in the lower half
    mould = w.math(nt, "MULTIPLY", w.map_range(nt, w.noise(nt, obj, 14.0, 5.0, 0.65, seed), 0.58, 0.64),
                   w.map_range(nt, z, -2.4, -0.3, 1.0, 0.2))
    base = w.mix_color(nt, w.math(nt, "MULTIPLY", mould, 0.7), base, MOULD)

    # mud wicked up from the floor splash and the hem's own grime
    ragged = w.noise(nt, obj, 6.0, 4.0, 0.6, seed)
    mud = w.map_range(nt, w.math(nt, "ADD", w.math(nt, "MULTIPLY", hem, 1.3), w.math(nt, "MULTIPLY", ragged, 0.5)), 1.0, 1.4)
    base = w.mix_color(nt, w.math(nt, "MULTIPLY", mud, 0.65), base, MUD)

    # pleats collect water and dirt: valleys are darker
    ao = w.occlusion(nt, 0.07)
    base = w.darken(nt, base, w.map_range(nt, ao, 0.25, 0.9, 0.75, 0.0), FOLD_TINT)
    # the whole cloth is soaked, a little more at the hem where the water gathers
    base = w.darken(nt, base, w.math(nt, "MULTIPLY_ADD", hem, 0.3, 0.45), (0.66, 0.64, 0.66))
    nt.links.new(base, bsdf.inputs["Base Color"])

    # wet: glossy water film, with matte patches where the wool shows through
    patch = w.map_range(nt, w.noise(nt, obj, 3.0, 3.0, 0.55, seed), 0.46, 0.62)
    nt.links.new(w.lerp(nt, patch, w.lerp(nt, hem, 0.52, 0.46), 0.72), bsdf.inputs["Roughness"])
    bsdf.inputs["Sheen Weight"].default_value = 0.04
    bsdf.inputs["Sheen Roughness"].default_value = 0.5
    bsdf.inputs["Sheen Tint"].default_value = (0.20, 0.12, 0.12, 1.0)
    bsdf.inputs["Specular IOR Level"].default_value = 0.4
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.0025
    nt.links.new(weave, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

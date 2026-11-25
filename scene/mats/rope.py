"""Frayed hemp rope: twisted strands as slanted stripes, pale loose fibres, dark and damp where rain soaks it."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood as w  # noqa: E402


def build(mat, nt, bsdf):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    seed, _ = w.seed_of(nt)
    wpos, wnrm = w.world(nt)
    x, y, z = w.sep(nt, obj)
    # angle about local Z (round the rope, or along a coil) and height give a helix
    angle = w.math(nt, "ARCTAN2", y, x)
    helix = w.combine(nt, w.math(nt, "MULTIPLY", angle, 1.2), w.math(nt, "MULTIPLY", z, 4.0), 0.0)

    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "DIAGONAL"
    wave.wave_profile = "TRI"
    wave.inputs["Scale"].default_value = 1.0
    wave.inputs["Distortion"].default_value = 0.0
    nt.links.new(helix, wave.inputs["Vector"])

    fibre = w.noise(nt, obj, 140.0, 3.0, 0.6)
    strands = w.lerp(nt, 0.35, wave.outputs["Fac"], fibre)

    # hemp: grey-tan, dirt packed between the strands
    base = w.ramp(nt, strands, [(0.0, (0.110, 0.092, 0.066)), (1.0, (0.300, 0.255, 0.188))])
    # frayed ends: sparse bright fibres standing out of the lay
    fray = w.math(nt, "MULTIPLY", w.map_range(nt, w.noise(nt, obj, 260.0, 2.0, 0.5, seed), 0.60, 0.68),
                  w.map_range(nt, w.noise(nt, obj, 7.0, 2.0, 0.5, seed), 0.40, 0.62))
    base = w.mix_color(nt, w.math(nt, "MULTIPLY", fray, 0.7), base, (0.40, 0.34, 0.25))

    # damp: soaked patches, the splash zone, and a general rain darkening
    wet, film, _ = w.rain_wetness(nt, wpos, wnrm, seed, ground=0.6, streaks=0.0, film=0.0)
    soaked = w.map_range(nt, w.noise(nt, obj, 2.5, 3.0, 0.55, seed), 0.35, 0.6, 0.25, 0.95)
    damp = w.math(nt, "MAXIMUM", wet, soaked)
    base = w.darken(nt, base, damp, (0.34, 0.30, 0.26))
    nt.links.new(base, bsdf.inputs["Base Color"])

    nt.links.new(w.lerp(nt, damp, 0.95, 0.55), bsdf.inputs["Roughness"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.25

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.006
    nt.links.new(strands, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

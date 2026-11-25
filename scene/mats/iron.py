"""Old iron: blued-black metal under orange-brown rust that streaks down from joints, with dark wet patches."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _scan  # noqa: E402
import _wood as w  # noqa: E402

RUST = "rust_coarse_01"  # scanned coarse rust and pitting (scene/textures)
RUST_TILE = 0.35  # meters per tile of the scan


def build(mat, nt, bsdf):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    seed, _ = w.seed_of(nt, 50.0)
    wpos, wnrm = w.world(nt)

    # fine structure: the scanned rust scale and pitting, broken by a little noise
    sc = _scan.wood(nt, RUST, (1.0, 1.01, 1.02), RUST_TILE, RUST_TILE, w.math(nt, "MULTIPLY", seed, 0.02),
                    maps=("diff", "nor_gl"))
    scan = w.map_range(nt, _scan.luminance(nt, sc["diff"]), 0.03, 0.10)
    fine = w.lerp(nt, 0.7, w.noise(nt, obj, 45.0, 6.0, 0.6, seed), scan)
    # rust coverage: broad blotches, runoff streaks down the world Z axis, and extra in corners
    patch = w.noise(nt, obj, 4.0, 5.0, 0.62, seed)
    squeezed = w.vm(nt, "MULTIPLY", wpos, (9.0, 9.0, 1.1))
    runoff = w.map_range(nt, w.noise(nt, squeezed.outputs[0], 1.0, 3.0, 0.55, seed), 0.50, 0.72)
    ao = w.occlusion(nt, 0.1)
    crevice = w.map_range(nt, ao, 0.3, 0.9, 0.25, 0.0)
    cover = w.math(nt, "ADD", w.math(nt, "MAXIMUM", w.map_range(nt, patch, 0.48, 0.66), runoff),
                   crevice, clamp=True)
    rust = w.map_range(nt, w.math(nt, "MULTIPLY", cover, w.map_range(nt, fine, 0.15, 0.6, 0.6, 1.0)), 0.35, 0.65)

    metal = w.ramp(nt, fine, [(0.3, (0.030, 0.030, 0.034)), (0.7, (0.100, 0.096, 0.094))])
    scale = w.ramp(nt, fine, [(0.25, (0.060, 0.030, 0.020)), (0.55, (0.150, 0.072, 0.036)),
                              (0.85, (0.230, 0.110, 0.050))])
    base = w.mix_color(nt, rust, metal, scale)

    # wet: dark, glossy patches on tops and in the splash zone
    wet, film, _ = w.rain_wetness(nt, wpos, wnrm, seed, ground=0.6, streaks=0.0, film=0.8)
    base = w.darken(nt, base, w.math(nt, "MULTIPLY", wet, 0.8), (0.42, 0.40, 0.40))
    nt.links.new(base, bsdf.inputs["Base Color"])

    # rust is dull and non-metallic; bare iron is metal; wet iron is glossy
    nt.links.new(w.map_range(nt, rust, 0.0, 1.0, 0.85, 0.12), bsdf.inputs["Metallic"])
    base_rough = w.map_range(nt, fine, 0.3, 0.7, 0.45, 0.62)
    rough = w.lerp(nt, rust, base_rough, w.map_range(nt, fine, 0.3, 0.7, 0.7, 0.92))
    nt.links.new(w.lerp(nt, w.math(nt, "MULTIPLY", wet, 0.7), rough, 0.22), bsdf.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.005
    nt.links.new(w.math(nt, "ADD", fine, rust), bump.inputs["Height"])
    nt.links.new(_scan.to_world_normal(nt, sc["normal"], 1.2), bump.inputs["Normal"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

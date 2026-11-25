"""Wet crow plumage: near-black barbs under a thin water film.

A bird is 20-30 px at the main camera, so the film carries the read, not the pigment:

- Low roughness and a thin coat give crisp reflections, so firelight and the moon leave small
  hard glints on the back and shoulders.
- A rim term stands in for the bright overcast horizon that the film mirrors at grazing angles.
  It follows the surface normal against the view, so it looks the same from every camera, and
  it is weighted toward up-facing surfaces because the sky is above.
- The pigment stays black and the reflections stay low, so a bird in front of a lit wall or
  wet floor is a dark shape, and in front of a dark wall it is a dark shape with a lit edge.

Flat feather ribbons (wings, tail) carry a `vane` point attribute of 1. A flat sheet mirrors
the whole moon or fire disc at once and flashes white, so vanes get a rough surface, almost no
specular and almost no rim. The round body, neck, head, bill and wing bones keep the gloss.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood as w  # noqa: E402

RIM_COLOR = (0.32, 0.36, 0.44)  # overcast sky just after sunset
RIM_STRENGTH = 0.7              # emission at the very edge of an up-facing surface
RIM_POWER = 2.6                 # higher keeps the rim thin
SKY_SHEEN = 0.07                # emission over the whole up-facing back, so it parts from the belly
SKY_VANE = 0.3                  # share of the back sheen that flat feathers keep
VANE_RIM = 0.15                 # share of the rim that flat feathers keep
WET_ROUGHNESS = (0.20, 0.36)    # smooth where feathers are matted wet, rougher where dry
SPECULAR = (0.35, 0.03)         # Specular IOR Level on round parts, on vanes
COAT = 0.12                     # water film weight on round parts


def build(mat, nt, bsdf):
    obj = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    barbs = w.noise(nt, obj, 90.0, 4.0, 0.6)
    clumps = w.noise(nt, obj, 24.0, 3.0, 0.5)   # matted groups of wet feathers
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_type = "GEOMETRY"
    attr.attribute_name = "vane"
    vane = attr.outputs["Fac"]

    # pigment: black, with a faint cool drift in the wetter clumps
    pigment = w.ramp(nt, barbs, [(0.0, (0.003, 0.003, 0.004)), (1.0, (0.014, 0.013, 0.017))])
    sheen = w.ramp(nt, clumps, [(0.0, (0.004, 0.005, 0.010)), (1.0, (0.010, 0.013, 0.024))])
    nt.links.new(w.mix_color(nt, w.map_range(nt, clumps, 0.35, 0.75, 0.0, 0.5), pigment, sheen),
                 bsdf.inputs["Base Color"])

    wet = w.map_range(nt, clumps, 0.3, 0.7, *WET_ROUGHNESS)
    nt.links.new(w.lerp(nt, vane, wet, 0.5), bsdf.inputs["Roughness"])
    nt.links.new(w.lerp(nt, vane, SPECULAR[0], SPECULAR[1]), bsdf.inputs["Specular IOR Level"])
    nt.links.new(w.lerp(nt, vane, COAT, 0.0), bsdf.inputs["Coat Weight"])
    bsdf.inputs["Coat Roughness"].default_value = 0.07
    bsdf.inputs["Coat IOR"].default_value = 1.4

    # sky rim: strongest at grazing angles on surfaces that face up
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.5
    edge = w.math(nt, "POWER", lw.outputs["Facing"], RIM_POWER)
    _, nrm = w.world(nt)
    _, _, nz = w.sep(nt, nrm)
    sky = w.map_range(nt, nz, -0.3, 0.9, 0.2, 1.0)
    rim = w.math(nt, "MULTIPLY", w.math(nt, "MULTIPLY", edge, sky),
                 w.map_range(nt, clumps, 0.2, 0.8, 0.6, 1.0))
    rim = w.math(nt, "MULTIPLY", rim, w.lerp(nt, vane, 1.0, VANE_RIM))
    # sky sheen: the up-facing back mirrors the lighter overcast, a little more toward the edges
    top = w.math(nt, "MULTIPLY", w.map_range(nt, nz, 0.15, 0.95, 0.0, 1.0),
                 w.map_range(nt, lw.outputs["Facing"], 0.0, 0.8, 0.35, 1.0))
    top = w.math(nt, "MULTIPLY", top, w.lerp(nt, vane, 1.0, SKY_VANE))
    glow = w.math(nt, "ADD", w.math(nt, "MULTIPLY", rim, RIM_STRENGTH), w.math(nt, "MULTIPLY", top, SKY_SHEEN))
    bsdf.inputs["Emission Color"].default_value = (*RIM_COLOR, 1.0)
    nt.links.new(glow, bsdf.inputs["Emission Strength"])

    # barb texture and matted clumps: kept shallow, because steep micro-normals scatter the
    # moon and fire reflections into a pale haze over the whole bird
    bump = nt.nodes.new("ShaderNodeBump")
    nt.links.new(w.lerp(nt, vane, 0.0007, 0.0002), bump.inputs["Distance"])
    nt.links.new(barbs, bump.inputs["Height"])
    clump_bump = nt.nodes.new("ShaderNodeBump")
    nt.links.new(w.lerp(nt, vane, 0.0025, 0.0006), clump_bump.inputs["Distance"])
    nt.links.new(clumps, clump_bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], clump_bump.inputs["Normal"])
    nt.links.new(clump_bump.outputs["Normal"], bsdf.inputs["Normal"])

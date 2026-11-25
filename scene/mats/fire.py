"""Flame: saturated orange, deep red-orange at the edges, amber in the core, ragged and see-through at the rim.

Flame meshes are tall tongues, so Generated Z runs 0 at the base to 1 at the tip whatever the mesh's
own position. Heat falls with height, rises where the surface faces the camera, and is broken up by
noise that streaks upward and slides up with the scene time, so a still frame is one moment of a
flicker. Every tongue has its own noise offset from its Object Info random value.

Colour. The view transform (AgX) turns a bright emission into pastel: red 1.0 at strength 1 comes out
salmon even with almost no green or blue, and the glare pass adds to that. Measured on swatches with
the scene's exposure and the Punchy look, strength 0.6 stays a saturated orange and strength 1.5 does
not. So emission is low: it peaks at 1.0 in the core and falls to 0.45 at the edges, and the ramp
runs from red-orange through orange to amber (1.0, 0.36, 0.010) and never to yellow-white.

Opacity. Opaque where the surface faces the camera, clear at the silhouette, at the tip and at the foot
(where the tongue sinks into the coals), with the noise biting ragged holes in the rim.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood as w  # noqa: E402

FPS = 24.0
FLICKER = 1.3        # noise units per second the flame structure slides upward


def _clock(nt):
    """Scene time in seconds, from the current frame."""
    v = nt.nodes.new("ShaderNodeValue")
    drv = v.outputs[0].driver_add("default_value")
    drv.driver.type = "SCRIPTED"
    drv.driver.expression = f"frame / {FPS}"
    return v.outputs[0]


def build(mat, nt, bsdf):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    gen = tc.outputs["Generated"]
    gx, gy, gz = w.sep(nt, gen)
    info = nt.nodes.new("ShaderNodeObjectInfo")
    seed = w.math(nt, "MULTIPLY", info.outputs["Random"], 30.0)
    clock = _clock(nt)

    coords = w.combine(nt, w.math(nt, "MULTIPLY", gx, 7.0), w.math(nt, "MULTIPLY", gy, 7.0),
                       w.math(nt, "SUBTRACT", w.math(nt, "MULTIPLY", gz, 2.2), w.math(nt, "MULTIPLY", clock, FLICKER)))
    streaks = w.noise(nt, coords, 1.0, 4.0, 0.62, seed)
    facing = nt.nodes.new("ShaderNodeLayerWeight")
    facing.inputs["Blend"].default_value = 0.5

    by_height = w.map_range(nt, gz, 0.0, 1.0, 0.80, -0.30)
    by_view = w.map_range(nt, facing.outputs["Facing"], 0.0, 1.0, 0.40, -0.20)
    by_noise = w.map_range(nt, streaks, 0.3, 0.7, -0.26, 0.26)
    heat = w.math(nt, "ADD", w.math(nt, "ADD", by_height, by_view), by_noise, clamp=True)

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (0.80, 0.050, 0.002, 1.0)
    for pos, col in ((0.30, (1.0, 0.10, 0.003, 1.0)), (0.60, (1.0, 0.19, 0.005, 1.0)),
                     (0.85, (1.0, 0.28, 0.008, 1.0))):
        cr.elements.new(pos).color = col
    cr.elements[4].position, cr.elements[4].color = 1.0, (1.0, 0.36, 0.010, 1.0)
    nt.links.new(heat, ramp.inputs["Fac"])

    bsdf.inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    bsdf.inputs["Specular IOR Level"].default_value = 0.0
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Emission Color"])
    nt.links.new(w.map_range(nt, heat, 0.0, 1.0, 0.45, 1.0), bsdf.inputs["Emission Strength"])

    a_view = w.map_range(nt, facing.outputs["Facing"], 0.0, 1.0, 3.5, -0.1)
    a_tip = w.map_range(nt, gz, 0.55, 1.0, 0.0, -1.8)
    a_foot = w.map_range(nt, gz, 0.0, 0.10, -0.6, 0.0)
    alpha = w.math(nt, "ADD", w.math(nt, "ADD", w.math(nt, "ADD", a_view, a_tip), a_foot), by_noise, clamp=True)
    nt.links.new(alpha, bsdf.inputs["Alpha"])

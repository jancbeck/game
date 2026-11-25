"""Smoke: a soft, dim plume as a volume that leaves the fire, is laid over by the wind and thins out.

Put this material on a closed mesh made by assets/_fire.smoke(). The mesh is only a
bounding box: the shader works from Object coordinates (meters, origin at the base of
the plume) and fades to zero long before the box wall, so the box never shows.

Shape, all in the object's own space:

- Wind. The downwind direction is a world-space yaw (`ang0`), turned into object space, so
  a rotated prop keeps the same wind. u is the distance downwind of the base, v the
  distance across the wind.
- Axis. The plume leaves the base at the angle atan(rise / drift) above the ground and
  flattens out as the wind takes it: its height is rise * (1 - exp(-u / drift)). A drift
  larger than the rise lays the plume down; a small one lets it climb. The progress along
  the plume is s = 1 - exp(-u / drift), 0 at the base and 0.93 at u = 2.7 * drift.
- Cross-section. A gaussian profile around the axis, measured square to the axis (a tube,
  not a stack of horizontal slices), whose radius grows from `r0` to `r1`. The edge has no
  outline. Density also falls with the radius (the same smoke spread over a wider cloud)
  and fades out toward the far end, so the plume is thin where it leaves the fire, a little
  denser a hand downwind of it, and gone before s reaches 1. Noise carried along the axis
  breaks it into billows and eats it away more and more with distance.
- Light. Albedo is a dark neutral grey and the optical depth stays below about one:
  moonlight and sky lift it only a little, and the fire's point lights warm the part
  near the flame. There is no emission, so no part of the plume glows by itself.

Per-plume numbers are custom properties of the object (`rise`, `drift`, `r0`, `r1`,
`ang0`, `density`, `seed`), so every plume shares this one material.
The noise drifts downwind with the scene time, so the plume moves when frames advance.
"""

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood as w  # noqa: E402

COLOR = (0.24, 0.235, 0.23)    # dark neutral grey albedo
ANISOTROPY = 0.15
FILL = (0.36, 0.38, 0.42)
FILL_STRENGTH = 0.05            # per unit density: a dim glow of scattered sky light
WARP = 0.9                      # how far the warp bends the puff cells, in cells
PUFF_SCALE = 1.7                # puff cells per plume radius
FLOW_SPEED = 0.45               # meters per second the billows travel along the plume
FPS = 24.0
DENSITY_GAIN = 5.0               # the `density` property is the foot density per meter divided by this


def _smooth(nt, value, lo, hi, to_lo=0.0, to_hi=1.0):
    m = nt.nodes.new("ShaderNodeMapRange")
    m.interpolation_type = "SMOOTHSTEP"
    m.inputs["From Min"].default_value = lo
    m.inputs["From Max"].default_value = hi
    m.inputs["To Min"].default_value = to_lo
    m.inputs["To Max"].default_value = to_hi
    nt.links.new(value, m.inputs["Value"])
    return m.outputs["Result"]


def _attr(nt, name):
    n = nt.nodes.new("ShaderNodeAttribute")
    n.attribute_type = "OBJECT"
    n.attribute_name = f'["{name}"]'
    return n.outputs["Fac"]


def _sep(nt, vec):
    s = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(vec, s.inputs[0])
    return s.outputs["X"], s.outputs["Y"], s.outputs["Z"]


def _comb(nt, x, y, z):
    c = nt.nodes.new("ShaderNodeCombineXYZ")
    for sock, v in zip(("X", "Y", "Z"), (x, y, z)):
        if isinstance(v, bpy.types.NodeSocket):
            nt.links.new(v, c.inputs[sock])
        else:
            c.inputs[sock].default_value = v
    return c.outputs[0]


def _wind_dir(nt, yaw_deg):
    """Unit XY direction, in object space, of a world-space yaw (degrees)."""
    rad = w.math(nt, "RADIANS", yaw_deg)
    world = _comb(nt, w.math(nt, "COSINE", rad), w.math(nt, "SINE", rad), 0.0)
    xf = nt.nodes.new("ShaderNodeVectorTransform")
    xf.vector_type = "VECTOR"
    xf.convert_from, xf.convert_to = "WORLD", "OBJECT"
    nt.links.new(world, xf.inputs[0])
    unit = w.vm(nt, "NORMALIZE", xf.outputs[0])
    x, y, _ = _sep(nt, unit.outputs[0])
    return x, y


def _clock(nt):
    """Scene time in seconds, from the current frame."""
    v = nt.nodes.new("ShaderNodeValue")
    drv = v.outputs[0].driver_add("default_value")
    drv.driver.type = "SCRIPTED"
    drv.driver.expression = f"frame / {FPS}"
    return v.outputs[0]


def build(mat, nt, bsdf):
    nt.nodes.remove(bsdf)          # volume only: the box itself stays invisible
    out = nt.nodes["Material Output"]
    mul, add, sub, div = (lambda a, b: w.math(nt, "MULTIPLY", a, b),
                          lambda a, b: w.math(nt, "ADD", a, b),
                          lambda a, b: w.math(nt, "SUBTRACT", a, b),
                          lambda a, b: w.math(nt, "DIVIDE", a, b))
    exp = lambda x: w.math(nt, "POWER", 2.718281828, x)  # noqa: E731

    rise, drift = _attr(nt, "rise"), _attr(nt, "drift")
    r0, r1 = _attr(nt, "r0"), _attr(nt, "r1")
    peak, seed = _attr(nt, "density"), _attr(nt, "seed")

    tc = nt.nodes.new("ShaderNodeTexCoord")
    px, py, pz = _sep(nt, tc.outputs["Object"])

    # downwind distance u (a little upwind of the base, so the foot is a round puff) and
    # crosswind distance v
    dx, dy = _wind_dir(nt, _attr(nt, "ang0"))
    u = add(add(mul(px, dx), mul(py, dy)), mul(r0, 0.6))
    v = sub(mul(py, dx), mul(px, dy))

    # progress along the plume and the height of its axis
    s = sub(1.0, exp(mul(div(w.math(nt, "MAXIMUM", u, 0.0), drift), -1.0)))
    axis_z = mul(rise, s)
    slope = mul(div(rise, drift), sub(1.0, s))
    # offsets from the axis, with a slow meander that grows downwind
    clock = _clock(nt)
    phase = add(mul(u, 2.3), sub(mul(seed, 3.1), mul(clock, 0.9)))
    meander = mul(mul(w.math(nt, "POWER", s, 1.2), r1), 0.35)
    off_v = sub(v, mul(w.math(nt, "SINE", phase), meander))
    off_z = sub(sub(pz, axis_z), mul(w.math(nt, "COSINE", mul(phase, 0.83)), mul(meander, 0.6)))
    # distance square to the axis: the vertical offset shrinks by cos(axis angle)
    perp = div(off_z, w.math(nt, "SQRT", add(1.0, mul(slope, slope))))

    # gaussian cross-section that widens quickly, then slowly
    radius = w.math(nt, "MULTIPLY_ADD", w.math(nt, "POWER", s, 0.6), sub(r1, r0), r0)
    dist = w.math(nt, "SQRT", add(mul(off_v, off_v), mul(perp, perp)))
    q = div(dist, radius)
    core = mul(exp(mul(mul(q, q), -2.2)), _smooth(nt, q, 1.9, 1.3))

    # billows: noise in axis-following coordinates, drifting downwind with time, sized by the plume
    fscale = div(1.0, w.math(nt, "MAXIMUM", r1, 0.05))
    coords = _comb(nt, mul(sub(u, mul(clock, FLOW_SPEED)), fscale), mul(off_v, fscale), mul(perp, fscale))
    coords = w.vm(nt, "ADD", coords, _comb(nt, seed, mul(seed, 1.7), mul(seed, 0.6))).outputs[0]
    # domain warp, then round puffs (cells of a Voronoi texture) with finer noise on top
    warp = nt.nodes.new("ShaderNodeTexNoise")
    warp.inputs["Scale"].default_value = 1.1
    warp.inputs["Detail"].default_value = 2.0
    nt.links.new(coords, warp.inputs["Vector"])
    bent = w.vm(nt, "ADD", coords,
                w.vm(nt, "MULTIPLY", w.vm(nt, "SUBTRACT", warp.outputs["Color"], (0.5, 0.5, 0.5)).outputs[0],
                     (WARP, WARP, WARP)).outputs[0])
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = PUFF_SCALE
    nt.links.new(bent.outputs[0], vor.inputs["Vector"])
    puff = _smooth(nt, vor.outputs["Distance"], 0.95, 0.05)
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 6.0
    fine.inputs["Detail"].default_value = 3.0
    nt.links.new(bent.outputs[0], fine.inputs["Vector"])
    wisp = _smooth(nt, fine.outputs["Fac"], 0.25, 0.75)

    # broken up more with distance: near the fire a soft column, the far end patchy wisps
    lumps = mul(puff, add(0.20, mul(wisp, 0.80)))
    breakup = add(0.65, mul(_smooth(nt, s, 0.0, 0.8), 0.3))
    shape = mul(core, add(sub(1.0, breakup), mul(lumps, breakup)))

    # thin at the foot, densest a hand downwind of the flame, spread thin and gone before the end
    fade_in = _smooth(nt, s, 0.0, 0.25)
    fade_out = _smooth(nt, s, 0.30, 0.93, 1.0, 0.0)
    spread = w.math(nt, "POWER", div(mul(add(r0, r1), 0.5), radius), 1.2)
    density = mul(mul(mul(shape, mul(fade_in, fade_out)), spread), mul(peak, DENSITY_GAIN))

    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (*COLOR, 1.0)
    vol.inputs["Anisotropy"].default_value = ANISOTROPY
    nt.links.new(density, vol.inputs["Density"])
    # a trace of cool fill, scaled by density so the box can never show
    vol.inputs["Emission Color"].default_value = (*FILL, 1.0)
    nt.links.new(mul(density, FILL_STRENGTH), vol.inputs["Emission Strength"])
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])

"""Materials of the falling-water asset (assets/drips.py).

Three materials, all built here because the shared library has no water:

- `drip_water`: strands, beads and splash droplets. Clear and glossy, with no emission, so it
  shows only where it catches light: the fires, the sky at a grazing angle, the moon. Opacity
  rises toward the silhouette (the thin cylinder reflects most there) and stays low across the
  middle, with a little diffuse body so a strand reads as water and not as a hole.
- `drip_ring`: the ripple ring and the thin film around a splash. Same water, fading to nothing
  at both edges of the ring through the per-vertex float attribute `fade`.
- `drip_wet`: the dark, mirror-wet patch under a drip. A near-black base with a sharp
  reflection, faded out toward its rim by `fade` and broken into a ragged edge by noise, so the
  cobbles show through and the patch does not look like a decal.

Meshes carry the float point attribute `fade` (1 in the middle of the ring or patch, 0 at its
edge); `drip_water` ignores it.
"""

import bpy

WATER_TINT = (0.56, 0.63, 0.73)  # tint of the faint ring and film
BODY_TINT = (0.11, 0.125, 0.145)  # diffuse body of a strand or sheet: clear water scatters little light


def _new(name):
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat, None
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    return mat, mat.node_tree


def _math(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, bpy.types.NodeSocket):
            nt.links.new(v, n.inputs[i])
        else:
            n.inputs[i].default_value = v
    return n.outputs[0]


def _map(nt, value, lo, hi, to_lo=0.0, to_hi=1.0, smooth=False):
    m = nt.nodes.new("ShaderNodeMapRange")
    if smooth:
        m.interpolation_type = "SMOOTHSTEP"
    m.inputs["From Min"].default_value = lo
    m.inputs["From Max"].default_value = hi
    m.inputs["To Min"].default_value = to_lo
    m.inputs["To Max"].default_value = to_hi
    nt.links.new(value, m.inputs["Value"])
    return m.outputs["Result"]


def _fade(nt):
    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_type = "GEOMETRY"
    a.attribute_name = "fade"
    return a.outputs["Fac"]


def _bsdf(nt):
    return nt.nodes["Principled BSDF"]


def water():
    mat, nt = _new("drip_water")
    if nt is None:
        return mat
    b = _bsdf(nt)
    b.inputs["Base Color"].default_value = (*BODY_TINT, 1.0)
    b.inputs["Roughness"].default_value = 0.04
    b.inputs["IOR"].default_value = 1.333
    b.inputs["Specular IOR Level"].default_value = 1.0
    b.inputs["Metallic"].default_value = 0.0
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.5
    # Facing is 0 across the middle of a strand and 1 at its silhouette
    rim = _math(nt, "POWER", lw.outputs["Facing"], 1.5)
    nt.links.new(_map(nt, rim, 0.0, 1.0, 0.16, 0.6), b.inputs["Alpha"])
    return mat


def ring():
    mat, nt = _new("drip_ring")
    if nt is None:
        return mat
    b = _bsdf(nt)
    b.inputs["Base Color"].default_value = (*WATER_TINT, 1.0)
    b.inputs["Roughness"].default_value = 0.3
    b.inputs["IOR"].default_value = 1.333
    b.inputs["Specular IOR Level"].default_value = 0.4
    nt.links.new(_map(nt, _fade(nt), 0.0, 1.0, 0.0, 0.08, smooth=True), b.inputs["Alpha"])
    return mat


def sheet():
    """The film between two merging streams: vertical streaks, thickest under the edge."""
    mat, nt = _new("drip_sheet")
    if nt is None:
        return mat
    b = _bsdf(nt)
    b.inputs["Base Color"].default_value = (*BODY_TINT, 1.0)
    b.inputs["Roughness"].default_value = 0.05
    b.inputs["IOR"].default_value = 1.333
    b.inputs["Specular IOR Level"].default_value = 1.0
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(_math(nt, "MULTIPLY", sep.outputs["X"], 38.0), comb.inputs["X"])
    nt.links.new(_math(nt, "MULTIPLY", sep.outputs["Y"], 38.0), comb.inputs["Y"])
    nt.links.new(_math(nt, "MULTIPLY", sep.outputs["Z"], 2.0), comb.inputs["Z"])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.0
    noise.inputs["Detail"].default_value = 2.0
    nt.links.new(comb.outputs[0], noise.inputs["Vector"])
    streaks = _map(nt, noise.outputs["Fac"], 0.30, 0.70, 0.35, 1.0)
    nt.links.new(_math(nt, "MULTIPLY", _map(nt, _fade(nt), 0.0, 1.0, 0.0, 0.4), streaks), b.inputs["Alpha"])
    return mat


def wet():
    mat, nt = _new("drip_wet")
    if nt is None:
        return mat
    b = _bsdf(nt)
    b.inputs["Base Color"].default_value = (0.010, 0.012, 0.016, 1.0)
    b.inputs["Roughness"].default_value = 0.05
    b.inputs["Specular IOR Level"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.333
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 9.0
    noise.inputs["Detail"].default_value = 3.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    # ragged edge: the noise lowers the fade where it is dark, so the rim breaks up first
    edge = _math(nt, "ADD", _fade(nt), _map(nt, noise.outputs["Fac"], 0.3, 0.7, -0.35, 0.35))
    nt.links.new(_map(nt, edge, 0.25, 0.85, 0.0, 0.8, smooth=True), b.inputs["Alpha"])
    return mat

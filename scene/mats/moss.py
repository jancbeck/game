"""Wet moss, weeds and grass tufts: dark olive at the root, paler olive at the tips.

Meant for small tufts and cushions placed on stone, mud and cobbles. The tip
gradient comes from the Generated coordinates, so it follows each tuft's own
bounding box whatever its size. Variation uses object coordinates in meters.
"""

ROOT = (0.016, 0.026, 0.010)  # shaded, wet base of the clump
BODY = (0.040, 0.056, 0.020)  # main olive green
TIP = (0.108, 0.120, 0.050)  # sun-bleached, yellower tips
DEAD = (0.120, 0.095, 0.050)  # a few dried brown blades
DEAD_AMOUNT = 0.22  # share of the clump that has dried out
TIP_FROM = 0.35  # height fraction where the tip color starts


def _link(nt, sock, value):
    if hasattr(value, "node"):
        nt.links.new(value, sock)
    elif value is not None:
        if sock.type == "RGBA" and len(value) == 3:
            value = (*value, 1.0)
        sock.default_value = value


def _node(nt, idname, inputs=None, **attrs):
    n = nt.nodes.new(idname)
    for k, v in attrs.items():
        setattr(n, k, v)
    for k, v in (inputs or {}).items():
        _link(nt, n.inputs[k], v)
    return n


def _range(nt, value, lo, hi, to_lo=0.0, to_hi=1.0):
    return _node(nt, "ShaderNodeMapRange",
                 {"Value": value, "From Min": lo, "From Max": hi, "To Min": to_lo, "To Max": to_hi}).outputs["Result"]


def _mix(nt, fac, a, b, blend="MIX"):
    n = _node(nt, "ShaderNodeMix", data_type="RGBA", blend_type=blend)
    _link(nt, n.inputs[0], fac)
    _link(nt, n.inputs[6], a)
    _link(nt, n.inputs[7], b)
    return n.outputs[2]


def _noise(nt, vec, scale, detail=3.0):
    n = _node(nt, "ShaderNodeTexNoise", {"Scale": scale, "Detail": detail, "Roughness": 0.6})
    nt.links.new(vec, n.inputs["Vector"])
    return n.outputs["Fac"]


def build(mat, nt, bsdf):
    tc = _node(nt, "ShaderNodeTexCoord")
    pos, gen = tc.outputs["Object"], tc.outputs["Generated"]
    height = _node(nt, "ShaderNodeSeparateXYZ", {"Vector": gen}).outputs["Z"]

    # root to tip: dark and wet below, paler on top
    body = _mix(nt, _range(nt, height, 0.0, 0.5), ROOT, BODY)
    color = _mix(nt, _range(nt, height, TIP_FROM, 1.0), body, TIP)
    # clump-scale patches, some of them dried out
    dry = _range(nt, _noise(nt, pos, 14.0), 0.5 + (0.5 - DEAD_AMOUNT) * 0.3, 0.72)
    color = _mix(nt, dry, color, DEAD)
    # fine mottling so a bare sphere does not read as flat green
    fine = _range(nt, _noise(nt, pos, 70.0, 4.0), 0.3, 0.7, 0.75, 1.25)
    grey = _node(nt, "ShaderNodeCombineXYZ", {"X": fine, "Y": fine, "Z": fine}).outputs[0]
    color = _mix(nt, 1.0, color, grey, "MULTIPLY")
    nt.links.new(color, bsdf.inputs["Base Color"])

    # damp: some sheen, rougher toward the dry tips
    nt.links.new(_range(nt, height, 0.0, 1.0, 0.55, 0.85), bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = 0.0
    if "Subsurface Weight" in bsdf.inputs:  # thin leaves let a little light through
        bsdf.inputs["Subsurface Weight"].default_value = 0.15
        bsdf.inputs["Subsurface Radius"].default_value = (0.05, 0.12, 0.03)

    bump = _node(nt, "ShaderNodeBump", {"Strength": 0.5, "Distance": 0.01,
                                         "Height": _noise(nt, pos, 90.0, 4.0)})
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

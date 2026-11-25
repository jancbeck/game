"""Ground fog west of the castle: clear along the wall, thicker with every meter of distance, with a low
mist hanging over the ditch water.

Helper of west_ditch.py. A bounded volume, like the fog bank in road.py: a world volume would fill the
space between camera and scene. Density is a product of smooth ramps, so no face of the box shows.
"""

import bpy

from . import _ditch_field as F

X_RANGE = (-50.0, -13.2)          # world x of the box; the wall side is clear because density ramps up from zero
Y_RANGE = (-32.0, 17.0)
Z_RANGE = (-3.6, 3.2)
NEAR_X, FAR_X = -14.0, -27.0      # density is 0 at NEAR_X and full at FAR_X
DENSITY = 0.085                   # per meter at full development
MIST = 0.10                       # extra density in the low mist over the ditch
COLOR = (0.40, 0.45, 0.54)


def build(kit, root):
    x0, x1 = X_RANGE[0] - F.ORIGIN[0], X_RANGE[1] - F.ORIGIN[0]
    y0, y1 = Y_RANGE[0] - F.ORIGIN[1], Y_RANGE[1] - F.ORIGIN[1]
    z0, z1 = Z_RANGE[0] - F.LOWER_WARD, Z_RANGE[1] - F.LOWER_WARD
    box = kit.box("west_fog", (x1 - x0, y1 - y0, z1 - z0), ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), parent=root)
    mat = bpy.data.materials.new("west_fog")
    nt = mat.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])

    def node(kind, **attrs):
        n = nt.nodes.new(kind)
        for k, v in attrs.items():
            setattr(n, k, v)
        return n

    def ramp(src, lo, hi, to_lo=0.0, to_hi=1.0):
        m = node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
        for sock, v in zip(("From Min", "From Max", "To Min", "To Max"), (lo, hi, to_lo, to_hi)):
            m.inputs[sock].default_value = v
        nt.links.new(src, m.inputs["Value"])
        return m.outputs["Result"]

    def math_(op, a, b=0.0):
        n = node("ShaderNodeMath", operation=op)
        for i, v in enumerate((a, b)):
            if hasattr(v, "node"):
                nt.links.new(v, n.inputs[i])
            else:
                n.inputs[i].default_value = v
        return n.outputs[0]

    geo = node("ShaderNodeNewGeometry")
    sep = node("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    X, Y, Z = sep.outputs["X"], sep.outputs["Y"], sep.outputs["Z"]

    away = ramp(X, NEAR_X, FAR_X)
    ends = math_("MULTIPLY", ramp(Y, Y_RANGE[0], Y_RANGE[0] + 12.0), ramp(Y, Y_RANGE[1], Y_RANGE[1] - 12.0))
    height = ramp(Z, F.LOWER_WARD, F.LOWER_WARD + 5.5, 1.0, 0.0)
    cloud = node("ShaderNodeTexNoise")
    cloud.inputs["Scale"].default_value = 0.09
    cloud.inputs["Detail"].default_value = 3.0
    nt.links.new(geo.outputs["Position"], cloud.inputs["Vector"])
    patchy = ramp(cloud.outputs["Fac"], 0.3, 0.7, 0.55, 1.4)
    body = math_("MULTIPLY", math_("MULTIPLY", away, height), math_("MULTIPLY", ends, patchy))
    body = math_("MULTIPLY", body, DENSITY)

    # low mist over the water: the distance to the ditch's center line, flat in z
    dist = math_("ABSOLUTE", math_("ADD", X, 16.5))
    over_water = math_("MULTIPLY", ramp(dist, 0.8, 3.2, 1.0, 0.0), ramp(Z, F.LOWER_WARD + 0.1, F.LOWER_WARD + 1.0, 1.0, 0.0))
    over_water = math_("MULTIPLY", over_water, math_("MULTIPLY", ends, MIST))
    dens = math_("ADD", body, over_water)

    vol = node("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (*COLOR, 1.0)
    vol.inputs["Anisotropy"].default_value = 0.3
    nt.links.new(dens, vol.inputs["Density"])
    nt.links.new(vol.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    box.data.materials.append(mat)
    box.visible_shadow = False
    return box

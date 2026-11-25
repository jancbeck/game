"""Soot plume on a wall above a place where a flame burns or has burned.

plume() lays a thin quad on a wall face. Its material `soot` is matte black with an alpha that is
densest just above the flame and widens and fades upward, with a broken, streaky edge, so the stone
shows through. The material is shared by every plume and reads the quad's UVs: u runs across the
plume, v from its foot (0) to its top (1). The quad casts no shadow.
"""

import bpy


def _material():
    mat = bpy.data.materials.get("soot")
    if mat is not None:
        return mat
    mat = bpy.data.materials.new("soot")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.008, 0.007, 0.006, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.95
    new, link = nt.nodes.new, nt.links.new

    def math_node(op, a=None, b=None):
        n = new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                link(v, n.inputs[i])
        return n.outputs[0]

    uv = new("ShaderNodeUVMap")
    sep = new("ShaderNodeSeparateXYZ")
    link(uv.outputs["UV"], sep.inputs[0])
    u, v = sep.outputs["X"], sep.outputs["Y"]
    # across: a soft lens that widens upward from 35 % of the quad at the foot to all of it
    cx = math_node("ABSOLUTE", math_node("MULTIPLY", math_node("SUBTRACT", u, 0.5), 2.0))
    n = new("ShaderNodeMath")
    n.operation = "MULTIPLY_ADD"
    link(v, n.inputs[0])
    n.inputs[1].default_value = 0.65
    n.inputs[2].default_value = 0.35
    spread = n.outputs[0]
    r = math_node("DIVIDE", cx, spread)
    side = math_node("SUBTRACT", 1.0, math_node("POWER", r, 2.0))
    side = math_node("MAXIMUM", side, 0.0)
    # up: dense at the foot, fading out toward the top; a short fade-in under the foot
    up = math_node("POWER", math_node("SUBTRACT", 1.0, v), 1.6)
    foot = math_node("MINIMUM", math_node("MULTIPLY", v, 12.0), 1.0)
    # streaks: noise stretched along v, so the soot runs in vertical tongues
    mapping = new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (9.0, 1.6, 1.0)
    link(uv.outputs["UV"], mapping.inputs["Vector"])
    noise = new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 6.0
    link(mapping.outputs["Vector"], noise.inputs["Vector"])
    n = new("ShaderNodeMath")
    n.operation = "MULTIPLY_ADD"
    link(noise.outputs["Fac"], n.inputs[0])
    n.inputs[1].default_value = 1.4
    n.inputs[2].default_value = -0.2
    streak = n.outputs[0]
    alpha = math_node("MULTIPLY", math_node("MULTIPLY", side, up), math_node("MULTIPLY", foot, streak))
    attr = new("ShaderNodeAttribute")
    attr.attribute_type = "OBJECT"
    attr.attribute_name = "soot_strength"
    alpha = math_node("MULTIPLY", alpha, attr.outputs["Fac"])
    link(math_node("MINIMUM", alpha, 1.0), bsdf.inputs["Alpha"])
    return mat


def plume(kit, root, name, foot, width, height, strength=0.9, axis="x"):
    """Soot quad whose foot center is root-relative `foot`.

    The quad stands in the plane of the wall: `axis` "x" spans X (a wall face in the XZ plane, the
    plume seen from -Y), "y" spans Y (a wall face in the YZ plane). It rises `height` meters and is
    `width` meters wide at the top. `strength` scales the alpha (1 is black at the densest point).
    """
    fx, fy, fz = foot
    h = width / 2
    if axis == "x":
        verts = [(fx - h, fy, fz), (fx + h, fy, fz), (fx + h, fy, fz + height), (fx - h, fy, fz + height)]
    else:
        verts = [(fx, fy - h, fz), (fx, fy + h, fz), (fx, fy + h, fz + height), (fx, fy - h, fz + height)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for loop, co in zip(uv.data, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop.uv = co
    me.materials.append(_material())
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.parent = root
    ob["soot_strength"] = float(strength)
    ob.visible_shadow = False
    return ob

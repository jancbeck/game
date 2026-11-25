"""Guard's wet wool cloak on a peg beside a door, with a belt on the next peg.

Origin: the board's center on the wall face (XZ plane at y = 0); the cloak hangs toward -Y. The
board is 0.62 m wide and its pegs are at z = 1.65, near a guard's eye level, so the cloak ends
about 0.55 m off the ground. The cloak is one gathered sheet: narrow where it hangs from the peg,
fanning out below it in deep vertical folds that grow toward a scalloped hem 1.1 m down, with a
hood bulge at the neck. It is dark red-brown wool, soaked darker toward the hem. Mount it under
"mounted" with z = 0.
"""

import math

import bpy

PEG_Z = 1.65
LENGTH = 1.10
PEG_X = (-0.16, 0.18)


def _wool():
    mat = bpy.data.materials.get("guard_wool")
    if mat is not None:
        return mat
    mat = bpy.data.materials.new("guard_wool")
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    new = nt.nodes.new
    tc = new("ShaderNodeTexCoord")
    sep = new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    # soaked toward the hem: Object Z runs from 0 at the peg down to -LENGTH
    wet = new("ShaderNodeMapRange")
    wet.inputs["From Min"].default_value = -LENGTH
    wet.inputs["From Max"].default_value = -0.15
    wet.inputs["To Min"].default_value = 0.45
    wet.inputs["To Max"].default_value = 1.0
    nt.links.new(sep.outputs["Z"], wet.inputs["Value"])
    fibre = new("ShaderNodeTexNoise")
    fibre.inputs["Scale"].default_value = 90.0
    fibre.inputs["Detail"].default_value = 2.0
    nt.links.new(tc.outputs["Object"], fibre.inputs["Vector"])
    tone = new("ShaderNodeValToRGB")
    tone.color_ramp.elements[0].color = (0.045, 0.014, 0.012, 1.0)
    tone.color_ramp.elements[1].color = (0.080, 0.026, 0.020, 1.0)
    nt.links.new(fibre.outputs["Fac"], tone.inputs["Fac"])
    dark = new("ShaderNodeMix")
    dark.data_type = "RGBA"
    dark.blend_type = "MULTIPLY"
    dark.inputs[0].default_value = 1.0
    nt.links.new(tone.outputs["Color"], dark.inputs[6])
    grey = new("ShaderNodeCombineColor")
    for name in ("Red", "Green", "Blue"):
        nt.links.new(wet.outputs["Result"], grey.inputs[name])
    nt.links.new(grey.outputs["Color"], dark.inputs[7])
    nt.links.new(dark.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.9
    b.inputs["Specular IOR Level"].default_value = 0.2
    b.inputs["Sheen Weight"].default_value = 0.4
    b.inputs["Sheen Roughness"].default_value = 0.5
    return mat


def _cloak(kit, rng, root, x):
    """Gathered sheet hanging from (x, -0.14, PEG_Z), as a grid with solidify."""
    nu, nv = 21, 28
    ph = rng.uniform(0, 6.28)
    verts, faces = [], []
    for j in range(nv):
        v = j / (nv - 1)                      # 0 at the peg, 1 at the hem
        half = 0.07 + 0.30 * v ** 0.75        # gathered at the neck, fanning out below
        depth = 0.035 + 0.06 * math.sin(math.pi * min(v * 1.2, 1.0)) * 0.6
        amp = 0.010 + 0.040 * v               # folds deepen toward the hem
        for i in range(nu):
            u = -1 + 2 * i / (nu - 1)
            fold = amp * math.cos(4.2 * math.pi * u + ph + 1.5 * v)
            sag = 0.04 * v * (1 - u * u)
            hem = 0.035 * math.sin(7.0 * u + ph) * v ** 3
            z = PEG_Z - 0.03 - v * LENGTH - hem
            y = -(0.075 + depth * 0.5 + fold + sag * 0.5)
            verts.append((x + u * half, y, z))
    for j in range(nv - 1):
        for i in range(nu - 1):
            a = j * nu + i
            faces.append((a, a + 1, a + nu + 1, a + nu))
    ob = kit.mesh("cloak", [(vx - x, vy, vz - PEG_Z) for vx, vy, vz in verts], faces, loc=(x, 0, PEG_Z),
                  mat=_wool(), parent=root)
    for p in ob.data.polygons:
        p.use_smooth = True
    kit.solidify(ob, 0.012)
    return ob


def build(kit, mats, rng):
    root = kit.group("cloak_peg")
    wd, iron, leather = mats["wood_dark"], mats["iron"], mats["burlap"]
    kit.box("board", (0.62, 0.05, 0.11), (0, -0.025, PEG_Z + 0.015), (0, 0, kit.jitter(rng, 1.5)), wd, bevel=0.006,
            parent=root)
    for n, x in enumerate(PEG_X):
        kit.cylinder(f"peg_{n}", 0.018, 0.16, (x, -0.1, PEG_Z), rot_deg=(90, 0, 0), mat=wd, segments=8,
                     radius_top=0.014, bevel=0.003, parent=root)
        kit.cylinder(f"peg_cap_{n}", 0.026, 0.02, (x, -0.185, PEG_Z), rot_deg=(90, 0, 0), mat=wd, segments=8,
                     parent=root)
    _cloak(kit, rng, root, PEG_X[0])
    # hood: a soft bulge hanging behind the neck, over the board
    kit.sphere("hood", 0.095, (PEG_X[0], -0.115, PEG_Z - 0.2), scale=(0.75, 0.55, 1.5), mat=_wool(), segments=10,
               parent=root)
    # a leather belt with an iron buckle hanging from the other peg
    x = PEG_X[1]
    kit.box("belt", (0.035, 0.012, 0.55), (x, -0.155, PEG_Z - 0.30), (3, 0, 0), leather, bevel=0.003, parent=root)
    kit.box("buckle", (0.05, 0.016, 0.04), (x, -0.16, PEG_Z - 0.04), mat=iron, bevel=0.004, parent=root)
    return root

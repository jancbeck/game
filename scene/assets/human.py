"""Scale mannequin: a 1.80 m artist's dummy standing on Z = 0, facing -Y.

Only used to judge prop sizes, so it is lit-emissive light cyan and stands out
against dark stone and wood. Head 0.23 m, shoulders 0.45 m wide, legs 0.93 m.
Eighteen parts: head, neck, chest, pelvis, two arms (shoulder, upper arm,
forearm, hand) and two legs (thigh, shin, foot).
"""

import math

import bpy
from mathutils import Vector

HEIGHT = 1.80
SHOULDER = Vector((0.175, 0.0, 1.45))   # right shoulder joint; the left one mirrors X
HIP = Vector((0.095, 0.0, 0.93))
KNEE = Vector((0.105, -0.01, 0.50))
ANKLE = Vector((0.115, 0.0, 0.10))
ELBOW = SHOULDER + Vector((0.078, 0.0, -0.29))
WRIST = ELBOW + Vector((0.052, -0.031, -0.25))


def _material():
    mat = bpy.data.materials.get("scale_human")
    if mat is not None:
        return mat
    mat = bpy.data.materials.new("scale_human")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.35, 0.85, 1.0, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.7
    bsdf.inputs["Emission Color"].default_value = (0.25, 0.85, 1.0, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 1.6
    return mat


def _euler_deg(direction):
    return [math.degrees(a) for a in Vector(direction).to_track_quat("Z", "Y").to_euler()]


def _limb(kit, name, p0, p1, r0, r1, mat, parent):
    """Tapered cylinder from p0 (radius r0) to p1 (radius r1)."""
    d = p1 - p0
    return kit.cylinder(name, r0, d.length, tuple((p0 + p1) / 2), _euler_deg(d), mat,
                        segments=14, radius_top=r1, parent=parent)


def _blob(kit, name, center, radii, mat, parent, rot_deg=(0, 0, 0)):
    ob = kit.sphere(name, 1.0, tuple(center), scale=radii, rot_deg=rot_deg, mat=mat,
                    segments=20, parent=parent)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def build(kit, mats, rng):
    mat = _material()
    root = kit.group("human")

    _blob(kit, "head", (0, 0, 1.685), (0.088, 0.104, 0.115), mat, root)
    kit.cylinder("neck", 0.048, 0.12, (0, 0, 1.55), mat=mat, segments=14, parent=root)
    _blob(kit, "chest", (0, 0, 1.30), (0.20, 0.115, 0.23), mat, root)
    _blob(kit, "pelvis", (0, 0, 1.00), (0.165, 0.11, 0.13), mat, root)

    for side, sx in (("r", 1), ("l", -1)):
        def mx(v):
            return Vector((v.x * sx, v.y, v.z))

        # arm: slightly away from the body, forearm bent a little forward
        _blob(kit, f"shoulder_{side}", mx(SHOULDER), (0.056, 0.056, 0.056), mat, root)
        _limb(kit, f"upper_arm_{side}", mx(SHOULDER), mx(ELBOW), 0.052, 0.042, mat, root)
        _limb(kit, f"forearm_{side}", mx(ELBOW), mx(WRIST), 0.042, 0.032, mat, root)
        fore = mx(WRIST) - mx(ELBOW)
        hand_c = mx(WRIST) + fore.normalized() * 0.08
        _blob(kit, f"hand_{side}", hand_c, (0.027, 0.045, 0.09), mat, root, rot_deg=_euler_deg(fore))

        # leg: thigh and shin meet at the knee, the foot points toward -Y
        _limb(kit, f"thigh_{side}", mx(HIP), mx(KNEE), 0.078, 0.058, mat, root)
        _limb(kit, f"shin_{side}", mx(KNEE), mx(ANKLE), 0.058, 0.038, mat, root)
        _blob(kit, f"foot_{side}", (sx * ANKLE.x, -0.05, 0.045), (0.045, 0.13, 0.045), mat, root)
    return root

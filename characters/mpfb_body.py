"""The body of a character: an MPFB human with the game_engine rig, in metres, feet on z = 0.

Runs inside Blender with the vendored MPFB enabled (scripts/make_character.py sets that up).
`make_body(recipe)` returns (body, rig): a mesh of the basemesh without its helper geometry, its
shape keys baked, and the armature whose weights come from MPFB's own game_engine weight file.
"""

import bmesh
import bpy
from mathutils import Vector

MPFB = "bl_ext.user_default.mpfb"

# the game_engine rig has 30 finger bones and a toe-less foot: the game rig keeps the hand and
# the ball, and the weights of the finger bones go to the hand
FINGER_PREFIXES = ("thumb_", "index_", "middle_", "ring_", "pinky_")


def enable_mpfb():
    bpy.ops.preferences.addon_enable(module=MPFB)


def _macro_dict(recipe):
    from bl_ext.user_default.mpfb.services import TargetService
    macro = TargetService.get_default_macro_info_dict()
    for key, value in recipe.get("macro", {}).items():
        if key != "race":
            macro[key] = value
    macro["race"] = recipe.get("macro", {}).get("race", {"asian": 0.0, "caucasian": 1.0, "african": 0.0})
    return macro


def _vertex_bounds(obj, group="body"):
    index = obj.vertex_groups[group].index
    zs = [v.co.z for v in obj.data.vertices if any(g.group == index and g.weight > 0 for g in v.groups)]
    return min(zs), max(zs)


def make_body(recipe):
    enable_mpfb()
    from bl_ext.user_default.mpfb.services import HumanService, TargetService

    body = HumanService.create_human(mask_helpers=False, detailed_helpers=True, extra_vertex_groups=True,
                                     feet_on_ground=False, scale=0.1, macro_detail_dict=_macro_dict(recipe))
    TargetService.bake_targets(body)

    # scale the whole mesh (helpers included, so the rig fits it) to the recipe's height, feet on z = 0
    low, high = _vertex_bounds(body)
    factor = recipe.get("height_m", high - low) / (high - low)
    for v in body.data.vertices:
        v.co = Vector((v.co.x * factor, v.co.y * factor, (v.co.z - low) * factor))
    body.data.update()

    rig = HumanService.add_builtin_rig(body, "game_engine", import_weights=True)
    body.name = "body"
    rig.name = "rig"
    rig.data.name = "rig"
    return body, rig


def remove_helper_geometry(body):
    """Delete everything outside the 'body' vertex group: joint cubes, eye and teeth helpers."""
    index = body.vertex_groups["body"].index
    bm = bmesh.new()
    bm.from_mesh(body.data)
    deform = bm.verts.layers.deform.verify()
    doomed = [v for v in bm.verts if not any(i == index and w > 0.0 for i, w in v[deform].items())]
    bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    bm.to_mesh(body.data)
    bm.free()


def drop_unused_groups(body, rig, keep_bones):
    """Merge the finger weights into the hand and delete every vertex group that is not a kept bone."""
    for side in ("l", "r"):
        hand = body.vertex_groups.get(f"hand_{side}")
        fingers = [g for g in body.vertex_groups if g.name.endswith(f"_{side}") and g.name.startswith(FINGER_PREFIXES)]
        finger_idx = {g.index for g in fingers}
        for v in body.data.vertices:
            extra = sum(g.weight for g in v.groups if g.group in finger_idx)
            if extra > 0.0:
                hand.add([v.index], extra + (hand_weight(v, hand.index)), "REPLACE")
    for group in list(body.vertex_groups):
        if group.name not in keep_bones:
            body.vertex_groups.remove(group)


def hand_weight(vertex, index):
    return next((g.weight for g in vertex.groups if g.group == index), 0.0)


def remove_finger_bones(rig):
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for bone in list(rig.data.edit_bones):
        if bone.name.startswith(FINGER_PREFIXES):
            rig.data.edit_bones.remove(bone)
    bpy.ops.object.mode_set(mode="OBJECT")

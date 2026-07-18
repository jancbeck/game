#!/usr/bin/env python3
"""Build the playable convict character: mesh + armature + baked animations.

Generates art/models/convict.glb from nothing but primitives and the two
generated cloth textures (art/models/convict_cloth.png / convict_rag.png —
created once via tools/genart.py, committed like all art). One script owns
mesh, rig, AND animations, so the rig can never mismatch the mesh — the
failure mode that killed the previous prototype (docs/POSTMORTEM.md #6) was
third-party models retargeted onto third-party animation libraries.

Run locally (never in CI — Blender is not installed there; the .glb is a
committed build artifact):

    blender -b -P tools/build_convict.py              # build + render previews
    blender -b -P tools/build_convict.py -- --no-render

Preview renders land in reports/convict/ for eyeballing.

Character design (from art/sprites/convict.png): a lean prisoner in a
tattered olive-brown tunic with a ragged knee-length hem, bare calves and
feet, dark tousled hair, a forward hunch — and his signature: wrists bound
with rope, held together in front of him. The bind pose IS the sprite pose,
so every animation naturally keeps the wrists together.

Rig: 15 bones (hips/spine/head, 2x[upper_arm, forearm, hand],
2x[thigh, calf, foot]). Puppet-style rigid skinning: every mesh part is
weighted 100% to one bone, joint spheres hide the seams. Deterministic —
no auto-weight roulette.

Animations (30 fps, loop, in-place — locomotion is code-driven):
  idle (72f)  breathing, weight shift, slow head turns
  walk (20f)  leg stride cycle, hips bob, bound arms stay put
  talk (60f)  bound hands lift in a small gesture, head nods
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_GLB = os.path.join(ROOT, "art", "models", "convict.glb")
CLOTH_PNG = os.path.join(ROOT, "art", "models", "convict_cloth.png")
RAG_PNG = os.path.join(ROOT, "art", "models", "convict_rag.png")
RENDER_DIR = os.path.join(ROOT, "reports", "convict")

FPS = 30
TAU = math.tau


def srgb(r, g, b):
    """8-bit sRGB triple -> linear RGBA for Principled base color."""
    return tuple((c / 255.0) ** 2.2 for c in (r, g, b)) + (1.0,)


# ---------------------------------------------------------------- materials
def flat_material(name, rgb, roughness=0.9):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = rgb
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def cloth_material(name, image_path, use_alpha=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.95
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(image_path)
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if use_alpha:
        links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        # Ask for cutout rendering; the glTF exporter maps this to
        # alphaMode MASK (verified by inspecting the exported .glb).
        if hasattr(mat, "blend_method"):
            mat.blend_method = "CLIP"
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "DITHERED"
    return mat


# ------------------------------------------------------------------- meshes
def assign_bone(obj, bone_name):
    """Rigid puppet skinning: the whole part follows exactly one bone."""
    group = obj.vertex_groups.new(name=bone_name)
    group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = ARMATURE_OBJ
    obj.parent = ARMATURE_OBJ


def smooth(obj):
    for poly in obj.data.polygons:
        poly.use_smooth = True


def add_sphere(name, location, scale, mat, bone):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=24, ring_count=16, location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    smooth(obj)
    obj.data.materials.append(mat)
    assign_bone(obj, bone)
    return obj


def capsule_between(name, p1, p2, radius, mat, bone, joints=True):
    """A cylinder with sphere caps between two points — one object."""
    p1, p2 = Vector(p1), Vector(p2)
    axis = p2 - p1
    mid = (p1 + p2) / 2.0
    parts = []
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=16, radius=radius, depth=axis.length, location=mid
    )
    cyl = bpy.context.object
    cyl.rotation_mode = "QUATERNION"
    cyl.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(
        axis.normalized()
    )
    parts.append(cyl)
    if joints:
        for point in (p1, p2):
            bpy.ops.mesh.primitive_uv_sphere_add(
                segments=16, ring_count=12, radius=radius, location=point
            )
            parts.append(bpy.context.object)
    for part in parts:
        smooth(part)
    if len(parts) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for part in parts:
            part.select_set(True)
        bpy.context.view_layer.objects.active = cyl
        bpy.ops.object.join()
    cyl.name = name
    cyl.data.materials.append(mat)
    assign_bone(cyl, bone)
    return cyl


def add_cone(name, location, r1, r2, depth, mat, bone):
    bpy.ops.mesh.primitive_cone_add(
        vertices=24, radius1=r1, radius2=r2, depth=depth, location=location
    )
    obj = bpy.context.object
    obj.name = name
    smooth(obj)
    obj.data.materials.append(mat)
    assign_bone(obj, bone)
    return obj


def add_torus(name, location, direction, major, minor, mat, bone):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major,
        minor_radius=minor,
        major_segments=20,
        minor_segments=8,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(
        Vector(direction).normalized()
    )
    smooth(obj)
    obj.data.materials.append(mat)
    assign_bone(obj, bone)
    return obj


# -------------------------------------------------------------------- bones
# Rest pose = the sprite pose: slight hunch, wrists bound in front.
BONES = {
    # name: (head, tail, parent)
    "hips": ((0.0, 0.0, 0.95), (0.0, 0.0, 1.06), None),
    "spine": ((0.0, 0.0, 1.06), (0.0, 0.0, 1.36), "hips"),
    "head": ((0.0, 0.0, 1.44), (0.0, -0.03, 1.58), "spine"),
    "upper_arm.L": ((-0.23, 0.0, 1.38), (-0.30, -0.10, 1.12), "spine"),
    "forearm.L": ((-0.30, -0.10, 1.12), (-0.06, -0.30, 0.99), "upper_arm.L"),
    "hand.L": ((-0.06, -0.30, 0.99), (-0.015, -0.37, 0.97), "forearm.L"),
    "upper_arm.R": ((0.23, 0.0, 1.38), (0.30, -0.10, 1.12), "spine"),
    "forearm.R": ((0.30, -0.10, 1.12), (0.06, -0.30, 0.99), "upper_arm.R"),
    "hand.R": ((0.06, -0.30, 0.99), (0.015, -0.37, 0.97), "forearm.R"),
    "thigh.L": ((-0.11, 0.0, 0.95), (-0.115, 0.005, 0.56), "hips"),
    "calf.L": ((-0.115, 0.005, 0.56), (-0.12, 0.01, 0.14), "thigh.L"),
    "foot.L": ((-0.12, 0.01, 0.14), (-0.12, -0.16, 0.05), "calf.L"),
    "thigh.R": ((0.11, 0.0, 0.95), (0.115, 0.005, 0.56), "hips"),
    "calf.R": ((0.115, 0.005, 0.56), (0.12, 0.01, 0.14), "thigh.R"),
    "foot.R": ((0.12, 0.01, 0.14), (0.12, -0.16, 0.05), "calf.R"),
}

ARMATURE_OBJ = None


def build_armature():
    global ARMATURE_OBJ
    data = bpy.data.armatures.new("ConvictRig")
    obj = bpy.data.objects.new("ConvictRig", data)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    edit = {}
    for name, (head, tail, _parent) in BONES.items():
        bone = data.edit_bones.new(name)
        bone.head = head
        bone.tail = tail
        edit[name] = bone
    for name, (_h, _t, parent) in BONES.items():
        if parent:
            # Parent WITHOUT connect: connect snaps the child head onto the
            # parent tail, which would move non-coincident joints (shoulders,
            # thighs) off their authored positions.
            edit[name].parent = edit[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in obj.pose.bones:
        pb.rotation_mode = "XYZ"
    ARMATURE_OBJ = obj
    return obj


# ------------------------------------------------------------- construction
def build_mesh(mats):
    skin, hair, cloth, rag, pants, rope = mats

    # Tunic: torso + shoulder sleeves + skirt + ragged hem.
    add_sphere("Convict_Torso", (0, 0, 1.20), (0.23, 0.175, 0.30), cloth, "spine")
    add_sphere(
        "Convict_Sleeve_L", (-0.235, -0.01, 1.36), (0.085, 0.08, 0.09), cloth,
        "upper_arm.L",
    )
    add_sphere(
        "Convict_Sleeve_R", (0.235, -0.01, 1.36), (0.085, 0.08, 0.09), cloth,
        "upper_arm.R",
    )
    # Tall enough that its top ring stays buried inside the torso sphere —
    # a shorter skirt flashes a waist gap from behind.
    add_cone("Convict_Skirt", (0, 0.01, 0.76), 0.31, 0.20, 0.62, cloth, "hips")
    # The rag strip image is authored full-frame: solid cloth at v=1, tatter
    # tips at v=0 — so the cone maps the whole V range as authored.
    add_cone("Convict_RagHem", (0, 0.01, 0.52), 0.315, 0.295, 0.26, rag, "hips")

    # Head + tousled hair: a second sphere riding high and back, large
    # enough to sheath the whole back of the skull.
    add_sphere("Convict_Head", (0, 0.0, 1.665), (0.105, 0.10, 0.125), skin, "head")
    # High and slightly back: sheaths the crown and the back of the skull,
    # leaves the face — the sphere intersection IS the hairline.
    add_sphere(
        "Convict_Hair", (0, 0.03, 1.70), (0.115, 0.11, 0.11), hair, "head"
    )

    # Bare arms — the sprite's sleeves are torn off.
    capsule_between(
        "Convict_UpperArm_L", (-0.23, 0.0, 1.38), (-0.30, -0.10, 1.12), 0.052,
        skin, "upper_arm.L",
    )
    capsule_between(
        "Convict_UpperArm_R", (0.23, 0.0, 1.38), (0.30, -0.10, 1.12), 0.052,
        skin, "upper_arm.R",
    )
    capsule_between(
        "Convict_Forearm_L", (-0.30, -0.10, 1.12), (-0.06, -0.30, 0.99), 0.046,
        skin, "forearm.L",
    )
    capsule_between(
        "Convict_Forearm_R", (0.30, -0.10, 1.12), (0.06, -0.30, 0.99), 0.046,
        skin, "forearm.R",
    )
    add_sphere(
        "Convict_Fist_L", (-0.03, -0.345, 0.975), (0.05, 0.062, 0.052), skin,
        "hand.L",
    )
    add_sphere(
        "Convict_Fist_R", (0.03, -0.345, 0.975), (0.05, 0.062, 0.052), skin,
        "hand.R",
    )

    # The rope: a ring lashed around each wrist plus a dangling loose end.
    wrist_l = Vector((-0.06, -0.30, 0.99))
    wrist_r = Vector((0.06, -0.30, 0.99))
    forearm_l_dir = wrist_l - Vector((-0.30, -0.10, 1.12))
    forearm_r_dir = wrist_r - Vector((0.30, -0.10, 1.12))
    add_torus(
        "Convict_Rope_L", wrist_l, forearm_l_dir, 0.062, 0.023, rope, "hand.L"
    )
    add_torus(
        "Convict_Rope_R", wrist_r, forearm_r_dir, 0.062, 0.023, rope, "hand.R"
    )
    # Loose tail hanging off the right wrist: three links + a knot.
    tail_pts = [
        (0.045, -0.335, 0.945),
        (0.05, -0.33, 0.885),
        (0.045, -0.325, 0.825),
    ]
    for i in range(len(tail_pts) - 1):
        capsule_between(
            "Convict_RopeTail_%d" % i, tail_pts[i], tail_pts[i + 1], 0.013,
            rope, "hand.R", joints=False,
        )
    add_sphere(
        "Convict_RopeKnot", tail_pts[-1], (0.02, 0.02, 0.028), rope, "hand.R"
    )

    # Legs: dark ragged trousers under the skirt, bare calves and feet.
    capsule_between(
        "Convict_Thigh_L", (-0.11, 0.0, 0.95), (-0.115, 0.005, 0.56), 0.075,
        pants, "thigh.L",
    )
    capsule_between(
        "Convict_Thigh_R", (0.11, 0.0, 0.95), (0.115, 0.005, 0.56), 0.075,
        pants, "thigh.R",
    )
    capsule_between(
        "Convict_Calf_L", (-0.115, 0.005, 0.56), (-0.12, 0.01, 0.14), 0.052,
        skin, "calf.L",
    )
    capsule_between(
        "Convict_Calf_R", (0.115, 0.005, 0.56), (0.12, 0.01, 0.14), 0.052,
        skin, "calf.R",
    )
    # Bare feet, near-horizontal so the convict stands flat, not en pointe.
    capsule_between(
        "Convict_Foot_L", (-0.12, 0.005, 0.075), (-0.12, -0.155, 0.048), 0.042,
        skin, "foot.L",
    )
    capsule_between(
        "Convict_Foot_R", (0.12, 0.005, 0.075), (0.12, -0.155, 0.048), 0.042,
        skin, "foot.R",
    )


# --------------------------------------------------------------- animations
def new_action(name, armature):
    action = bpy.data.actions.new(name)
    armature.animation_data.action = action
    return action


def key(armature, bone, frame, rot=None, loc=None):
    pb = armature.pose.bones[bone]
    if rot is not None:
        pb.rotation_euler = rot
        pb.keyframe_insert("rotation_euler", frame=frame)
    if loc is not None:
        pb.location = loc
        pb.keyframe_insert("location", frame=frame)


def clear_pose(armature):
    for pb in armature.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)


def anim_idle(armature):
    """72 frames: breathing, weight shift, a slow wary look around."""
    new_action("idle", armature)
    clear_pose(armature)
    # frame: (spine_x_hunch, hips_z_roll, head_yaw, head_pitch)
    keys = [
        (0, 0.14, 0.00, 0.00, 0.02),
        (18, 0.16, 0.045, 0.18, 0.03),
        (36, 0.14, 0.00, 0.00, 0.02),
        (54, 0.12, -0.045, -0.15, 0.01),
        (72, 0.14, 0.00, 0.00, 0.02),
    ]
    for frame, hunch, roll, yaw, pitch in keys:
        key(armature, "spine", frame, rot=(hunch, 0, 0))
        key(armature, "hips", frame, rot=(0, 0, roll))
        # Head yaw is a twist around the (vertical) bone's local Y axis.
        key(armature, "head", frame, rot=(pitch, yaw, 0))
        # Bound hands breathe along, barely.
        bob = 0.0 if frame in (0, 36, 72) else 0.012
        key(armature, "hand.L", frame, loc=(0, 0, bob))
        key(armature, "hand.R", frame, loc=(0, 0, bob))
        # Every other bone holds the bound rest pose; key it so the clip
        # never falls back to a raw rest pose mid-blend.
        for bone in BONES:
            if bone not in ("spine", "hips", "head", "hand.L", "hand.R"):
                key(armature, bone, frame, rot=(0, 0, 0), loc=(0, 0, 0))


def anim_walk(armature):
    """20-frame stride. Legs do the work; bound arms only counter-sway."""
    new_action("walk", armature)
    clear_pose(armature)
    # Kept modest: a wider stride pulls the thighs out from under the
    # skirt's silhouette and opens a gap at the hip.
    swing = 0.45
    # frame: phase within the cycle (0 = left contact forward).
    for frame, t in [(0, 0.0), (5, 0.25), (10, 0.5), (15, 0.75), (20, 1.0)]:
        phase = TAU * t
        s = math.sin(phase)
        # Thigh bones point DOWN: a positive local-X rotation swings the leg
        # backward, so forward swing takes the negative sign.
        key(armature, "thigh.L", frame, rot=(-swing * s, 0, 0))
        key(armature, "thigh.R", frame, rot=(swing * s, 0, 0))
        # Knee folds (heel back) with positive local-X; it folds most while
        # the leg swings through, least at front contact.
        bend_l = 0.15 + 0.45 * max(0.0, -s)
        bend_r = 0.15 + 0.45 * max(0.0, s)
        key(armature, "calf.L", frame, rot=(bend_l, 0, 0))
        key(armature, "calf.R", frame, rot=(bend_r, 0, 0))
        key(armature, "foot.L", frame, rot=(0.3 * s - 0.1, 0, 0))
        key(armature, "foot.R", frame, rot=(-0.3 * s - 0.1, 0, 0))
        # Hips bob on the passing poses and roll into the stance leg.
        bob = 0.035 * abs(math.cos(phase))
        key(armature, "hips", frame, rot=(0, 0, 0.055 * s), loc=(0, 0, bob))
        # Hunched lean plus counter-roll; the bound unit barely sways.
        key(armature, "spine", frame, rot=(0.19, 0, -0.045 * s))
        key(armature, "head", frame, rot=(-0.05, 0, 0.03 * s))
        key(armature, "upper_arm.L", frame, rot=(-0.06 * s, 0, 0))
        key(armature, "upper_arm.R", frame, rot=(0.06 * s, 0, 0))
        key(armature, "forearm.L", frame, rot=(0, 0, 0), loc=(0, 0, 0))
        key(armature, "forearm.R", frame, rot=(0, 0, 0), loc=(0, 0, 0))
        key(armature, "hand.L", frame, rot=(0, 0, 0), loc=(0, 0, 0))
        key(armature, "hand.R", frame, rot=(0, 0, 0), loc=(0, 0, 0))


def anim_talk(armature):
    """60 frames: leans in, bound hands lift in a small plea, head nods."""
    new_action("talk", armature)
    clear_pose(armature)
    # frame: (spine_lean, hands_lift, hands_fwd, head_pitch, head_yaw)
    keys = [
        (0, 0.16, 0.00, 0.00, 0.02, 0.00),
        (15, 0.20, 0.055, -0.03, 0.07, 0.05),
        (30, 0.17, 0.01, 0.00, -0.02, 0.00),
        (45, 0.20, 0.045, -0.02, 0.06, -0.06),
        (60, 0.16, 0.00, 0.00, 0.02, 0.00),
    ]
    for frame, lean, lift, fwd, pitch, yaw in keys:
        key(armature, "spine", frame, rot=(lean, 0, 0))
        key(armature, "hips", frame, rot=(0, 0, 0), loc=(0, 0, 0))
        # Head yaw is a twist around the (vertical) bone's local Y axis.
        key(armature, "head", frame, rot=(pitch, yaw, 0))
        key(armature, "hand.L", frame, rot=(-0.25 * lift * 10, 0, 0), loc=(0, fwd, lift))
        key(armature, "hand.R", frame, rot=(-0.25 * lift * 10, 0, 0), loc=(0, fwd, lift))
        key(armature, "forearm.L", frame, rot=(0.1 * lift * 10, 0, 0))
        key(armature, "forearm.R", frame, rot=(0.1 * lift * 10, 0, 0))
        for bone in ("upper_arm.L", "upper_arm.R"):
            key(armature, bone, frame, rot=(0, 0, 0), loc=(0, 0, 0))
        for bone in ("thigh.L", "thigh.R", "calf.L", "calf.R", "foot.L", "foot.R"):
            key(armature, bone, frame, rot=(0, 0, 0), loc=(0, 0, 0))


# ------------------------------------------------------------------ renders
def render_previews(armature):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 560
    scene.render.resolution_y = 640
    scene.render.film_transparent = False
    world = bpy.data.worlds.new("Preview")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (
        0.012,
        0.010,
        0.014,
        1.0,
    )
    scene.world = world

    def area(name, location, energy, color, size=3.0):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.color = color
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        obj.location = location
        bpy.context.collection.objects.link(obj)
        # Point the light at the torso.
        direction = Vector((0, 0, 1.0)) - obj.location
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        return obj

    # Warm key from front-left (the yard's fires), cool rim from back-right.
    area("Key", (-1.6, -2.2, 2.6), 700, (1.0, 0.62, 0.38))
    area("Rim", (1.8, 1.4, 2.4), 500, (0.35, 0.45, 0.75))

    cam_data = bpy.data.cameras.new("PreviewCam")
    cam = bpy.data.objects.new("PreviewCam", cam_data)
    cam.location = (1.35, -3.1, 1.55)
    target = Vector((0, 0, 0.95))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = 58
    bpy.context.collection.objects.link(cam)
    scene.camera = cam

    os.makedirs(RENDER_DIR, exist_ok=True)
    shots = [
        ("pose_bind", None, 0),
        ("pose_idle", "idle", 36),
        ("pose_walk", "walk", 5),
        ("pose_talk", "talk", 15),
    ]
    actions = {a.name: a for a in bpy.data.actions}
    for name, action_name, frame in shots:
        armature.animation_data.action = actions.get(action_name)
        scene.frame_set(frame)
        scene.render.filepath = os.path.join(RENDER_DIR, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)

    # Side view: the front-3/4 camera foreshortens forward-pointing feet
    # into a diagonal that reads as "en pointe" — the profile shot is the
    # honest check for foot angle and hunch.
    cam.location = (-3.1, 0.0, 1.2)
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    armature.animation_data.action = actions.get("walk")
    scene.frame_set(5)
    scene.render.filepath = os.path.join(RENDER_DIR, "pose_walk_side.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", scene.render.filepath)


# --------------------------------------------------------------------- main
def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS

    armature = build_armature()
    armature.animation_data_create()

    mats = (
        flat_material("Skin", srgb(170, 122, 76), 0.75),
        flat_material("Hair", srgb(34, 28, 24), 0.85),
        cloth_material("Tunic", CLOTH_PNG),
        cloth_material("RagHem", RAG_PNG, use_alpha=True),
        flat_material("Trousers", srgb(74, 61, 44), 0.95),
        flat_material("Rope", srgb(110, 76, 36), 0.9),
    )
    build_mesh(mats)

    anim_idle(armature)
    anim_walk(armature)
    anim_talk(armature)
    clear_pose(armature)

    if "--no-render" not in sys.argv:
        render_previews(armature)

    bpy.ops.export_scene.gltf(
        filepath=OUT_GLB,
        export_format="GLB",
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_force_sampling=True,
        export_image_format="AUTO",
        export_yup=True,
        export_apply=True,
    )
    print("wrote", OUT_GLB)


main()

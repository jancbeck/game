"""Quick CPU views of the character in the scene (Cycles on the CPU, so no GPU queue).

`preview(rig, out_dir)` renders the rest pose from four sides, a head close-up and every clip as a
strip of frames; scripts/make_character.py --preview runs it after the export.
"""
import math, bpy
from mathutils import Vector


def setup(res=(420, 640), samples=12):
    for n in ("Cube", "Camera", "Light"):
        if n in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[n])
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    w = bpy.data.worlds.new("w") if not sc.world else sc.world
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.55, 0.6, 0.7, 1)
    bg.inputs[1].default_value = 1.0
    if "devsun" not in bpy.data.objects:
        sun = bpy.data.lights.new("devsun", "SUN")
        sun.energy = 3.0
        o = bpy.data.objects.new("devsun", sun)
        bpy.context.collection.objects.link(o)
        o.rotation_euler = (math.radians(50), 0, math.radians(-30))
    if "devcam" not in bpy.data.objects:
        cam = bpy.data.cameras.new("devcam")
        cam.type = "ORTHO"
        o = bpy.data.objects.new("devcam", cam)
        bpy.context.collection.objects.link(o)
    sc.camera = bpy.data.objects["devcam"]
    return sc


def shot(path, yaw_deg=0, center=(0, 0, 0.9), ortho=2.0, pitch=0.0):
    sc = bpy.context.scene
    cam = bpy.data.objects["devcam"]
    cam.data.ortho_scale = ortho
    # character faces -Y; yaw 0 = camera in front (at -Y), looking +Y
    d = 6.0
    a = math.radians(yaw_deg)
    p = math.radians(pitch)
    pos = Vector((math.sin(a) * math.cos(p), -math.cos(a) * math.cos(p), math.sin(p))) * d + Vector(center)
    cam.location = pos
    direction = Vector(center) - pos
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def lit_still(rig, action, path, frame_k=0.0, res=(1400, 900)):
    """A lying figure on a plank floor in the game's camera (38 degrees up, 11 degrees yaw), lit by a warm
    lamp and a dim blue sky, like the place it sleeps in."""
    sc = setup(res=res, samples=48)
    sc.cycles.use_denoising = False
    w = sc.world.node_tree.nodes["Background"]
    w.inputs[0].default_value = (0.05, 0.07, 0.12, 1)
    w.inputs[1].default_value = 1.0
    if "devsun" in bpy.data.objects:
        bpy.data.objects["devsun"].data.energy = 0.0
    floor = bpy.data.objects.get("floor")
    if floor is None:
        bpy.ops.mesh.primitive_plane_add(size=6.0, location=(0, 0, 0))
        floor = bpy.context.active_object
        floor.name = "floor"
        mat = bpy.data.materials.new("planks")
        mat.use_nodes = True
        nt = mat.node_tree
        wave = nt.nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.inputs["Scale"].default_value = 16.0
        wave.inputs["Distortion"].default_value = 2.0
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (0.035, 0.022, 0.014, 1)
        ramp.color_ramp.elements[1].color = (0.075, 0.048, 0.030, 1)
        nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
        nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
        floor.data.materials.append(mat)
    lamp = bpy.data.objects.get("lamp")
    if lamp is None:
        data = bpy.data.lights.new("lamp", "POINT")
        data.energy = 120.0
        data.color = (1.0, 0.62, 0.32)
        data.shadow_soft_size = 0.12
        lamp = bpy.data.objects.new("lamp", data)
        bpy.context.collection.objects.link(lamp)
    lamp.location = (0.6, -0.9, 0.9)
    rig.rotation_euler = (0, 0, -math.pi / 2)         # the body lies across the view, head to the left
    rig.animation_data.action = action
    start, end = action.frame_range
    sc.frame_set(int(start + (end - start) * frame_k))
    cam = bpy.data.objects["devcam"]
    cam.data.ortho_scale = 2.6
    yaw, el = math.radians(11), math.radians(38)
    d = 8.0
    centre = Vector((0, 0, 0.25))
    pos = centre + Vector((math.sin(yaw) * math.cos(el), -math.cos(yaw) * math.cos(el), math.sin(el))) * d
    cam.location = pos
    cam.rotation_euler = (centre - pos).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    rig.rotation_euler = (0, 0, 0)


def preview(rig, out_dir):
    import os
    os.makedirs(out_dir, exist_ok=True)
    setup()
    rig.animation_data_create()
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    for name, yaw in (("front", 0), ("side", 90), ("back", 180), ("q", 35)):
        shot(f"{out_dir}/rest_{name}.png", yaw)
    top = max(v.co.z for v in rig.children[0].data.vertices) if rig.children else 1.8
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 640, 640
    shot(f"{out_dir}/head.png", 25, center=(0, 0, top - 0.12), ortho=0.5)
    shot(f"{out_dir}/head_front.png", 0, center=(0, 0, top - 0.12), ortho=0.5)
    shot(f"{out_dir}/arm.png", 30, center=(0.40, 0, top * 0.62), ortho=0.7)
    sc.render.resolution_x, sc.render.resolution_y = 420, 640
    for action in list(bpy.data.actions):
        clip = action.name
        lying = clip.startswith(("sleep", "rest"))
        rig.animation_data.action = action
        start, end = action.frame_range
        count = 4 if lying else 8
        for k in range(count):
            bpy.context.scene.frame_set(int(start + (end - start) * k / count))
            if lying:
                # from the side, from above and from the foot end, at the figure's own scale
                shot(f"{out_dir}/{clip}_{k}.png", 90, center=(0, 0, 0.3), ortho=2.4, pitch=25)
                shot(f"{out_dir}/{clip}_top_{k}.png", 90, center=(0, 0, 0.3), ortho=2.4, pitch=80)
                shot(f"{out_dir}/{clip}_foot_{k}.png", 160, center=(0, 0, 0.3), ortho=2.4, pitch=30)
            else:
                shot(f"{out_dir}/{clip}_{k}.png", 90 if clip == "walk" else 20)
        if lying:
            lit_still(rig, action, f"{out_dir}/{clip}_still.png")
            setup()


def sketch(rig, out_dir, clips=None, frames=6, views=((90, "side"), (35, "q"), (180, "back")), res=(360, 560), fits=None):
    """Fast Workbench stills (vertex colours, studio light, no GPU queue) of the rest pose and of
    each clip's frames from a few yaws: for judging shapes (a skirt in a stride, a cloak on the
    floor). `clips` limits the clips; lying clips are shot from above at an angle."""
    import os
    os.makedirs(out_dir, exist_ok=True)
    sc = setup(res=res)
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "VERTEX"
    sh.show_cavity = True
    sc.render.film_transparent = False
    sc.world.color = (0.35, 0.37, 0.42)
    rig.animation_data_create()
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    for yaw, name in views:
        shot(f"{out_dir}/rest_{name}.png", yaw)
    top = max(v.co.z for v in rig.children[0].data.vertices) if rig.children else 1.8
    for yaw, name in ((0, "front"), (50, "q"), (130, "back")):
        shot(f"{out_dir}/head_{name}.png", yaw, center=(0, 0, top - 0.11), ortho=0.42)
    for action in list(bpy.data.actions):
        clip = action.name
        if clips and clip not in clips:
            continue
        lying = clip.startswith(("sleep", "rest"))
        rig.animation_data.action = action
        start, end = action.frame_range
        for k in range(frames):
            frame = int(start + (end - start) * k / frames)
            bpy.context.scene.frame_set(frame)
            if fits is not None:
                import posefit
                posefit.apply_weights(rig.children[0], fits, clip, frame)
                bpy.context.view_layer.update()
            if lying:
                shot(f"{out_dir}/{clip}_side_{k}.png", 90, center=(0, 0, 0.3), ortho=2.4, pitch=25)
                shot(f"{out_dir}/{clip}_top_{k}.png", 35, center=(0, 0, 0.3), ortho=2.4, pitch=55)
                shot(f"{out_dir}/{clip}_cam_{k}.png", 160, center=(0, 0, 0.25), ortho=2.6, pitch=38)
                shot(f"{out_dir}/{clip}_cam2_{k}.png", 20, center=(0, 0, 0.25), ortho=2.6, pitch=38)
            else:
                for yaw, name in views:
                    shot(f"{out_dir}/{clip}_{name}_{k}.png", yaw, center=(0, 0, 0.8), ortho=2.2)

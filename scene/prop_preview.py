"""Render one procedural prop on its own, from an angle close to the scene camera.

    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python scene/prop_preview.py -- gallows
    -> renders/props/gallows.png (768x768), compare with props/crops/gallows.png

    ... --python scene/prop_preview.py -- --swatches
    -> renders/props/_swatches.png, one sphere per material in the library
"""

import math
import random
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scene"))

import assets  # noqa: E402
import kit  # noqa: E402
from materials import SPECS, Materials  # noqa: E402

OUT = ROOT / "renders" / "props"


def setup_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    world = bpy.data.worlds.new("w")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.06, 0.07, 0.09, 1)
    key = bpy.data.objects.new("key", bpy.data.lights.new("key", "SUN"))
    key.data.energy = 3.5
    key.data.color = (1.0, 0.92, 0.82)
    key.rotation_euler = (math.radians(50), 0, math.radians(-35))
    bpy.context.collection.objects.link(key)
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
    fill.data.energy = 1.0
    fill.data.color = (0.6, 0.7, 1.0)
    fill.rotation_euler = (math.radians(60), 0, math.radians(140))
    bpy.context.collection.objects.link(fill)
    floor = kit.box("floor", (40, 40, 0.02), (0, 0, -0.011))
    mat = bpy.data.materials.new("floor")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.08, 0.08, 0.08, 1)
    floor.data.materials.append(mat)


def bbox(objs):
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    deps = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.evaluated_get(deps).bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def frame_camera(lo, hi):
    center = (lo + hi) / 2
    radius = (hi - lo).length / 2
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.lens = 50
    bpy.context.collection.objects.link(cam)
    # elevated, slightly from the left: the scene camera looks north and down ~50 degrees
    direction = Vector((-0.30, -1.0, 1.15)).normalized()
    cam.location = center + direction * radius * 3.1
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam


def render(path):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = 32
    sc.render.resolution_x = sc.render.resolution_y = 768
    sc.view_settings.look = "AgX - Punchy"
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def preview_prop(name):
    setup_stage()
    mats = Materials()
    mod = assets.load(name)
    t0 = time.time()
    root = mod.build(kit, mats, random.Random(7))
    build_s = time.time() - t0
    bpy.context.view_layer.update()
    parts = [o for o in bpy.data.objects if o.type == "MESH" and o.name != "floor"]
    lo, hi = bbox(parts)
    for pos, color, watts in getattr(mod, "LIGHTS", []):
        li = bpy.data.objects.new(f"pl_{name}", bpy.data.lights.new(f"pl_{name}", "POINT"))
        li.data.color = color
        li.data.energy = watts
        li.location = root.matrix_world @ Vector(pos)
        bpy.context.collection.objects.link(li)
    frame_camera(lo, hi)
    out = OUT / f"{name}.png"
    render(out)
    size = hi - lo
    print(f"PREVIEW {name}: parts={len(parts)} size=({size.x:.2f}, {size.y:.2f}, {size.z:.2f}) m "
          f"min_z={lo.z:.2f} build={build_s:.2f}s -> {out.relative_to(ROOT)}")


def preview_swatches():
    setup_stage()
    mats = Materials()
    keys = list(SPECS)
    cols = 4
    for i, key in enumerate(keys):
        x, y = (i % cols) * 1.3, -(i // cols) * 1.3
        kit.sphere(f"sw_{key}", 0.5, (x, y, 0.5), mat=mats[key], segments=32)
        kit.box(f"swb_{key}", (0.5, 0.5, 0.5), (x + 0.45, y + 0.35, 0.25), mat=mats[key])
    parts = [o for o in bpy.data.objects if o.type == "MESH" and o.name != "floor"]
    frame_camera(*bbox(parts))
    out = OUT / "_swatches.png"
    render(out)
    print("SWATCHES", ", ".join(keys), "->", out.relative_to(ROOT))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    OUT.mkdir(parents=True, exist_ok=True)
    if argv and argv[0] == "--swatches":
        preview_swatches()
    else:
        preview_prop(argv[0])


main()

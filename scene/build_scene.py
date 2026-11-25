"""Build a location from its plan.json and render one frame.

    /Applications/Blender.app/Contents/MacOS/Blender --background --python scene/build_scene.py -- \
        --out renders/iter_003.png [--location courtyard] [--view ref|plan|eye] [--check-scale] \
        [--layout locations/courtyard/layout_preview.json] [--percent 50]

plan.json is the place in meters, designed for realism. trace.json holds the orthographic
camera matched to the reference, used by the default `ref` view. The files come from
locations/<location>/ (scene/location.py).

Views:
  ref   the reference camera; compare against ref/courtyard.webp
  plan  straight down, to judge the layout as a floor plan (location.json views.plan)
  eye   a person standing in the courtyard (location.json views.eye)

--check-scale adds 1.8 m cyan figures next to the props. `build_world()` is the shared scene
build that game_frame.py uses too.
"""

import argparse
import json
import math
import random
import zlib
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scene"))

import assets  # noqa: E402
import kit  # noqa: E402
import location  # noqa: E402
import terrain  # noqa: E402
from materials import Materials  # noqa: E402
from planlib import entries, height, inside_polygon, resolve_block  # noqa: E402

LIGHT_SCALE = 1.0


# ---------- cameras ----------

def ortho_camera(spec, still_res, ortho_scale, sensor_fit=None):
    """The traced orthographic camera, shifted so that pixel `center_px` of a `still_res` image sees
    the world origin, `ortho_scale` metres wide. A frame of another size keeps that image centre."""
    th, ps = math.radians(spec["elevation_deg"]), math.radians(spec["yaw_deg"])
    s = spec["px_per_m"]
    view = Vector((math.cos(th) * math.sin(ps), math.cos(th) * math.cos(ps), -math.sin(th)))
    right = Vector((math.cos(ps), -math.sin(ps), 0))
    up = Vector((math.sin(th) * math.sin(ps), math.sin(th) * math.cos(ps), math.cos(th)))
    cu, cv = spec["center_px"]
    offset = right * ((still_res[0] / 2 - cu) / s) + up * ((cv - still_res[1] / 2) / s)
    data = bpy.data.cameras.new("cam")
    data.type = "ORTHO"
    data.ortho_scale = ortho_scale
    if sensor_fit:
        data.sensor_fit = sensor_fit
    data.clip_end = 500
    cam = bpy.data.objects.new("cam", data)
    cam.rotation_euler = (math.pi / 2 - th, 0, -ps)
    # 45 m clears the castle and keeps the camera above the haze box
    cam.location = offset - view * 45
    return cam


def camera_ref(spec, res):
    """The reference camera at the still's own size."""
    return ortho_camera(spec, res, res[0] / spec["px_per_m"])


def camera_view(view):
    """Camera of a location.json `views` entry: perspective when it has a lens, else orthographic."""
    return camera_eye(view) if "lens" in view else camera_plan(view)


def camera_plan(view):
    data = bpy.data.cameras.new("cam")
    data.type = "ORTHO"
    data.ortho_scale = view["ortho_scale"]
    data.clip_end = 500
    cam = bpy.data.objects.new("cam", data)
    cam.location = view["location"]
    return cam


def camera_eye(view):
    data = bpy.data.cameras.new("cam")
    data.lens = view["lens"]
    data.clip_end = 500
    cam = bpy.data.objects.new("cam", data)
    cam.location = view["location"]
    target = Vector(view["target"])
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    return cam


def install_camera(cam, res):
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    r = bpy.context.scene.render
    r.resolution_x, r.resolution_y = res


# ---------- architecture ----------

PERCHES = []  # merlon tops (x, y, z, rot_z) where crows can sit
FOOTPRINTS = []  # (center, half size, rot_z rad, top z) of every block, to drop buried perches


def _buried(x, y, z):
    for (cx, cy), (hw, hd), rot, top in FOOTPRINTS:
        dx, dy = x - cx, y - cy
        lx = dx * math.cos(rot) + dy * math.sin(rot)
        ly = -dx * math.sin(rot) + dy * math.cos(rot)
        if abs(lx) < hw - 0.05 and abs(ly) < hd - 0.05 and top > z - 0.3:
            return True
    return False


def build_block(name, b, mats, heights, merlon):
    stone = mats["stone_wall"]
    rng = random.Random(name)
    base = b.get("base", heights["lower_ward"])
    # h_offset lowers a block by a few mm where it meets another of the same height, so the two tops are
    # not coplanar: a path tracer shades a face that lies inside another solid as black
    h = height(b["h"], heights) + b.get("h_offset", 0.0)
    b = resolve_block(b)
    w, d = b["size"]
    rot = math.radians(b.get("rot_z", 0))
    cx, cy = b["center"]
    FOOTPRINTS.append(((cx, cy), (w / 2, d / 2), rot, h))
    ob = kit.box(f"block_{name}", (w, d, h - base), (cx, cy, (h + base) / 2),
                 (0, 0, b.get("rot_z", 0)), stone, bevel=0.03)

    # battered plinth: the wall foot flares out where it stands on the lower ward; parapets have none
    if h - base > 5.0:
        flare, top = 0.5, base + 2.4
        hw, hd = w / 2, d / 2
        verts = [(-hw - flare, -hd - flare, base), (hw + flare, -hd - flare, base),
                 (hw + flare, hd + flare, base), (-hw - flare, hd + flare, base),
                 (-hw, -hd, top), (hw, -hd, top), (hw, hd, top), (-hw, hd, top)]
        faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        kit.mesh(f"plinth_{name}", verts, faces, (cx, cy, 0), (0, 0, b.get("rot_z", 0)), stone, bevel=0.03)

    # battlements on the chosen top edges, in the block's local frame
    ux, uy = Vector((math.cos(rot), math.sin(rot), 0)), Vector((-math.sin(rot), math.cos(rot), 0))
    md, step = merlon["depth"], merlon["w"] + merlon["gap"]
    edges = b.get("merlons", [])
    if "all" in edges:
        edges = ["+x", "-x", "+y", "-y"]
    for edge in edges:
        if edge in ("+y", "-y", "center"):
            length, along = w, ux
            off = uy * {"+y": d / 2 - md / 2, "-y": -(d / 2 - md / 2), "center": 0}[edge]
        else:
            length, along = d, uy
            off = ux * (w / 2 - md / 2) * (1 if edge == "+x" else -1)
            # the +y/-y runs own the corners; ending short of them keeps faces from lying inside them
            length -= md * sum(e in edges for e in ("+y", "-y"))
            off += uy * (md / 2) * (("-y" in edges) - ("+y" in edges))
        # breast-high parapet along the edge; merlons stand on it, crenels open above it
        ph = 0.0 if edge == "center" else merlon.get("parapet", 0.0)
        if ph:
            c = Vector((cx, cy, 0)) + off
            size = (length, md, ph) if along == ux else (md, length, ph)
            kit.box(f"parapet_{name}_{edge}", size, (c.x, c.y, h + ph / 2), (0, 0, b.get("rot_z", 0)),
                    stone, bevel=0.03)
        n = max(1, int((length + merlon["gap"]) // step))
        start = -(n - 1) * step / 2
        inward = -off.normalized() if off.length > 1e-6 else Vector((0, 0, 0))
        rz = b.get("rot_z", 0)
        for i in range(n):
            p = Vector((cx, cy, 0)) + off + along * (start + i * step)
            # a fallen merlon leaves a stump and its stones on the wall-walk
            if rng.random() < merlon.get("missing", 0.0):
                kit.box(f"merlon_{name}_{edge}_{i}_stump", (merlon["w"] * 0.9, md * 0.9, 0.12),
                        (p.x, p.y, h + ph + 0.06), (0, 0, rz + rng.uniform(-4, 4)), stone, bevel=0.03)
                for k in range(rng.randint(2, 4)):
                    q = p + inward * rng.uniform(0.5, 1.1) + along * rng.uniform(-0.5, 0.5)
                    s = rng.uniform(0.16, 0.3)
                    kit.box(f"merlon_{name}_{edge}_{i}_rubble{k}", (s, s * 0.8, s * 0.6),
                            (q.x, q.y, h + s * 0.3), (rng.uniform(-15, 15), rng.uniform(-15, 15), rng.uniform(0, 90)),
                            stone, bevel=0.03)
                continue
            # hand-laid and weathered: no two merlons quite alike, a few broken down or leaning
            mh = merlon["h"] * rng.uniform(0.85, 1.12)
            tilt = (rng.uniform(-1.5, 1.5), rng.uniform(-1.5, 1.5))
            broken = rng.random() < merlon.get("broken", 0.0)
            if broken:
                mh *= rng.uniform(0.35, 0.7)
                tilt = (rng.uniform(-6, 6), rng.uniform(-6, 6))
            elif rng.random() < merlon.get("leaning", 0.0):
                tilt = (rng.uniform(-4, 4), rng.uniform(-4, 4))
            mw = merlon["w"] * rng.uniform(0.88, 1.08)
            size = (mw, md, mh) if along == ux else (md, mw, mh)
            kit.box(f"merlon_{name}_{edge}_{i}", size, (p.x, p.y, h + ph + mh / 2),
                    (*tilt, rz + rng.uniform(-2, 2)), stone, bevel=0.05)
            top = h + ph + mh
            # coping stone: a slightly wider slab that sheds rain, on most intact merlons
            if not broken and rng.random() < merlon.get("coping", 0.0):
                ct = rng.uniform(0.07, 0.11)
                csize = (mw + 0.08, md + 0.08, ct) if along == ux else (md + 0.08, mw + 0.08, ct)
                kit.box(f"merlon_{name}_{edge}_{i}_cap", csize, (p.x, p.y, top + ct / 2),
                        (*tilt, rz + rng.uniform(-3, 3)), stone, bevel=0.025)
                top += ct
            if not broken:
                PERCHES.append((p.x, p.y, top, rz))

    if "cut_gate" in b:
        g = b["cut_gate"]
        face_y = cy - d / 2
        r = g["width"] / 2
        cutters = [
            kit.box(f"cut_{name}_rect", (g["width"], 2.4, g["spring"] + 0.2), (g["x"], face_y, g["spring"] / 2 - 0.1)),
            kit.cylinder(f"cut_{name}_arch", r, 2.4, (g["x"], face_y, g["spring"]), (90, 0, 0), segments=32),
        ]
    else:
        cutters = []

    # arrow slits: narrow recesses [face, offset along the face, center height]
    for i, (face, along_off, zc) in enumerate(b.get("slits", [])):
        normal = {"+x": ux, "-x": -ux, "+y": uy, "-y": -uy}[face]
        half = (w if face in ("+x", "-x") else d) / 2
        along = uy if face in ("+x", "-x") else ux
        p = Vector((cx, cy, 0)) + normal * half + along * along_off
        size = (0.8, 0.13, 1.1) if face in ("+x", "-x") else (0.13, 0.8, 1.1)
        cutters.append(kit.box(f"slit_{name}_{i}", size, (p.x, p.y, zc), (0, 0, b.get("rot_z", 0))))

    if cutters:
        for c in cutters:
            mod = ob.modifiers.new(c.name, "BOOLEAN")
            mod.operation = "DIFFERENCE"
            mod.object = c
            c.hide_render = True
            c.display_type = "WIRE"
    return ob


def build_terrain(mats):
    """Ground outside the walls: a mound at the wall feet, the cliff on the south, mud farther out (terrain.py).

    The grid is finer near the castle, where the mound meets the battered plinths.
    """
    import bmesh
    half, fine, coarse, inner = 70.0, 0.5, 1.0, 26.0
    xs, x = [], -half
    while x < half + 1e-6:
        xs.append(x)
        x += fine if abs(x) < inner else coarse
    bm = bmesh.new()
    rows = []
    for y in xs:
        rows.append([bm.verts.new((x, y, terrain.ground_z(x, y))) for x in xs])
    for j in range(len(xs) - 1):
        for i in range(len(xs) - 1):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    me = bpy.data.meshes.new("terrain")
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    ob = bpy.data.objects.new("terrain", me)
    me.materials.append(mats["mud"])
    # bare rock on the cliff and its strip at the south wall feet, and wherever the ground is too steep for mud
    me.materials.append(mats["rock"])
    for poly in me.polygons:
        c = poly.center
        if terrain.rock(c.x, c.y) > 0.5 or poly.normal.z < 0.6:
            poly.material_index = 1
            poly.use_smooth = False  # broken rock reads faceted
    bpy.context.collection.objects.link(ob)


def build_ground(mats, plan, holes):
    """The terrain and the floor of the platform polygon. plan["ground"] (all keys optional):
    `terrain` (default true) builds the terrain of terrain.py; `floor` is the floor's material key
    (default cobble_wet); `apron` {size [x, y], z, material} lays a flat skin of ground around the
    place instead of the terrain, for a room outside which only a little ground shows."""
    lw = plan["heights"]["lower_ward"]
    ground = plan.get("ground", {})
    if ground.get("terrain", True):
        build_terrain(mats)
    apron = ground.get("apron")
    if apron:
        kit.box("apron", (*apron["size"], 0.4), (0, 0, apron["z"] - 0.2), mat=mats[apron.get("material", "mud")])
    poly = plan["platform"]["polygon"]
    n = len(poly)
    verts = [(x, y, 0.0) for x, y in poly] + [(x, y, lw - 0.3) for x, y in poly]
    faces = [list(range(n)), list(range(2 * n - 1, n - 1, -1))]
    faces += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    floor = kit.mesh("courtyard_floor", verts, faces, mat=mats[ground.get("floor", "cobble_wet")])
    # the platform's sides are its retaining walls
    floor.data.materials.append(mats["stone_wall"])
    for p in floor.data.polygons[2:]:
        p.material_index = 1
    for i, (center, rot_z, hx, hy) in enumerate(holes):
        cutter = kit.box(f"hole_{i}", (hx * 2, hy * 2, 1.0), (center.x, center.y, 0),
                         (0, 0, math.degrees(rot_z)))
        mod = floor.modifiers.new(f"hole_{i}", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter
        cutter.hide_render = True
        cutter.display_type = "WIRE"


# ---------- props ----------

def place_asset(key, mats, loc, rot_z_deg, scale=1.0, seed=0):
    name = key.split("#")[0]
    if name in assets.available():
        mod = assets.load(name)
        root = mod.build(kit, mats, random.Random(seed))
        lights = getattr(mod, "LIGHTS", [])
    else:
        root = kit.group(f"missing_{key}")
        ph = bpy.data.materials.get("placeholder") or bpy.data.materials.new("placeholder")
        ph.diffuse_color = (0.5, 0.1, 0.5, 1)
        kit.box(f"ph_{key}", (1, 1, 1), (0, 0, 0.5), mat=ph, parent=root)
        lights = []
    root.name = f"prop_{key}"
    # flames sit around their own point light; if they cast shadows the light never escapes
    for ob in root.children_recursive:
        if ob.type == "MESH" and any(m and m.name in ("fire", "embers") for m in ob.data.materials):
            ob.visible_shadow = False
    root.location = loc
    root.rotation_euler = (0, 0, math.radians(rot_z_deg))
    root.scale = scale if isinstance(scale, (list, tuple)) else (scale,) * 3
    bpy.context.view_layer.update()
    for i, (pos, color, watts) in enumerate(lights):
        li = bpy.data.objects.new(f"light_{key}_{i}", bpy.data.lights.new(f"light_{key}_{i}", "POINT"))
        li.data.color = color
        li.data.energy = watts * LIGHT_SCALE
        li.data.shadow_soft_size = 0.25
        li.location = root.matrix_world @ Vector(pos)
        bpy.context.collection.objects.link(li)
    return root


def build_props(plan, mats, check_scale):
    holes = []
    heights = plan["heights"]
    for i, (key, p) in enumerate(entries(plan["props"])):
        z = p.get("z", 0.0)
        # "ground": stand on the terrain outside the walls
        z = terrain.ground_z(*p["pos"]) if z == "ground" else height(z, heights)
        loc = Vector((p["pos"][0], p["pos"][1], z))
        scale = p.get("scale", 1.0)
        # seeded by key, so a prop keeps its shape when entries are added or reordered
        place_asset(key, mats, loc, p.get("rot_z", 0), scale, seed=zlib.crc32(key.encode()))
        if key.split("#")[0] == "grate":
            s = scale if not isinstance(scale, (list, tuple)) else scale[0]
            holes.append((loc, math.radians(p.get("rot_z", 0)), 0.62 * s, 0.62 * s))

    for i, (key, m) in enumerate(entries(plan["mounted"])):
        place_asset(key, mats, Vector(m["pos"]), m.get("rot_z", 0), m.get("scale", 1.0),
                    seed=zlib.crc32(key.encode()))

    crows = plan["crows"]
    rng = random.Random(crows.get("seed", 0))
    region = crows.get("perch_region")
    perches = [p for p in PERCHES if not _buried(*p[:3]) and (not region or
               (region[0][0] <= p[0] <= region[0][1] and region[1][0] <= p[1] <= region[1][1]))]
    for i, (x, y, z, wall_rot) in enumerate(rng.sample(perches, min(crows["perched"], len(perches)))):
        rot = wall_rot + rng.choice((0, 180)) + rng.uniform(-50, 50)
        place_asset(f"crow#{i}", mats, Vector((x, y, z)), rot, crows.get("scale", 1.0), seed=200 + i)
    for i, (x, y, z, rot) in enumerate(crows.get("points", [])):
        place_asset(f"crow#p{i}", mats, Vector((x, y, z)), rot, crows.get("scale", 1.0), seed=230 + i)
    for i, (x, y, z, rot) in enumerate(crows.get("flying", [])):
        place_asset(f"crow_flying#{i}", mats, Vector((x, y, z)), rot, 1.0, seed=250 + i)

    if check_scale:
        for i, (x, y, rot) in enumerate(plan["humans"]["points"]):
            place_asset(f"human#{i}", mats, Vector((x, y, 0)), rot, 1.0, seed=300 + i)
    return holes


# ---------- world and render ----------

def build_environment(env):
    world = bpy.data.worlds.new("world")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    bg.inputs[1].default_value = env.get("ambient_strength", 1.0)
    # overcast night sky: brighter low cloud near the horizon, dark overhead.
    # Wet ground reflects the low sky at grazing angles, which lights the puddles.
    horizon = env.get("horizon_color")
    if horizon:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Generated"], sep.inputs[0])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        els = ramp.color_ramp.elements
        els[0].position, els[0].color = 0.0, (*horizon, 1.0)
        els[1].position, els[1].color = env.get("horizon_falloff", 0.35), (*env["sky_color"], 1.0)
        absz = nt.nodes.new("ShaderNodeMath")
        absz.operation = "ABSOLUTE"
        nt.links.new(sep.outputs["Z"], absz.inputs[0])
        nt.links.new(absz.outputs[0], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bg.inputs[0])
    else:
        bg.inputs[0].default_value = (*env["sky_color"], 1.0)
    # what the camera sees directly: a darker overcast sky with soft cloud banks.
    # Lighting and reflections keep the brighter gradient above.
    cam_sky = env.get("camera_sky")
    if cam_sky:
        lp = nt.nodes.new("ShaderNodeLightPath")
        tc2 = nt.nodes.new("ShaderNodeTexCoord")
        cloud = nt.nodes.new("ShaderNodeTexNoise")
        cloud.inputs["Scale"].default_value = 2.5
        cloud.inputs["Detail"].default_value = 6.0
        nt.links.new(tc2.outputs["Generated"], cloud.inputs["Vector"])
        cr = nt.nodes.new("ShaderNodeValToRGB")
        cr.color_ramp.elements[0].color = (*[c * 0.6 for c in cam_sky], 1.0)
        cr.color_ramp.elements[1].color = (*[c * 1.5 for c in cam_sky], 1.0)
        nt.links.new(cloud.outputs["Fac"], cr.inputs["Fac"])
        bg2 = nt.nodes.new("ShaderNodeBackground")
        nt.links.new(cr.outputs["Color"], bg2.inputs[0])
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
        nt.links.new(bg.outputs[0], mix.inputs[1])
        nt.links.new(bg2.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], nt.nodes["World Output"].inputs["Surface"])
    m = env["moon"]
    li = bpy.data.objects.new("moon", bpy.data.lights.new("moon", "SUN"))
    li.data.color = m["color"]
    li.data.energy = m["strength"]
    li.data.angle = math.radians(m.get("angle_deg", 3))
    li.rotation_euler = [math.radians(a) for a in m["direction_euler"]]
    bpy.context.collection.objects.link(li)


def _set(sock, value):
    try:
        sock.default_value = value
    except (TypeError, ValueError) as e:
        print(f"POST could not set {sock.name}={value!r}: {e}")


def _color_input(node, name):
    return next(s for s in node.inputs if s.name == name and s.type == "RGBA")


def setup_post(post):
    """Compositor: painterly Kuwahara -> bloom -> lift/gamma/gain grade -> vignette."""
    sc = bpy.context.scene
    ng = bpy.data.node_groups.new("post", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    sc.compositing_node_group = ng
    nodes, links = ng.nodes, ng.links
    img = nodes.new("CompositorNodeRLayers").outputs["Image"]

    if post.get("kuwahara"):
        k = nodes.new("CompositorNodeKuwahara")
        _set(k.inputs["Type"], "Anisotropic")
        _set(k.inputs["Size"], post["kuwahara"])
        _set(k.inputs["Sharpness"], post.get("kuwahara_sharpness", 0.5))
        links.new(img, k.inputs["Image"])
        img = k.outputs["Image"]

    if post.get("sharpen"):
        # brings back fine texture (stone grain, rain) that the Kuwahara pass smooths away
        f = nodes.new("CompositorNodeFilter")
        _set(f.inputs["Type"], "Diamond Sharpen")
        _set(f.inputs["Factor"], post["sharpen"])
        links.new(img, f.inputs["Image"])
        img = f.outputs["Image"]

    if "saturation" in post:
        hs = nodes.new("CompositorNodeHueSat")
        _set(hs.inputs["Saturation"], post["saturation"])
        links.new(img, hs.inputs["Image"])
        img = hs.outputs["Image"]

    if post.get("bloom"):
        g = nodes.new("CompositorNodeGlare")
        _set(g.inputs["Type"], "Bloom")
        _set(g.inputs["Threshold"], post.get("bloom_threshold", 1.0))
        _set(g.inputs["Strength"], post["bloom"])
        _set(g.inputs["Size"], post.get("bloom_size", 0.5))
        links.new(img, g.inputs["Image"])
        img = g.outputs["Image"]

    if "grade" in post:
        cb = nodes.new("CompositorNodeColorBalance")
        for name in ("Lift", "Gamma", "Gain"):
            _set(_color_input(cb, name), (*post["grade"][name.lower()], 1.0))
        links.new(img, cb.inputs["Image"])
        img = cb.outputs["Image"]

    if post.get("vignette"):
        m = nodes.new("CompositorNodeEllipseMask")
        _set(m.inputs["Size"], (0.95, 0.9))
        blur = nodes.new("CompositorNodeBlur")
        _set(blur.inputs["Size"], (300, 300))
        links.new(m.outputs["Mask"], blur.inputs["Image"])
        mix = nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs[0].default_value = post["vignette"]
        links.new(img, mix.inputs[6])
        links.new(blur.outputs["Image"], mix.inputs[7])
        img = mix.outputs[2]

    out = nodes.new("NodeGroupOutput")
    links.new(img, out.inputs[0])


def setup_atmosphere(env):
    """Bounded haze around the castle: rain mist, denser near the ground.

    A world volume would fill the space between the camera and the scene, so
    the haze is a box around the castle. Density falls off with height and is
    broken up by noise, so the lower ward reads as misty and the courtyard
    stays clear enough to read.
    """
    h = env.get("haze")
    if not h:
        return
    sc = bpy.context.scene
    sc.eevee.volumetric_tile_size = str(h.get("tile_px", 4))
    sc.eevee.volumetric_samples = h.get("samples", 64)
    lo, hi = h["z_range"]
    size = h["size"]
    box = kit.box("haze", (size[0], size[1], hi - lo), (h["center"][0], h["center"][1], (lo + hi) / 2))
    mat = bpy.data.materials.new("haze")
    nt = mat.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    falloff = nt.nodes.new("ShaderNodeMapRange")
    falloff.inputs["From Min"].default_value = lo
    falloff.inputs["From Max"].default_value = lo + h.get("falloff_m", 6.0)
    falloff.inputs["To Min"].default_value = h["ground_density"]
    falloff.inputs["To Max"].default_value = h["density"]
    nt.links.new(sep.outputs["Z"], falloff.inputs["Value"])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.08
    noise.inputs["Detail"].default_value = 3.0
    nt.links.new(geo.outputs["Position"], noise.inputs["Vector"])
    patch = nt.nodes.new("ShaderNodeMapRange")
    patch.inputs["To Min"].default_value = 0.3
    patch.inputs["To Max"].default_value = 1.7
    nt.links.new(noise.outputs["Fac"], patch.inputs["Value"])
    dens = nt.nodes.new("ShaderNodeMath")
    dens.operation = "MULTIPLY"
    nt.links.new(falloff.outputs["Result"], dens.inputs[0])
    nt.links.new(patch.outputs["Result"], dens.inputs[1])
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (*h.get("color", (0.6, 0.65, 0.75)), 1)
    vol.inputs["Anisotropy"].default_value = h.get("anisotropy", 0.3)
    nt.links.new(dens.outputs[0], vol.inputs["Density"])
    nt.links.new(vol.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    box.data.materials.append(mat)
    box.visible_shadow = False


# ---------- rain ----------

def build_rain(spec, cam_yaw_deg, platform, mats, rng, clear=None):
    """Falling streaks, splashes on the floor and the lower ward, as two meshes.

    Each streak is a thin quad along the fall direction, turned to face the
    camera, so it reads as a motion-blurred drop. Splashes are small crowns
    of upward flecks.
    `clear` = (point, radius) keeps streaks away from a perspective camera,
    where a drop right in front of the lens would read as a thick bar.
    """
    import bmesh
    if not spec or not spec.get("count"):
        return
    mat = mats["rain"]
    ps = math.radians(cam_yaw_deg)
    right = Vector((math.cos(ps), -math.sin(ps), 0))
    wind = Vector((*spec.get("wind", (0.0, 0.0)), -1.0)).normalized()
    (x0, x1), (y0, y1), (z0, z1) = spec["region"]
    lmin, lmax = spec["length"]
    w = spec["width"]
    sheltered = spec.get("sheltered", [])  # [[x0, x1], [y0, y1], [z0, z1]] boxes under a roof or vault

    # depth layers: many faint short drops, fewer bright long ones, so the rain has depth
    layers = spec.get("layers", [[1.0, 1.0, 1.0, 1.0]])
    for li, (share, bright, lscale, wscale) in enumerate(layers):
        lmat = mat.copy()
        lmat.name = f"rain_{li}"
        em = next(n for n in lmat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        em.inputs["Emission Strength"].default_value *= bright
        em.inputs["Alpha"].default_value = min(1.0, em.inputs["Alpha"].default_value * bright)
        bm = bmesh.new()
        for _ in range(int(spec["count"] * share)):
            p = Vector((rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(z0, z1)))
            if clear and (p - clear[0]).length < clear[1]:
                continue
            if any(a[0] < p.x < a[1] and b[0] < p.y < b[1] and c[0] < p.z < c[1] for a, b, c in sheltered):
                continue
            d = wind * rng.uniform(lmin, lmax) * lscale
            side = right * (w * wscale * rng.uniform(0.6, 1.4) / 2)
            vs = [bm.verts.new(p + side), bm.verts.new(p - side),
                  bm.verts.new(p + d - side * 0.3), bm.verts.new(p + d + side * 0.3)]
            bm.faces.new(vs)
        me = bpy.data.meshes.new(f"rain_{li}")
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(f"rain_{li}", me)
        me.materials.append(lmat)
        ob.visible_shadow = False
        bpy.context.collection.objects.link(ob)

    # splashes: a few flecks thrown up and out around each impact point
    bm = bmesh.new()
    n = spec.get("splashes", 0)
    poly = [Vector((x, y)) for x, y in platform]
    for _ in range(n):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        z = 0.0 if inside_polygon(x, y, poly) else terrain.ground_z(x, y)
        c = Vector((x, y, z + 0.005))
        for k in range(rng.randint(3, 6)):
            a = rng.uniform(0, 2 * math.pi)
            out = Vector((math.cos(a), math.sin(a), 0))
            h = rng.uniform(0.04, 0.10)
            tip = c + out * h * 0.6 + Vector((0, 0, h))
            s = right * 0.006
            vs = [bm.verts.new(c + out * 0.02 + s), bm.verts.new(c + out * 0.02 - s), bm.verts.new(tip)]
            bm.faces.new(vs)
    me = bpy.data.meshes.new("splashes")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("splashes", me)
    me.materials.append(mat)
    ob.visible_shadow = False
    bpy.context.collection.objects.link(ob)


def render(out_path, spec, passes=False):
    sc = bpy.context.scene
    if passes:
        # data for compositing real-time objects over the pre-rendered background
        vl = sc.view_layers[0]
        vl.use_pass_z = True
        vl.use_pass_normal = True
        vl.use_pass_mist = True
    sc.render.engine = spec.get("engine", "BLENDER_EEVEE")
    sc.render.resolution_percentage = spec.get("percent", 100)  # quick look tests at the same framing
    if sc.render.engine == "CYCLES":
        # path tracing on the GPU (Metal), denoised; used for stills that set the target look
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
        sc.cycles.samples = spec.get("cycles_samples", 256)
        sc.cycles.use_denoising = True
        sc.cycles.max_bounces = spec.get("cycles_bounces", 6)
        sc.cycles.volume_bounces = 1
        sc.cycles.volume_step_rate = spec.get("cycles_volume_step", 4.0)
        sc.cycles.light_sampling_threshold = 0.01
    # every prop light casts shadows; the default 512 MB pool overflows with a dozen lights
    sc.eevee.shadow_pool_size = "2048"
    sc.eevee.taa_render_samples = spec.get("samples", 64)
    if spec.get("raytracing") and hasattr(sc.eevee, "use_raytracing"):
        sc.eevee.use_raytracing = True
    sc.view_settings.look = "AgX - Punchy"
    sc.view_settings.exposure = spec.get("exposure", 0.0)
    sc.render.filepath = str(out_path)
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    if passes:
        exr = out_path.with_suffix(".passes.exr")
        st = sc.render.image_settings
        if hasattr(st, "media_type"):  # Blender 5 lists multilayer EXR under its own media type
            st.media_type = "MULTI_LAYER_IMAGE"
        st.file_format = "OPEN_EXR_MULTILAYER"
        sc.render.image_settings.color_depth = "32"
        bpy.data.images["Render Result"].save_render(str(exr), scene=sc)
        print("passes ->", exr)


def build_world(plan, layout, check_scale=False):
    """Everything but the camera, haze, rain and post: sky and moon, blocks, props, ground."""
    global LIGHT_SCALE
    LIGHT_SCALE = layout.get("prop_light_scale", 1.0)
    PERCHES.clear()
    FOOTPRINTS.clear()
    terrain.reset()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = Materials()
    build_environment(layout["environment"])
    for name, b in entries(plan["blocks"]):
        build_block(name, b, mats, plan["heights"], plan["merlon"])
    holes = build_props(plan, mats, check_scale)
    build_ground(mats, plan, holes)
    return mats


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    location.add_argument(ap)
    ap.add_argument("--plan", default=None, help="plan.json to build instead of the location's")
    ap.add_argument("--layout", default=None, help="default: the location's layout.json")
    ap.add_argument("--out", default=str(ROOT / "renders" / "render.png"))
    ap.add_argument("--view", default="ref", help="ref, or names of location.json views (plan, eye, ...), comma-separated")
    ap.add_argument("--check-scale", action="store_true")
    ap.add_argument("--percent", type=int, default=None, help="render size in percent (overrides the layout)")
    ap.add_argument("--save-blend", default=None)
    ap.add_argument("--passes", action="store_true", help="also write depth, normal and mist to <out>.passes.exr")
    args = ap.parse_args(argv)
    location.use(args.location)
    if args.plan:
        location.override("plan.json", args.plan)

    plan = location.plan()
    trace = location.load("trace.json")
    layout = json.loads(Path(args.layout).read_text()) if args.layout else location.load("layout.json")
    if args.percent:
        layout["render"]["percent"] = args.percent
    res = layout["render"]["resolution"]
    views = location.table("views")

    mats = build_world(plan, layout, args.check_scale)
    names = args.view.split(",")
    for name in names:
        if name != "ref" and name not in views:
            raise SystemExit(f"no view {name}; location.json views: {[k for k in views if not k.startswith('_')]}")
    setup_atmosphere(layout["environment"])
    if "post" in layout:
        setup_post(layout["post"])
    if args.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.save_blend).resolve()))
    out = Path(args.out).resolve()
    # several views are rendered from one build: --out is then a folder and each view is <location>_<view>.png
    for name in names:
        cam = camera_ref(trace["camera"], res) if name == "ref" else camera_view(views[name])
        install_camera(cam, res)
        build_rain(layout.get("rain"), trace["camera"]["yaw_deg"], plan["platform"]["polygon"],
                   mats, random.Random(11),
                   clear=(cam.location.copy(), 5.0) if name != "ref" and "lens" in views[name] else None)
        target = out / f"{location.name()}_{name}{'_scale' if args.check_scale else ''}.png" if len(names) > 1 else out
        render(target, layout["render"], args.passes)
        print(f"rendered -> {target}")
        if len(names) > 1:
            for ob in [o for o in bpy.data.objects if o.name.startswith(("rain_", "splashes"))] + [cam]:
                bpy.data.objects.remove(ob)


if __name__ == "__main__":
    main()

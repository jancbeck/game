"""Small arched window with a lit room behind iron bars, set in a stone surround.

Origin: center of the opening on the wall face (XZ plane at y = 0, the wall is not part of this
prop). The opening is 0.40 m wide and 0.80 m high: straight sides from z = -0.4 to the springing
line at z = 0.2, then a round arch to z = 0.4. The surround stands 0.18 m proud toward -Y and the
sill 0.3 m, so the room sits recessed in the reveal.

The room is a back wall that a lamp lights from one side: bright near the lamp, falling off to a
dark red-brown at the corners, with plank joints and a dark ceiling beam and ledge in front of it.
One of three variants is picked from the rng:

- figure: a hooded person stands at the window with the lamp behind them, seen as a dark bust
  against the glow, and one shutter leaf is swung half open;
- shuttered: one shutter leaf is closed over half the opening and light leaks around its edge;
- open: both leaves stand open against the reveal and the whole lit room shows.

Three vertical bars and two cross bars guard the opening. One point light just under the sill
washes the stone around the window.
"""

import math

import bpy

from . import _lights

HALF = 0.2               # half the opening width, also the arch radius
Z_BOT = -0.4
SPRING = 0.2             # z of the springing line
REVEAL = 0.18            # how far the surround stands out from the wall
STONES = 7               # voussoirs; the middle one is the keystone
VARIANTS = ("figure", "shuttered", "open")

LIGHTS = []
LIGHT = dict(pos=(0.0, -0.32, -0.12), color=(1.0, 0.45, 0.12), watts=24.0, radius=0.1, specular=0.15,
             reach=5.0)


def _wedge(kit, name, a0, a1, r0, r1, y0, y1, mat, parent):
    """Arch stone between angles a0..a1 (radians from +X) and radii r0..r1, from y0 to y1."""
    verts = []
    for a in (a0, a1):
        for r in (r0, r1):
            for y in (y0, y1):
                verts.append((r * math.cos(a), y, SPRING + r * math.sin(a)))
    v = lambda i, j, k: i * 4 + j * 2 + k  # noqa: E731
    faces = [
        (v(0, 0, 0), v(0, 1, 0), v(0, 1, 1), v(0, 0, 1)),
        (v(1, 0, 0), v(1, 0, 1), v(1, 1, 1), v(1, 1, 0)),
        (v(0, 0, 0), v(0, 0, 1), v(1, 0, 1), v(1, 0, 0)),
        (v(0, 1, 0), v(1, 1, 0), v(1, 1, 1), v(0, 1, 1)),
        (v(0, 0, 0), v(1, 0, 0), v(1, 1, 0), v(0, 1, 0)),
        (v(0, 0, 1), v(0, 1, 1), v(1, 1, 1), v(1, 0, 1)),
    ]
    return kit.mesh(name, verts, faces, mat=mat, parent=parent, bevel=0.012)


def _surround(kit, mats, rng, root):
    stone = mats["stone_wall"]
    step = math.pi / STONES
    for i in range(STONES):
        r1 = HALF + 0.12 + kit.jitter(rng, 0.015) + (0.03 if i % 2 == 0 else 0.0)
        if i == STONES // 2:
            r1 = HALF + 0.17
        _wedge(kit, f"voussoir_{i}", i * step + 0.01, (i + 1) * step - 0.01,
               HALF + kit.jitter(rng, 0.004), r1, -REVEAL + kit.jitter(rng, 0.02), 0.0, stone, root)

    # jamb stones, alternating widths, from the sill to the springing line
    courses = 3
    h = (SPRING - Z_BOT) / courses
    for side in (-1, 1):
        for c in range(courses):
            w = (0.13, 0.20)[(c + (side > 0)) % 2] + kit.jitter(rng, 0.01)
            d = REVEAL - abs(kit.jitter(rng, 0.02))
            kit.box(f"jamb_{'R' if side > 0 else 'L'}{c}", (w, d, h - 0.012),
                    (side * (HALF + w / 2), -d / 2, Z_BOT + c * h + h / 2), mat=stone, bevel=0.012,
                    parent=root)

    # sill: one long stone that projects past the surround
    kit.box("sill", (0.8, 0.30, 0.07), (0, -0.15, Z_BOT - 0.035), mat=stone, bevel=0.014,
            parent=root)


def _arch_outline(n=14):
    pts = [(-HALF, Z_BOT), (HALF, Z_BOT)]
    for i in range(n + 1):
        a = math.pi * i / n
        pts.append((HALF * math.cos(a), SPRING + HALF * math.sin(a)))
    return pts


def _room_material(lamp_x, lamp_z):
    """Emission of the room's back wall: hot near the lamp, dim at the corners, with plank joints."""
    mat = bpy.data.materials.new("window_room")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    new = nt.nodes.new

    def math_node(op, a, b=None, clamp=False):
        n = new("ShaderNodeMath")
        n.operation = op
        n.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                nt.links.new(v, n.inputs[i])
        return n.outputs[0]

    sep = new("ShaderNodeSeparateXYZ")
    nt.links.new(new("ShaderNodeTexCoord").outputs["Object"], sep.inputs[0])
    dx = math_node("SUBTRACT", sep.outputs["X"], lamp_x)
    dz = math_node("MULTIPLY", math_node("SUBTRACT", sep.outputs["Z"], lamp_z), 0.75)
    dist = math_node("SQRT", math_node("ADD", math_node("MULTIPLY", dx, dx), math_node("MULTIPLY", dz, dz)))
    t = math_node("DIVIDE", dist, 0.5, clamp=True)

    ramp = new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (1.0, 0.62, 0.22, 1.0)
    cr.elements.new(0.3).color = (1.0, 0.36, 0.07, 1.0)
    cr.elements.new(0.7).color = (0.50, 0.11, 0.02, 1.0)
    cr.elements[3].position, cr.elements[3].color = 1.0, (0.10, 0.022, 0.008, 1.0)
    nt.links.new(t, ramp.inputs["Fac"])

    # plank joints: thin dark vertical lines every 0.07 m
    wave = new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.wave_profile = "SAW"
    wave.inputs["Scale"].default_value = 14.0
    wave.inputs["Distortion"].default_value = 0.0
    wave.inputs["Detail"].default_value = 0.0
    nt.links.new(new("ShaderNodeTexCoord").outputs["Object"], wave.inputs["Vector"])
    joints = new("ShaderNodeMapRange")
    joints.inputs["From Min"].default_value = 0.0
    joints.inputs["From Max"].default_value = 0.12
    joints.inputs["To Min"].default_value = 0.35
    joints.inputs["To Max"].default_value = 1.0
    # the saw profile runs 0..1 across each plank, so the distance from a joint is min(v, 1 - v)
    edge = math_node("MINIMUM", wave.outputs["Fac"], math_node("SUBTRACT", 1.0, wave.outputs["Fac"]))
    nt.links.new(edge, joints.inputs["Value"])

    shade = new("ShaderNodeMix")
    shade.data_type = "RGBA"
    shade.blend_type = "MULTIPLY"
    shade.inputs[0].default_value = 1.0
    nt.links.new(ramp.outputs["Color"], shade.inputs[6])
    grey = new("ShaderNodeCombineColor")
    for name in ("Red", "Green", "Blue"):
        nt.links.new(joints.outputs["Result"], grey.inputs[name])
    nt.links.new(grey.outputs["Color"], shade.inputs[7])

    emit = new("ShaderNodeEmission")
    nt.links.new(shade.outputs[2], emit.inputs["Color"])
    strength = new("ShaderNodeMapRange")
    strength.inputs["From Min"].default_value = 0.0
    strength.inputs["From Max"].default_value = 1.0
    strength.inputs["To Min"].default_value = 3.6
    strength.inputs["To Max"].default_value = 0.5
    nt.links.new(t, strength.inputs["Value"])
    nt.links.new(strength.outputs["Result"], emit.inputs["Strength"])
    out = new("ShaderNodeOutputMaterial")
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def _cloth_material():
    mat = bpy.data.materials.get("window_figure")
    if mat is None:
        mat = bpy.data.materials.new("window_figure")
        mat.use_nodes = True
        b = mat.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.012, 0.009, 0.008, 1.0)
        b.inputs["Roughness"].default_value = 0.95
        b.inputs["Specular IOR Level"].default_value = 0.0
    return mat


def _shutter(kit, mats, rng, parent, side, swing_deg, name):
    """Plank shutter leaf hinged on the jamb at `side` (-1 left, 1 right), swung out by `swing_deg`."""
    pivot = kit.group(name, (side * (HALF - 0.005), -0.06, 0.0), parent=parent)
    pivot.rotation_euler = (0, 0, math.radians(-side * swing_deg))
    planks = 3
    pw = (HALF - 0.012) / planks
    for k in range(planks):
        top = 0.60 - abs(kit.jitter(rng, 0.01))
        kit.box(f"{name}_plank_{k}", (pw - 0.004, 0.022, top),
                (-side * (0.006 + pw * (k + 0.5)), 0, Z_BOT + top / 2), mat=mats["door_wood"], bevel=0.004,
                parent=pivot)
    for z in (-0.3, 0.1):
        kit.box(f"{name}_strap", (HALF - 0.01, 0.01, 0.035), (-side * (HALF / 2), -0.016, z), mat=mats["iron"],
                parent=pivot)
    kit.box(f"{name}_batten", (0.025, 0.012, 0.52), (-side * (HALF - 0.04), -0.016, Z_BOT + 0.30),
            mat=mats["wood_dark"], bevel=0.003, parent=pivot)
    return pivot


def _figure(kit, x, parent):
    """Hooded bust: head, hood point, shoulders and chest, in front of the lit back wall."""
    cloth = _cloth_material()
    y = -0.075
    kit.sphere("fig_head", 0.05, (x, y, 0.115), scale=(0.95, 0.9, 1.2), mat=cloth, segments=10, parent=parent)
    kit.cylinder("fig_hood", 0.05, 0.075, (x, y + 0.012, 0.165), rot_deg=(-18, 0, 0), mat=cloth, segments=8,
                 radius_top=0.012, parent=parent)
    kit.sphere("fig_shoulders", 0.055, (x, y, 0.0), scale=(2.7, 0.8, 0.95), mat=cloth, segments=12, parent=parent)
    kit.box("fig_chest", (0.20, 0.07, 0.30), (x, y, -0.16), mat=cloth, bevel=0.02, parent=parent)


def _room(kit, mats, rng, root):
    """Lit back wall, ceiling beam and ledge, and the variant's figure or shutters."""
    variant = VARIANTS[int(rng.random() * len(VARIANTS)) % len(VARIANTS)]
    flip = rng.choice((-1, 1))
    lamp_x = -flip * 0.10 if variant == "figure" else flip * 0.06
    lamp_z = -0.08

    wall = [(x, -0.03, z) for x, z in _arch_outline()]
    kit.mesh("room", wall, [tuple(range(len(wall)))], mat=_room_material(lamp_x, lamp_z), parent=root)
    kit.box("ledge", (2 * HALF - 0.01, 0.10, 0.17), (0, -0.075, Z_BOT + 0.085), mat=mats["wood_dark"],
            bevel=0.004, parent=root)
    # ceiling beam seen across the opening, a little off level
    kit.box("beam", (2 * HALF + 0.12, 0.05, 0.055), (0, -0.07, 0.24 + kit.jitter(rng, 0.02)),
            rot_deg=(0, kit.jitter(rng, 3.0), 0), mat=mats["wood_dark"], bevel=0.004, parent=root)

    if variant == "figure":
        _figure(kit, flip * 0.065, root)
        _shutter(kit, mats, rng, root, -flip, 55.0, "shutter")
    elif variant == "shuttered":
        _shutter(kit, mats, rng, root, flip, 4.0, "shutter")
    else:
        _shutter(kit, mats, rng, root, -1, 62.0, "shutter_l")
        _shutter(kit, mats, rng, root, 1, 62.0, "shutter_r")


def _bars(kit, mats, root):
    iron = mats["iron"]
    for i, x in enumerate((-0.1, 0.0, 0.1)):
        top = SPRING + math.sqrt(max(HALF ** 2 - x ** 2, 0.0)) + 0.02
        kit.beam(f"bar_{i}", (x, -0.15, Z_BOT - 0.03), (x, -0.15, top), section=(0.014, 0.014),
                 mat=iron, bevel=0.002, parent=root)
    kit.box("cross_bar", (2 * HALF + 0.06, 0.012, 0.014), (0, -0.15, -0.05), mat=iron, parent=root)
    kit.box("cross_bar_hi", (2 * HALF + 0.06, 0.012, 0.014), (0, -0.15, 0.22), mat=iron,
            parent=root)


def build(kit, mats, rng):
    root = kit.group("lit_window")
    _surround(kit, mats, rng, root)
    _room(kit, mats, rng, root)
    _bars(kit, mats, root)
    _lights.add(root, "lit_window", **LIGHT)
    return root

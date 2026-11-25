"""Garrison tool rack under its own small roof against a wall: the yard's digging and sweeping tools.

Footprint 1.3 m wide (X) by 0.9 m deep (Y), 2.7 m at the roof's high edge. The wall side is +Y and
the front faces -Y, so place it with its back 0.45 m from the wall (rot_z 0 against a wall that
faces south). Origin is the center of the footprint on the ground.

Four posts on stone pads carry a plank roof that slopes down toward the front. Two rails run along
the back; the long tools lean on the upper one (1.45 m) with their feet on a foot board, the short
mattock on the lower one (0.52 m). From left to right: a birch-twig besom, an iron-shod wooden
spade, an iron shovel, a three-tined wooden hay fork, the mattock standing on its head and a wooden
hay rake, teeth up. A bow saw hangs from a peg on the outer face of the left front post, a coil of
rope from a peg on the right one. Handles are grey, weathered ash, dark and smooth where hands hold
them; every iron part is rusted, with the edges worn bright-dark by use.
"""

import math

import bpy

POST_X = 0.48            # posts stand at x = +-POST_X
FRONT_Y, REAR_Y = -0.38, 0.40
ROOF_FRONT = (-0.62, 2.42)       # (y, z) of the eave
ROOF_REAR = (0.47, 2.70)         # (y, z) at the wall
ROOF_HALF = 0.63
RAIL_Y = 0.33
RAIL_Z, LOW_RAIL_Z = 1.45, 0.52
RAIL_FACE = RAIL_Y - 0.045       # front face of the upper rail, where the shafts rest


def _rust():
    """Rusted iron: patchy orange-brown scale over dark metal."""
    mat = bpy.data.materials.get("tool_rust")
    if mat is not None:
        return mat
    mat = bpy.data.materials.new("tool_rust")
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 22.0
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.65
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.42, (0.022, 0.020, 0.020, 1.0)   # dark metal
    cr.elements[1].position, cr.elements[1].color = 0.60, (0.16, 0.055, 0.020, 1.0)   # rust scale
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    metal = nt.nodes.new("ShaderNodeMapRange")
    metal.inputs["From Min"].default_value = 0.42
    metal.inputs["From Max"].default_value = 0.60
    metal.inputs["To Min"].default_value = 0.7
    metal.inputs["To Max"].default_value = 0.0
    nt.links.new(noise.outputs["Fac"], metal.inputs["Value"])
    nt.links.new(metal.outputs["Result"], b.inputs["Metallic"])
    b.inputs["Roughness"].default_value = 0.8
    return mat


def _slab(kit, name, poly, thick, mat, parent, loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.0):
    """Closed prism from a 2D outline in the XZ plane, `thick` deep along Y (centered)."""
    n = len(poly)
    t0, t1 = -thick / 2, thick / 2
    verts = [(x, t0, z) for x, z in poly] + [(x, t1, z) for x, z in poly]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    return kit.mesh(name, verts, faces, loc=loc, rot_deg=rot, mat=mat, parent=parent, bevel=bevel)


def _lean(kit, rng, parent, name, x, rest_z, foot_z=0.0, roll=0.0):
    """Group whose +Z axis runs up the tool from its foot to where it rests on a rail."""
    tilt = math.radians(8.5 + kit.jitter(rng, 1.5))
    foot_y = RAIL_FACE - (rest_z - foot_z) * math.tan(tilt) - 0.02
    g = kit.group(name, (x, foot_y, foot_z), parent=parent)
    g.rotation_euler = (-tilt, math.radians(kit.jitter(rng, 2.0)), math.radians(roll))
    return g


def _handle(kit, mats, g, name, z0, z1, r=0.017, grip=None):
    """Ash shaft along +Z; `grip` (z0, z1) is the hand-worn dark stretch."""
    kit.cylinder(f"{name}_shaft", r, z1 - z0, (0, 0, (z0 + z1) / 2), mat=mats["wood_old"], segments=8,
                 radius_top=r * 0.9, parent=g)
    if grip:
        kit.cylinder(f"{name}_grip", r * 1.04, grip[1] - grip[0], (0, 0, (grip[0] + grip[1]) / 2),
                     mat=mats["wood_dark"], segments=8, parent=g)


def _besom(kit, mats, rng, root, x):
    g = _lean(kit, rng, root, "besom", x, RAIL_Z)
    _handle(kit, mats, g, "besom", 0.25, 1.55, 0.016, grip=(1.1, 1.35))
    # twig bundle, splayed at the foot and worn short on one side, bound with two withy bands
    kit.cylinder("besom_twigs", 0.13, 0.5, (0.0, -0.01, 0.25), mat=mats["straw"], radius_top=0.045, segments=12,
                 parent=g)
    for k, z in enumerate((0.38, 0.47)):
        kit.torus(f"besom_band_{k}", 0.055 - 0.01 * k, 0.009, (0, -0.005, z), mat=mats["bark"], major_segments=12,
                  minor_segments=4, parent=g)


def _spade(kit, mats, rng, root, x, rust):
    """Wooden spade with an iron shoe on the cutting edge and a D-grip."""
    g = _lean(kit, rng, root, "spade", x, RAIL_Z, roll=kit.jitter(rng, 8))
    _handle(kit, mats, g, "spade", 0.36, 1.12, grip=(0.95, 1.12))
    _slab(kit, "spade_blade", [(-0.085, 0.04), (0.085, 0.04), (0.09, 0.30), (0.03, 0.38), (-0.03, 0.38),
                               (-0.09, 0.30)], 0.024, mats["wood_dark"], g, bevel=0.004)
    _slab(kit, "spade_shoe", [(-0.09, 0.0), (0.09, 0.0), (0.09, 0.075), (-0.09, 0.075)], 0.032, rust, g,
          bevel=0.003)
    kit.torus("spade_d", 0.055, 0.012, (0, 0, 1.18), (90, 0, 0), mats["wood_old"], major_segments=10,
              minor_segments=4, parent=g)


def _shovel(kit, mats, rng, root, x, rust):
    """Iron shovel: a dished blade on a socket, a long straight ash handle."""
    g = _lean(kit, rng, root, "shovel", x, RAIL_Z, roll=kit.jitter(rng, 10))
    _handle(kit, mats, g, "shovel", 0.36, 1.52, grip=(1.25, 1.52))
    _slab(kit, "shovel_blade", [(-0.12, 0.02), (0.0, -0.0), (0.12, 0.02), (0.13, 0.27), (0.04, 0.31),
                                (-0.04, 0.31), (-0.13, 0.27)], 0.008, rust, g, rot=(-6, 0, 0))
    for sx in (-1, 1):
        _slab(kit, f"shovel_lip_{sx}", [(-0.006, 0.03), (0.006, 0.03), (0.006, 0.27), (-0.006, 0.27)], 0.05, rust,
              g, loc=(sx * 0.125, -0.02, 0.0))
    kit.cylinder("shovel_socket", 0.024, 0.12, (0, 0, 0.37), mat=rust, radius_top=0.019, segments=8, parent=g)


def _hay_fork(kit, mats, rng, root, x):
    """Three-tined fork grown and cut from one branch, the tines pegged and bound to the shaft."""
    g = _lean(kit, rng, root, "hay_fork", x, RAIL_Z)
    _handle(kit, mats, g, "fork", 0.0, 1.55, 0.018, grip=(0.55, 0.85))
    kit.box("fork_crutch", (0.16, 0.03, 0.05), (0, 0, 1.55), mat=mats["wood_old"], bevel=0.008, parent=g)
    for k, dx in enumerate((-0.07, 0.0, 0.07)):
        kit.beam(f"fork_tine_{k}", (dx, 0, 1.55), (dx * 1.25, -0.03, 1.92 - 0.03 * abs(k - 1)), (0.016, 0.016),
                 mats["wood_old"], parent=g)
    kit.torus("fork_binding", 0.03, 0.008, (0, 0, 1.5), mat=mats["rope"], major_segments=10, minor_segments=4,
              parent=g)


def _mattock(kit, mats, rng, root, x, rust):
    """Mattock standing on its head (adze blade and pick), haft against the lower rail."""
    tilt = math.radians(26)
    y_head = RAIL_Y - 0.05 - (LOW_RAIL_Z - 0.06) * math.tan(tilt)
    g = kit.group("mattock", (x, y_head, 0.06), parent=root)
    g.rotation_euler = (-tilt, 0, math.radians(kit.jitter(rng, 6)))
    _handle(kit, mats, g, "mattock", 0.0, 0.86, 0.02, grip=(0.62, 0.86))
    # the head lies across the haft foot, in the YZ plane, resting on its blade and its point
    kit.cylinder("mattock_eye", 0.035, 0.09, (0, 0, 0.0), (90, 0, 0), rust, segments=8, parent=g)
    kit.beam("mattock_adze", (0, -0.03, 0.0), (0, -0.27, -0.04), (0.075, 0.018), rust, parent=g)
    kit.beam("mattock_pick", (0, 0.03, 0.0), (0, 0.27, -0.035), (0.026, 0.026), rust, parent=g)
    kit.box("mattock_wedge", (0.012, 0.03, 0.03), (0, 0, -0.04), mat=mats["wood_dark"], parent=g)


def _rake(kit, mats, rng, root, x):
    """Wooden hay rake, head up: a bar with pegged teeth and two braces to the shaft."""
    g = _lean(kit, rng, root, "rake", x, RAIL_Z)
    _handle(kit, mats, g, "rake", 0.0, 1.78, 0.017, grip=(0.7, 1.0))
    head_z, half = 1.8, 0.2
    kit.box("rake_head", (2 * half, 0.04, 0.045), (0, 0, head_z), mat=mats["wood_old"], bevel=0.006, parent=g)
    for sx in (-1, 1):
        kit.beam(f"rake_brace_{sx}", (0, 0, 1.55), (sx * 0.12, 0, head_z - 0.02), (0.014, 0.014),
                 mats["wood_old"], parent=g)
    for k in range(11):
        if k in (3, 8):
            continue                     # lost teeth
        tx = -half + 0.02 + k * (2 * half - 0.04) / 10
        kit.cylinder(f"rake_tooth_{k}", 0.006, 0.09, (tx, -0.04, head_z), (90, 0, 0), mats["wood_old"], segments=5,
                     parent=g)


def _bow_saw(kit, mats, rng, root, rust):
    """Bow saw hung by its frame from a peg on the outer face of the left front post."""
    x0 = -POST_X - 0.05
    kit.cylinder("saw_peg", 0.012, 0.1, (x0 - 0.02, FRONT_Y, 1.62), (0, 90, 0), mats["wood_dark"], segments=6,
                 parent=root)
    g = kit.group("bow_saw", (x0 - 0.06, FRONT_Y, 1.6), parent=root)
    g.rotation_euler = (0, 0, math.radians(90))
    wo = mats["wood_old"]
    for sx in (-1, 1):
        kit.box(f"saw_arm_{sx}", (0.03, 0.022, 0.42), (sx * 0.3, 0, -0.2), mat=wo, bevel=0.004, parent=g)
    kit.box("saw_stretcher", (0.6, 0.02, 0.03), (0, 0, -0.22), mat=wo, bevel=0.004, parent=g)
    kit.box("saw_blade", (0.6, 0.004, 0.045), (0, 0, -0.39), mat=rust, parent=g)
    kit.box("saw_cord", (0.6, 0.012, 0.014), (0, 0, -0.02), mat=mats["rope"], parent=g)
    kit.box("saw_toggle", (0.012, 0.02, 0.14), (0.05, 0.012, -0.06), (0, 30, 0), wo, parent=g)


def _rope_coil(kit, mats, rng, root):
    """Coil of rope hung from a peg on the outer face of the right front post."""
    x0 = POST_X + 0.05
    kit.cylinder("rope_peg", 0.012, 0.1, (x0 + 0.02, FRONT_Y, 1.72), (0, 90, 0), mats["wood_dark"], segments=6,
                 parent=root)
    for k in range(7):
        r = 0.2 + kit.jitter(rng, 0.015)
        kit.torus(f"rope_turn_{k}", r, 0.011, (x0 + 0.035 + 0.008 * (k % 3), FRONT_Y + kit.jitter(rng, 0.01),
                                                1.73 - r + kit.jitter(rng, 0.01)),
                  (kit.jitter(rng, 5), 90, kit.jitter(rng, 4)), mats["rope"], major_segments=20, minor_segments=4,
                  parent=root)
    kit.beam("rope_tail", (x0 + 0.04, FRONT_Y + 0.05, 1.32), (x0 + 0.06, FRONT_Y + 0.02, 0.98), (0.02, 0.02),
             mats["rope"], parent=root)


def _frame(kit, mats, rng, root):
    wd, wo, iron = mats["wood_dark"], mats["wood_old"], mats["iron"]
    j = lambda a: kit.jitter(rng, a)  # noqa: E731
    for sx in (-1, 1):
        x = sx * POST_X
        for name, y, top in (("front", FRONT_Y, 2.36), ("rear", REAR_Y, 2.62)):
            kit.beam(f"{name}_post_{sx}", (x, y, 0.0), (x + j(0.01), y + j(0.01), top), (0.10, 0.10), wd,
                     bevel=0.008, parent=root)
            kit.box(f"{name}_pad_{sx}", (0.22, 0.22, 0.08), (x, y, 0.03), (0, 0, j(8)), mats["stone_wall"],
                    bevel=0.02, parent=root)
        kit.beam(f"brace_{sx}", (x, FRONT_Y, 1.75), (x, FRONT_Y + 0.42, 2.34), (0.06, 0.06), wo, bevel=0.005,
                 parent=root)
    kit.beam("eave_beam", (-POST_X - 0.1, FRONT_Y, 2.34), (POST_X + 0.1, FRONT_Y, 2.34), (0.10, 0.12), wd,
             bevel=0.008, parent=root)
    kit.beam("rear_beam", (-POST_X - 0.1, REAR_Y, 2.58), (POST_X + 0.1, REAR_Y, 2.58), (0.10, 0.12), wd,
             bevel=0.008, parent=root)
    kit.beam("rail_upper", (-POST_X, RAIL_Y, RAIL_Z), (POST_X, RAIL_Y, RAIL_Z), (0.09, 0.07), wd, bevel=0.006,
             parent=root)
    kit.beam("rail_lower", (-POST_X, RAIL_Y, LOW_RAIL_Z), (POST_X, RAIL_Y, LOW_RAIL_Z), (0.07, 0.06), wd,
             bevel=0.006, parent=root)
    kit.box("foot_board", (2 * POST_X - 0.08, 0.24, 0.05), (0.0, 0.17, 0.025), mat=wo, bevel=0.006, parent=root)
    for sx in (-1, 1):
        kit.box(f"rail_strap_{sx}", (0.12, 0.012, 0.05), (sx * POST_X, RAIL_Y - 0.035, RAIL_Z), mat=iron,
                parent=root)


def _roof(kit, mats, rng, root):
    wd, wo = mats["wood_dark"], mats["wood_old"]
    j = lambda a: kit.jitter(rng, a)  # noqa: E731
    (y0, z0), (y1, z1) = ROOF_FRONT, ROOF_REAR
    length = math.hypot(y1 - y0, z1 - z0)
    ang = math.degrees(math.atan2(z1 - z0, y1 - y0))
    ym, zm = (y0 + y1) / 2, (z0 + z1) / 2
    for x in (-0.52, -0.17, 0.17, 0.52):
        kit.box(f"rafter_{x}", (0.06, length, 0.07), (x, ym, zm - 0.05), (ang, 0, 0), wd, bevel=0.005, parent=root)
    planks = 6
    pw = 2 * ROOF_HALF / planks
    for k in range(planks):
        x = -ROOF_HALF + pw * (k + 0.5)
        kit.box(f"roof_plank_{k}", (pw - 0.012, length + 0.04 + j(0.05), 0.026),
                (x, ym + j(0.01), zm + j(0.004)), (ang + j(0.8), j(0.6), j(0.8)),
                wo if k % 3 else wd, bevel=0.004, parent=root)
    for t in (0.25, 0.7):
        kit.box(f"batten_{t}", (2 * ROOF_HALF + 0.02, 0.05, 0.022), (0, y0 + (y1 - y0) * t,
                                                                   z0 + (z1 - z0) * t + 0.026),
                (ang, 0, 0), wd, bevel=0.003, parent=root)
    kit.box("fascia", (2 * ROOF_HALF, 0.022, 0.13), (0, y0 - 0.005, z0 - 0.04), mat=wd, bevel=0.004, parent=root)


def build(kit, mats, rng):
    root = kit.group("tool_rack")
    rust = _rust()
    _frame(kit, mats, rng, root)
    _roof(kit, mats, rng, root)
    _besom(kit, mats, rng, root, -0.37)
    _spade(kit, mats, rng, root, -0.24, rust)
    _shovel(kit, mats, rng, root, -0.09, rust)
    _hay_fork(kit, mats, rng, root, 0.05)
    _mattock(kit, mats, rng, root, 0.15, rust)
    _rake(kit, mats, rng, root, 0.27)
    _bow_saw(kit, mats, rng, root, rust)
    _rope_coil(kit, mats, rng, root)
    return root

"""Plank water trough: 2.05 m long, 0.6 m wide, 0.6 m high, full of dark rainwater.

Four courses of side planks (some split at a butt joint, one sagging) are capped by end
boards and held by three iron straps. The box stands on two sunken stone footings. Water
lies 0.1 m below the rim with floating leaves, a drifting scrap of board and a green waterline
on the inside. An iron ring bolt on the +X end carries a short tether rope that trails on the
ground.

Long axis along X, centered on the origin, resting on Z = 0. The private glossy `rainwater`
material is shared with barrel.py and well.py: it is created only when missing.
"""

import math

import bpy

from . import _sweep

LENGTH = 2.0
WIDTH = 0.60
RIM = 0.60
FLOOR_Z = 0.10
PLANK_T = 0.045
ROWS = 4
WATER_Z = 0.50


def _rainwater():
    mat = bpy.data.materials.get("rainwater")
    if mat is None:
        mat = bpy.data.materials.new("rainwater")
        mat.use_nodes = True
        b = mat.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.03, 0.04, 0.05, 1.0)
        b.inputs["Roughness"].default_value = 0.02
        b.inputs["Specular IOR Level"].default_value = 1.0
        b.inputs["Metallic"].default_value = 0.0
    return mat


def _planks(kit, mats, rng, root):
    wo, wd = mats["wood_old"], mats["wood_dark"]
    j = lambda a: kit.jitter(rng, a)  # noqa: E731
    row_h = (RIM - FLOOR_Z) / ROWS
    sag_row, sag_side = rng.randrange(ROWS), rng.choice((-1, 1))
    for side in (-1, 1):
        y = side * (WIDTH / 2 - PLANK_T / 2)
        for r in range(ROWS):
            z = FLOOR_Z + row_h * (r + 0.5)
            h = row_h - 0.007
            mat = wd if rng.random() < 0.25 else wo
            if rng.random() < 0.4:       # two boards butted end to end
                cut = rng.uniform(-0.5, 0.5)
                pieces = [(-LENGTH / 2, cut - 0.003), (cut + 0.003, LENGTH / 2)]
            else:
                pieces = [(-LENGTH / 2, LENGTH / 2)]
            for k, (x0, x1) in enumerate(pieces):
                droop = 0.0
                if r == sag_row and side == sag_side and k == len(pieces) - 1:
                    droop = -0.012
                ry = j(0.5) + (math.degrees(math.atan2(-droop, x1 - x0)) if droop else 0.0)
                kit.box(f"plank_{side}_{r}_{k}", (x1 - x0, PLANK_T, h),
                        ((x0 + x1) / 2 + j(0.004), y + j(0.003), z + j(0.003) + droop / 2),
                        (0, ry, j(0.25)), mat, bevel=0.004, parent=root)
    # end boards outside the side planks
    for sx in (-1, 1):
        kit.box(f"end_{sx}", (PLANK_T, WIDTH, RIM - FLOOR_Z + 0.02),
                (sx * (LENGTH / 2 + PLANK_T / 2), j(0.003), (RIM + FLOOR_Z) / 2 - 0.01), (0, 0, j(0.8)),
                wo, bevel=0.005, parent=root)
    kit.box("floor", (LENGTH, WIDTH - 2 * PLANK_T, 0.05), (0, 0, FLOOR_Z + 0.025), mat=wd, parent=root)


def _straps(kit, mats, rng, root):
    iron = mats["iron"]
    for x in (-0.66, 0.0, 0.66):
        x += kit.jitter(rng, 0.02)
        for side in (-1, 1):
            y = side * (WIDTH / 2 + 0.005)
            kit.box(f"strap_{x:.2f}_{side}", (0.045, 0.010, RIM - FLOOR_Z + 0.03), (x, y, (RIM + FLOOR_Z) / 2),
                    mat=iron, bevel=0.002, parent=root)
            for z in (FLOOR_Z + 0.07, (RIM + FLOOR_Z) / 2, RIM - 0.07):
                kit.cylinder(f"nail_{x:.2f}_{side}_{z:.2f}", 0.009, 0.006, (x, y + side * 0.006, z),
                             rot_deg=(90, 0, 0), mat=iron, segments=6, parent=root)
        kit.box(f"strap_under_{x:.2f}", (0.045, WIDTH + 0.02, 0.010), (x, 0, FLOOR_Z - 0.005), mat=iron,
                bevel=0.002, parent=root)


def _footings(kit, mats, rng, root):
    for sx in (-1, 1):
        kit.box(f"footing_{sx}", (0.46, 0.50, 0.12), (sx * 0.68, 0, 0.04),
                (kit.jitter(rng, 2), kit.jitter(rng, 2), kit.jitter(rng, 8)), mats["stone_wall"], bevel=0.03,
                parent=root)
        kit.sphere(f"footing_moss_{sx}", 1.0, (sx * 0.68 + kit.jitter(rng, 0.1), -0.22, 0.102),
                   scale=(0.09, 0.06, 0.012), mat=mats["moss"], segments=8, parent=root)


def _water(kit, mats, rng, root):
    wm = _rainwater()
    w = LENGTH - 0.02
    d = WIDTH - 2 * PLANK_T - 0.004
    verts = [(-w / 2, -d / 2, WATER_Z), (w / 2, -d / 2, WATER_Z), (w / 2, d / 2, WATER_Z), (-w / 2, d / 2, WATER_Z)]
    kit.mesh("trough_water", verts, [(0, 1, 2, 3)], mat=wm, parent=root)
    # green waterline on the inside of the long planks
    for side in (-1, 1):
        x = rng.uniform(-0.6, 0.2)
        kit.box(f"waterline_{side}", (rng.uniform(0.7, 1.3), 0.004, 0.035),
                (x, side * (WIDTH / 2 - PLANK_T - 0.001), WATER_Z + 0.004), mat=mats["moss"], parent=root)
    # floating leaves and a scrap of board
    for i in range(7):
        s = rng.uniform(0.03, 0.055)
        kit.sphere(f"leaf_{i}", 1.0, (rng.uniform(-0.85, 0.85), rng.uniform(-0.2, 0.2), WATER_Z + 0.002),
                   scale=(s, s * 0.55, 0.002), rot_deg=(0, 0, rng.uniform(0, 180)),
                   mat=mats["straw"] if i % 3 else mats["moss"], segments=6, parent=root)
    kit.box("float_scrap", (0.28, 0.045, 0.016), (rng.uniform(-0.5, 0.5), rng.uniform(-0.1, 0.1), WATER_Z + 0.004),
            (0, 0, rng.uniform(-30, 30)), mats["wood_dark"], bevel=0.003, parent=root)


def _tether(kit, mats, rng, root):
    x = LENGTH / 2 + PLANK_T + 0.005
    kit.box("ring_plate", (0.012, 0.07, 0.07), (x, 0, 0.40), mat=mats["iron"], bevel=0.002, parent=root)
    kit.torus("ring", 0.032, 0.006, (x + 0.02, 0, 0.385), (0, 90, 0), mats["iron"], major_segments=16,
              minor_segments=5, parent=root)
    ctrl = [(x + 0.03, 0.0, 0.352), (x + 0.07, 0.015, 0.22), (x + 0.17, 0.05, 0.05), (x + 0.38, 0.12, 0.012),
            (x + 0.50, 0.05, 0.012)]
    _sweep.rope(kit, "tether", ctrl, 0.0115, mats["rope"], root, lay=0.075, step=0.01, sides=5)


def build(kit, mats, rng):
    root = kit.group("trough")
    _footings(kit, mats, rng, root)
    _planks(kit, mats, rng, root)
    _straps(kit, mats, rng, root)
    _water(kit, mats, rng, root)
    _tether(kit, mats, rng, root)
    return root

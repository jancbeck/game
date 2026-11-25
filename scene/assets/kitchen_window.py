"""The one small window of a garrison kitchen: a deep splayed opening with iron bars and a wooden shutter.

Origin: center of the opening's sill on the wall face. The wall face is the XZ plane at y = 0, the
wall lies toward +Y and the room toward -Y. The opening is 0.42 m wide and 0.7 m high, cut through the
wall block named in `BLOCK`, with a dressed stone case and a shutter leaf standing open against the
reveal. A cool point light stands in the opening: dusk coming through the bars.
"""

import math

import bpy

from . import _lights

LIGHTS = []
LIGHT = dict(pos=(0.0, 0.3, 0.38), color=(0.42, 0.58, 1.0), watts=55.0, radius=0.18, specular=0.1)
BLOCK = "block_north_wall"
W, H = 0.42, 0.7
WALL = 0.8


def build(kit, mats, rng):
    root = kit.group("kitchen_window")
    _lights.add(root, "kitchen_window", **LIGHT)
    from .gate_door import _dressed
    dressed = _dressed(mats["stone_wall"])
    block = bpy.data.objects.get(BLOCK)
    if block is not None:
        c = kit.box("cut_kitchen_window", (W, WALL + 0.4, H), (0, WALL / 2, H / 2), parent=root)
        mod = block.modifiers.new("kitchen_window", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = c
        c.hide_render = True
        c.display_type = "WIRE"
    for s in (-1, 1):
        kit.box(f"win_jamb_{s}", (0.14, 0.16, H + 0.04), (s * (W / 2 + 0.07), -0.04, H / 2), mat=dressed, bevel=0.01, parent=root)
    kit.box("win_head", (W + 0.42, 0.18, 0.15), (0, -0.05, H + 0.075), mat=dressed, bevel=0.01, parent=root)
    kit.box("win_sill", (W + 0.46, 0.26, 0.08), (0, -0.09, -0.04), mat=dressed, bevel=0.01, parent=root)
    for k in range(3):
        kit.box(f"win_bar_{k}", (0.02, 0.02, H + 0.08), (-W / 2 + (k + 1) * W / 4, -0.02, H / 2), mat=mats["iron"], parent=root)
    kit.box("win_bar_cross", (W, 0.02, 0.02), (0, -0.02, H * 0.55), mat=mats["iron"], parent=root)
    leaf = kit.group("win_shutter", (-W / 2 - 0.12, -0.1, 0.0), parent=root)
    leaf.rotation_euler = (0, 0, math.radians(-80))
    kit.box("shutter_board", (W * 0.55, 0.04, H - 0.04), (W * 0.27, 0, H / 2), mat=mats["wood_old"], bevel=0.004, parent=leaf)
    kit.box("shutter_strap", (W * 0.55, 0.045, 0.04), (W * 0.27, 0, H * 0.7), mat=mats["iron"], parent=leaf)
    return root

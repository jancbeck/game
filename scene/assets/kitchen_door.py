"""The yard door of a garrison kitchen: a plain stone case in a wall and an oak door standing ajar.

Origin: center of the opening on the wall face at floor level. The wall face is the XZ plane at
y = 0, the wall lies toward +Y and the room toward -Y; the door opens inward. The opening is 1.0 m
wide and 2.05 m high, cut into the wall block named in `BLOCK`. The leaf is turned 34 degrees about
its left hinge, so a strip of the yard shows. The leaf is the object `kitchen_door_leaf`. A cool point light
stands in the opening: the blue dusk of the yard coming in.
"""

import math

import bpy

from . import _lights

LIGHTS = []
LIGHT = dict(pos=(0.0, 0.35, 1.25), color=(0.42, 0.58, 1.0), watts=100.0, radius=0.35, specular=0.1)
BLOCK = "block_north_wall"
W, H = 1.0, 2.05
WALL = 0.8
OPEN_DEG = 34


def build(kit, mats, rng):
    root = kit.group("kitchen_door")
    _lights.add(root, "kitchen_door", **LIGHT)
    from .gate_door import _dressed
    dressed = _dressed(mats["stone_wall"])
    block = bpy.data.objects.get(BLOCK)
    if block is not None:
        c = kit.box("cut_kitchen_door", (W, WALL + 0.4, H), (0, WALL / 2, H / 2), parent=root)
        mod = block.modifiers.new("kitchen_door", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = c
        c.hide_render = True
        c.display_type = "WIRE"
    for s in (-1, 1):
        kit.box(f"door_jamb_{s}", (0.2, 0.2, H + 0.1), (s * (W / 2 + 0.1), -0.06, H / 2 + 0.05), mat=dressed, bevel=0.012,
                parent=root)
    kit.box("door_lintel", (W + 0.6, 0.26, 0.28), (0, -0.07, H + 0.14), mat=dressed, bevel=0.014, parent=root)
    kit.box("door_threshold", (W + 0.2, 0.7, 0.1), (0, 0.22, -0.02), mat=dressed, bevel=0.012, parent=root)
    # the leaf: hinged at x = -W/2, swung into the room
    hinge = kit.group("kitchen_door_leaf", (-W / 2 + 0.02, 0.1, 0.0), parent=root)
    hinge.rotation_euler = (0, 0, -math.radians(OPEN_DEG))
    boards = 5
    bw = (W - 0.06) / boards
    for k in range(boards):
        kit.box(f"leaf_board_{k}", (bw - 0.01, 0.07, H - 0.06), (0.03 + (k + 0.5) * bw, 0, H / 2), mat=mats["door_wood"],
                bevel=0.006, parent=hinge)
    for k, z in enumerate((0.4, H - 0.45)):
        kit.box(f"leaf_strap_{k}", (W - 0.06, 0.03, 0.1), (W / 2, -0.04, z), mat=mats["iron"], bevel=0.004, parent=hinge)
        kit.box(f"leaf_hinge_{k}", (0.22, 0.04, 0.08), (0.1, -0.05, z), mat=mats["iron"], bevel=0.004, parent=hinge)
    kit.box("leaf_latch", (0.14, 0.04, 0.04), (W - 0.12, -0.055, 1.0), mat=mats["iron"], parent=hinge)
    return root

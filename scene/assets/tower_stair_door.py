"""The stair door at the east end of the back wall of the commander's chamber: a low oak door ajar on its hinges, a dressed stone case, a worn threshold, and the dark of the spiral stair behind.

The opening is 0.85 m wide and 2.1 m high; the plan's blocks leave it open in the wall (back_wall_w, back_wall_e and the
lintel block) and this prop cuts the passage on through the stair turret (block `stair_turret`, which stands behind the wall) and sets
three worn steps going down into the dark. Origin: the middle of the opening on the wall's inner face at floor level; the wall (0.75 m)
lies toward +Y, the room toward -Y. The leaf is hinged on the east jamb and stands 30 degrees into the room.
"""

import math

import bpy

from . import _tower as T

LIGHTS = []
BLOCK = "block_stair_turret"
OW, OH, WALL = 0.85, 2.1, 0.75
STEPS = ((0.0, 0.30, -0.18), (0.30, 0.55, -0.38), (0.55, 0.72, -0.58))     # (y from, y to, top z) beyond the wall's outer face


def build(kit, mats, rng):
    root = kit.group("tower_stair_door")
    dressed = T.dressed(mats)
    wd, iron, door = mats["wood_dark"], mats["iron"], mats["door_wood"]
    # case: dressed jambs and head standing proud of the wall, a worn threshold across the wall's thickness
    for n, s in enumerate((-1, 1)):
        kit.box(f"case_jamb_{n}", (0.15, 0.13, OH + 0.12), (s * (OW / 2 + 0.075), -0.03, (OH + 0.12) / 2), mat=dressed, bevel=0.01, parent=root)
    kit.box("case_head", (OW + 0.5, 0.13, 0.16), (0, -0.03, OH + 0.08), mat=dressed, bevel=0.01, parent=root)
    kit.box("threshold", (OW + 0.04, WALL, 0.05), (0, WALL / 2, 0.025), mat=dressed, bevel=0.012, parent=root)
    # the passage through the turret, three steps down into the dark
    block = bpy.data.objects.get(BLOCK)
    cutter = kit.box("cut_passage", (OW, 0.95, OH + 1.0), (0, WALL + 0.475 - 0.05, (OH - 1.0) / 2), parent=root)
    if block is not None:
        mod = block.modifiers.new("passage", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter
        cutter.hide_render = True
        cutter.display_type = "WIRE"
    for n, (y0, y1, top) in enumerate(STEPS):
        kit.box(f"step_{n}", (OW, y1 - y0, top + 1.0), (0, WALL + (y0 + y1) / 2, (top - 1.0) / 2), mat=dressed, bevel=0.01, parent=root)
    # the leaf: oak boards, iron straps, a ring, studs; hinged at the east jamb (local +x)
    hinge = (OW / 2 - 0.015, -0.03)
    phi = math.radians(30)
    ln, h = OW - 0.03, OH - 0.1
    dx, dy = -math.cos(phi), -math.sin(phi)
    leaf = kit.group("door_leaf", (hinge[0] + dx * ln / 2, hinge[1] + dy * ln / 2, 0.05 + h / 2), parent=root)
    leaf.rotation_euler = (0, 0, math.atan2(dy, dx))
    nb = 5
    for k in range(nb):
        kit.box(f"board_{k}", (ln / nb - 0.004, 0.05, h), (-ln / 2 + ln / nb * (k + 0.5), 0, 0), mat=door, bevel=0.004, parent=leaf)
    for zz in (-h * 0.36, 0.0, h * 0.36):
        kit.box("strap", (ln * 0.96, 0.012, 0.075), (0.0, -0.03, zz), mat=iron, parent=leaf)
    kit.torus("ring", 0.04, 0.006, (-ln / 2 + 0.12, -0.04, -0.05), (90, 0, 0), iron, major_segments=12, minor_segments=4, parent=leaf)
    for k in range(10):
        kit.sphere(f"stud_{k}", 0.011, (-ln / 2 + 0.1 + 0.07 * (k % 5), -0.032, h * (0.28 if k < 5 else -0.28)), mat=iron, segments=6,
                   parent=leaf)
    return root

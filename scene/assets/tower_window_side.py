"""The side window of the commander's chamber, in the east wall: a splayed embrasure with both shutter leaves closed.

Origin: the middle of the opening on the wall's inner face at floor level, wall toward +Y, room
toward -Y; the recess is 0.6 m deep in the 1.6 m wall, which stays solid behind it; the plan turns it by -90 degrees onto the east wall. Dusk shows only as a cool light that leaks round the
boards and falls on the rack in the corner (the light stands in front of the shutters). The leaves are barred.
"""

from . import _tower as T

LIGHTS = []
BLOCK = "block_east_wall"
WALL = 0.6


def build(kit, mats, rng):
    root = kit.group("tower_window_side")
    T.window(kit, mats, root, BLOCK, WALL, lights_w=0.3, wi=1.1, leaves=(0.0, 2.0), light_watts=35.0, throat=0.22, light_y=-0.3,
             name="tower_window_side")
    kit.box("shutter_bar", (1.12, 0.05, 0.07), (0.0, -0.09, 1.75), mat=mats["wood_dark"], bevel=0.006, parent=root)
    return root

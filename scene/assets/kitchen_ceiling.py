"""The ceiling of the cookhouse that the cutaway takes away, and the dusk that comes in where a wall is missing.

The ceiling is a slab of dark boards over the kitchen and the larder, invisible to the camera
(`visible_camera` off) and solid to light: moon and sky cannot fall in from above, so the rooms are lit by the
hearth and oven, the window and the door, and the fill below, and the underside of the boards throws
a little of the hearth's light back down. The front and the west side are open, as the cutaway is, and two
soft cool lights stand where the south wall was, one before each room: dusk coming over the low sill. They
light the north wall and the floor, and the faces of the partition and the east wall, which look west, only
at a grazing angle. The slab is not exported as geometry (it is far over the body band), and not seen in any pass.

Origin: the middle of the ceiling at z = 0. It covers x -2.6 .. 6.7, y -2.75 .. 1.95 at z = 3.35.
"""

from . import _lights

LIGHTS = []
X0, X1, Y0, Y1, Z = -2.6, 6.7, -2.75, 1.95, 3.35
FILL = dict(color=(0.50, 0.64, 1.0), watts=1500.0, radius=2.6, specular=0.0)


def build(kit, mats, rng):
    root = kit.group("kitchen_ceiling")
    slab = kit.box("ceiling_slab", (X1 - X0, Y1 - Y0, 0.12), ((X0 + X1) / 2, (Y0 + Y1) / 2, Z + 0.06), mat=mats["wood_dark"],
                   parent=root)
    slab.visible_camera = False
    # two soft cool lights low in front of the room, one for each room, shining in under the front edge
    _lights.add(root, "kitchen_fill_kitchen", pos=(0.8, -8.0, 2.8), **FILL)
    _lights.add(root, "kitchen_fill_larder", pos=(5.0, -8.0, 2.8), **FILL)
    return root

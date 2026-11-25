"""Beehive bread oven of a garrison kitchen: a stone platform with a dome, mouth toward the room.

The oven is the cookhouse's (assets/_shed_hearth.oven) with its own warm light and a coal bed that
glows in spots (the shared one glows along cracks). Origin: the oven's footprint is centered at
x = 0.62 and y = -0.36 of the prop frame, so place the root 0.62 m west and 0.36 m south of where
the oven's center goes. The mouth faces -Y, the back of the platform is at about y = +0.06, so a
root 0.1 m in front of a south-facing wall puts the oven against it. Ash lies on the floor in front.
"""

from . import _kitchen, _lights
from . import _shed_hearth as hearth

LIGHTS = []
LIGHT = dict(pos=(0.62, -0.62, 0.98), color=(1.0, 0.3, 0.05), watts=34.0, radius=0.1, specular=0.2, reach=4.5)
LIGHT_FLOOR = dict(pos=(0.62, -1.15, 0.5), color=(1.0, 0.3, 0.05), watts=20.0, radius=0.25, specular=0.05, reach=3.5)


def build(kit, mats, rng):
    root = kit.group("kitchen_oven")
    _lights.add(root, "kitchen_oven", **LIGHT)
    _lights.add(root, "kitchen_oven_floor", **LIGHT_FLOOR)
    hearth.oven(kit, mats, rng, root)
    # the coal bed of the shared oven is replaced by the kitchen's
    coals = next(ob for ob in root.children if ob.name.startswith("oven_coals"))
    coals.data.materials.clear()
    coals.data.materials.append(_kitchen.coal_material(mats))
    ox, oy = hearth.OVEN
    # raked-out ash on the floor below the mouth
    _kitchen.scatter_blobs(kit, rng, "oven_ash", mats["ash"], root, (ox, oy - 0.95), (0.25, 0.1), 9, (0.03, 0.08), 0.004)
    return root

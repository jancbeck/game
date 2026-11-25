"""The ceiling of the chamber that the cutaway takes away, and the dusk that comes over the sill.

A slab of dark boards over the whole room, invisible to the camera (`visible_camera` off) and solid to
light: the moon cannot fall in from above, so the room is lit by its own flames, the windows and the fill. The
front is open as the cutaway is. One soft cool point light stands where the south wall was, high in front; it lights the room and the live figures. Two area lights in the same
places, which the game does not export, brighten the frame alone so the boards, the bed and the desk read in blue without overlighting a figure. The slab is not
exported as geometry (it is far over the body band) and not seen in any pass.

Origin: the middle of the room at z = 0. The slab covers x -2.85 .. 2.85, y -2.5 .. 2.2 at z = 2.82, so the tops of the walls stay in the moon's light.
"""

import bpy
from mathutils import Vector

from . import _lights

LIGHTS = []
X0, X1, Y0, Y1, Z = -2.85, 2.85, -2.5, 2.2, 2.82
FILL = dict(color=(0.50, 0.64, 1.0), watts=1500.0, radius=2.6, specular=0.0)


def build(kit, mats, rng):
    root = kit.group("tower_ceiling")
    slab = kit.box("ceiling_slab", (X1 - X0, Y1 - Y0, 0.12), ((X0 + X1) / 2, (Y0 + Y1) / 2, Z + 0.06), mat=mats["wood_dark"],
                   parent=root)
    slab.visible_camera = False
    _lights.add(root, "tower_fill_front", pos=(0.2, -6.5, 4.4), **FILL)
    # two area lights for the frame alone: only point lights reach the game's live figures, which the point fill already lights
    _area(root, "tower_fill_area_front", (0.2, -6.5, 4.4), (0.0, 0.4, 0.8), 3.0, 800.0)
    _area(root, "tower_fill_area_mid", (0.0, -0.4, 2.7), (0.0, -0.4, 0.0), 1.6, 90.0)
    return root


def _area(root, name, pos, target, size, watts):
    """A cool square area light at `pos` aimed at `target`; `light_scale()` of layout.json applies as it does to the point lights."""
    data = bpy.data.lights.new(f"light_{name}", "AREA")
    data.shape = "SQUARE"
    data.size = size
    data.color = (0.50, 0.64, 1.0)
    data.energy = watts * _lights.light_scale()
    data.specular_factor = 0.0
    ob = bpy.data.objects.new(f"light_{name}", data)
    bpy.context.collection.objects.link(ob)
    ob.parent = root
    ob.location = pos
    ob.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    return ob

"""Point lights that an asset places itself, for props whose light needs more than LIGHTS offers.

build_scene.py turns every entry of a module's LIGHTS list into a plain point light with full
specular. On the wet stone that gives round, hard-edged glints: a flame light shining on a wall
leaves a disc on the stone at the mirror point of the camera, away from the flame. An asset that
calls `add` instead of listing the light in LIGHTS controls three things:

- `specular`: scales the light's mirror highlight (1 is the default light). Walls and wet cobbles
  both shine; use a low value for lights near walls and a high one for fires standing on the floor.
- `radius`: light size in meters. A bigger light makes a softer, wider highlight and soft shadows.
- `reach`: distance in meters at which the light has faded to nothing. The fade is smooth, and it
  keeps a floor fire from lighting walls far across the yard.

The watts are root-relative like LIGHTS entries and are multiplied by `prop_light_scale` from
layout.json, as build_scene.py does for LIGHTS. The light is a child of the prop root, so it moves
and turns with the prop. Lights cast shadows, and the scene's shadow budget is the same as for
LIGHTS entries.
"""

import bpy

import location

_scale = None


def light_scale():
    """`prop_light_scale` from the location's layout.json (1.0 when it is missing)."""
    global _scale
    if _scale is None:
        try:
            _scale = float(location.load("layout.json").get("prop_light_scale", 1.0))
        except (OSError, ValueError):
            _scale = 1.0
    return _scale


def add(root, name, pos, color, watts, radius=0.25, specular=1.0, reach=None, shadow=True):
    """Point light named `light_<name>` at root-relative `pos`; returns the light object."""
    data = bpy.data.lights.new(f"light_{name}", "POINT")
    data.color = color
    data.energy = watts * light_scale()
    data.shadow_soft_size = radius
    data.specular_factor = specular
    data.use_shadow = shadow
    if reach:
        data.use_custom_distance = True
        data.cutoff_distance = reach
    ob = bpy.data.objects.new(f"light_{name}", data)
    bpy.context.collection.objects.link(ob)
    ob.parent = root
    ob.location = pos
    return ob

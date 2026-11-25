"""Small helpers for reading plan.json: entries, heights, wall blocks and the floor polygon."""

import math

from mathutils import Vector


def entries(section):
    """(key, value) pairs of a plan section without its `_doc`-style keys."""
    return [(k, v) for k, v in section.items() if not k.startswith("_")]


def height(value, heights):
    """A height given as a number or as a name in plan["heights"]."""
    return heights[value] if isinstance(value, str) else value


def resolve_block(b):
    """A block with center, size and rot_z (degrees); a wall given by its center line `from` -> `to`
    and a thickness `t` is turned into that form."""
    if "from" in b:
        a, c = Vector((*b["from"], 0)), Vector((*b["to"], 0))
        b = dict(b, center=list((a + c) / 2)[:2], size=[(c - a).length + b["t"] * 0.5, b["t"]],
                 rot_z=math.degrees(math.atan2(c.y - a.y, c.x - a.x)))
    return b


def inside_polygon(x, y, poly):
    """Even-odd point-in-polygon test on the XY plane; poly is a list of (x, y) pairs."""
    inside = False
    for i in range(len(poly)):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % len(poly)]
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            inside = not inside
    return inside

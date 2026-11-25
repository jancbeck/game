"""What lies around the commander's chamber: the rock the tower is built against, the lower storey under the floor.

Origin: the middle of the room at z = 0. The walls, the courtyard wall on the east and the lower storey's face are plan blocks
(plan.json); this prop adds what they do not have, so that nothing around the room is void and the valley shows only through
the window:

- a spur of the cliff rock hugging the west wall, its top about 1 m over the floor, falling away to the west and the
  front, solid down to the rock shelf 9 m under the floor;
- a ledge of rock under the courtyard wall in the south-east corner of the frame, where the wall stands on the cliff;
- a roofed stretch of that wall-walk, a guard post, whose shed roof fills the top right corner of the frame;
- a dressed string course along the foot of the chamber, where the floor ends and the lower storey begins, and one lower
  course, each casting a shadow band on the face below.
"""

import math

import bmesh
import bpy
from mathutils import Vector, noise

from . import load
from .tower_ceiling import _area

LIGHTS = []
SHELF = -9.2


def _n(x, y, scale, seed):
    return noise.noise(Vector((x * scale + seed, y * scale - seed, seed * 0.37)))


def _terrace(h, rise=0.4):
    """Heights stepped into ledges `rise` m apart with steep risers: bedded rock."""
    k = math.floor(h / rise)
    f = h / rise - k
    t = max(0.0, min(1.0, (f - 0.55) / 0.45))
    return (k + t * t * (3 - 2 * t)) * rise


def _slab(kit, name, box, top, mat, root, step=0.15, smooth=True):
    """A solid of rock: a grid over box (x0, x1, y0, y1) at heights top(x, y), a vertical skirt down to the rock shelf."""
    x0, x1, y0, y1 = box
    nx, ny = int(round((x1 - x0) / step)), int(round((y1 - y0) / step))
    bm = bmesh.new()
    grid = [[bm.verts.new((x0 + i * (x1 - x0) / nx, y0 + j * (y1 - y0) / ny, 0.0)) for i in range(nx + 1)] for j in range(ny + 1)]
    for j in range(ny + 1):
        for i in range(nx + 1):
            v = grid[j][i]
            v.co.z = top(v.co.x, v.co.y)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    loop = ([grid[0][i] for i in range(nx + 1)] + [grid[j][nx] for j in range(1, ny + 1)]
            + [grid[ny][i] for i in range(nx - 1, -1, -1)] + [grid[j][0] for j in range(ny - 1, 0, -1)])
    low = [bm.verts.new((v.co.x, v.co.y, SHELF)) for v in loop]
    for k in range(len(loop)):
        a, b = loop[k], loop[(k + 1) % len(loop)]
        c, d = low[(k + 1) % len(loop)], low[k]
        bm.faces.new((a, d, c, b))
    bm.faces.new(low[::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.parent = root
    for p in me.polygons:
        p.use_smooth = smooth
    return ob


def build(kit, mats, rng):
    root = kit.group("tower_surround")
    rock, st = mats["cliff_rock"], mats["stone_wall"]

    # the spur west of the tower: highest at the wall, a broken slope to the west, rounded at the front and the back
    def west(x, y):
        out = max(0.0, -4.9 - x)
        front = max(0.0, -1.6 - y)
        back = max(0.0, y - 4.6)
        bed = _terrace(1.3 + 0.75 * _n(x, y, 0.45, 3.0) + 0.3 * _n(x, y, 1.3, 8.0))
        return bed + 0.09 * _n(x, y, 4.3, 1.0) - out * 0.85 - front * 1.1 - back * 0.7
    _slab(kit, "rock_west", (-8.5, -4.25, -2.9, 7.2), west, rock, root)

    # the ledge under the courtyard wall: the wall's foot sits on it, rounded to the front
    def east(x, y):
        front = max(0.0, -0.4 - y)
        bed = _terrace(-2.3 + 0.6 * _n(x, y, 0.7, 5.0) + 0.25 * _n(x, y, 2.3, 2.0))
        return bed + 0.07 * _n(x, y, 4.0, 4.0) - front * 1.25 - max(0.0, x - 7.5) * 0.4
    _slab(kit, "rock_east_ledge", (3.9, 9.4, -2.2, 0.5), east, rock, root)

    # boulders and scrub on the spur
    for k in range(9):
        x, y = rng.uniform(-7.4, -4.6), rng.uniform(-1.6, 5.0)
        r = rng.uniform(0.22, 0.55)
        z = west(x, y) + r * 0.2
        kit.sphere(f"boulder_{k}", r, (x, y, z), (rng.uniform(0.9, 1.4), rng.uniform(0.8, 1.2), rng.uniform(0.5, 0.8)),
                   (rng.uniform(-12, 12), rng.uniform(-12, 12), rng.uniform(0, 180)), rock, segments=9, parent=root)
    bush = load("dead_bush")
    for k, (x, y) in enumerate(((-4.9, -0.4), (-5.7, 2.6), (-5.2, -1.5), (-5.0, 3.9))):
        ob = bush.build(kit, mats, rng)
        ob.parent = root
        ob.location = (x, y, west(x, y) - 0.04)
        ob.rotation_euler = (0, 0, rng.uniform(0, 6.28))
    # a roofed stretch of the courtyard's wall-walk, a guard post: posts on the low parapet and on the walk, a shed roof of
    # planks that falls toward the cliff and covers the top right corner of the frame
    wd, wo = mats["wood_dark"], mats["wood_old"]
    for n, x in enumerate((5.5, 7.4, 9.2)):
        kit.box(f"roof_post_front_{n}", (0.2, 0.2, 2.2), (x, 0.55, 1.1 + 1.1), mat=wd, bevel=0.01, parent=root)
        kit.box(f"roof_post_back_{n}", (0.2, 0.2, 2.8), (x, 2.45, 0.1 + 1.4), mat=wd, bevel=0.01, parent=root)
    tilt = 8.5
    kit.box("roof_planks", (4.7, 3.3, 0.1), (7.3, 1.75, 3.05), (-tilt, 0, 0), wo, bevel=0.01, parent=root)
    for n in range(10):
        kit.box(f"roof_batten_{n}", (4.7, 0.07, 0.05), (7.3, 0.2 + n * 0.33, 3.3 - n * 0.33 * math.tan(math.radians(tilt)) + 0.0),
                (-tilt, 0, 0), wd, bevel=0.005, parent=root)
    # string courses: the floor line of the chamber, and a lower one
    for n, (z, h, d) in enumerate(((-0.1, 0.2, 0.16), (-1.35, 0.14, 0.1))):
        kit.box(f"string_course_{n}", (8.9, d, h), (0.0, -2.4 - d / 2 + 0.02, z), mat=st, bevel=0.012, parent=root)
    # cool light for the frame alone (area lights are not exported): the courtyard wall and the rock lie in the tower's moon shadow
    _area(root, "tower_fill_wall", (8.6, -3.6, 3.2), (6.2, 1.6, 0.4), 3.0, 650.0)
    _area(root, "tower_fill_rock", (-8.0, -3.4, 3.2), (-5.8, 1.5, 0.8), 3.0, 160.0)
    return root

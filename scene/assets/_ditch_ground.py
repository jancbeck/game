"""The ditch's ground skin and water: mud surface, ditch pool, track puddles, gully rill, water material.

Helper of west_ditch.py. All meshes here are built in world coordinates and parked under the prop root
with an offset that cancels the root's own, so the root must stand at `_ditch_field.ORIGIN` on the lower
ward. The mud shader works in object coordinates, which are then world coordinates, exactly like the
terrain's: the skin continues the terrain's mud without a seam.
"""

import math
import random

import bpy

from mats.cobble_wet import _math, _mix, _node, _noise, _range, _xyz, water_ripples

from . import _ditch_field as F

WATER_DEEP = (0.011, 0.015, 0.018)       # silty ditch water: nearly black, the mirror does the rest
WATER_TEA = (0.052, 0.040, 0.022)        # shallows and puddles: brown from the earth below
SCUM = (0.036, 0.052, 0.020)             # duckweed and algae film
LEAVES = (0.075, 0.052, 0.026)           # drowned leaves
ROUGH_WATER = 0.03
WET_MUD_DARK = (0.012, 0.009, 0.006)     # saturated mud: much darker than the dry earth around it
WET_MUD_LIGHT = (0.030, 0.023, 0.014)
COAT_IOR = 1.45                          # a faint second reflection on top of the water's own: a sky sheen from a high view
WATER_COAT = 0.08                        # weight of that second reflection


# ---------------------------------------------------------------- mesh plumbing

def _world_object(kit, name, verts, faces, mat, root, smooth=True):
    """Mesh given in world coordinates; the object's offset cancels the root's."""
    loc = (-F.ORIGIN[0], -F.ORIGIN[1], -F.LOWER_WARD)
    ob = kit.mesh(name, verts, faces, loc=loc, mat=mat, parent=root)
    if smooth:
        for p in ob.data.polygons:
            p.use_smooth = True
    return ob


def _vertex_attribute(ob, name, values):
    me = ob.data
    attr = me.color_attributes.new(name=name, type="FLOAT_COLOR", domain="POINT")
    flat = []
    for v in values:
        flat += [v, v, v, 1.0]
    attr.data.foreach_set("color", flat)


# ---------------------------------------------------------------- ground skin

def _columns():
    xs = []
    x = F.X_MAX
    while x > F.X_MIN - 1e-6:
        xs.append(x)
        x -= 0.07 if x > -15.9 else (0.12 if x > -19.5 else 0.4)
    return xs


def build_ground(kit, mats, root):
    xs = _columns()
    nx = len(xs)
    ny = int(round((F.Y_MAX - F.Y_MIN) / 0.1)) + 1
    verts, faces = [], []
    for j in range(ny):
        y = F.Y_MIN + j * 0.1
        for x in xs:
            verts.append((x, y, F.ground(x, y)))
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    ob = _world_object(kit, "ditch_ground", verts, faces, mats["mud"], root)
    return ob


# ---------------------------------------------------------------- water material

def water_material():
    mat = bpy.data.materials.get("west_ditch_water")
    if mat is not None:
        return mat
    mat = bpy.data.materials.new("west_ditch_water")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    pos = _node(nt, "ShaderNodeTexCoord").outputs["Object"]
    attr = _node(nt, "ShaderNodeAttribute", attribute_name="shore", attribute_type="GEOMETRY")
    shore = _xyz(nt, attr.outputs["Vector"])[0]       # 0 over open water, 1 at the rim and in puddles

    # color: black in the deep, brown in the shallows; a film of scum and leaves gathers at the edges
    tea = _range(nt, shore, 0.2, 1.0, 0.0, 0.85, smooth=True)
    water = _mix(nt, tea, WATER_DEEP, WATER_TEA)
    film_field = _noise(nt, pos, 0.8, 4.0, "2D", rough=0.6, distortion=0.3)
    film = _math(nt, "MULTIPLY", _range(nt, film_field, 0.50, 0.66, smooth=True),
                 _range(nt, shore, 0.15, 0.85, 0.15, 1.0, smooth=True))
    film = _math(nt, "MULTIPLY", film, _range(nt, shore, 0.98, 0.9, 1.0, 0.0))     # not in the puddles
    tint = _mix(nt, _range(nt, _noise(nt, pos, 6.0, 3.0, "2D"), 0.4, 0.6, smooth=True), SCUM, LEAVES)
    color = _mix(nt, film, water, tint)
    nt.links.new(color, bsdf.inputs["Base Color"])

    nt.links.new(_range(nt, film, 0.0, 1.0, ROUGH_WATER, 0.5), bsdf.inputs["Roughness"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.45
    nt.links.new(_range(nt, film, 0.0, 1.0, WATER_COAT, 0.0), bsdf.inputs["Coat Weight"])
    bsdf.inputs["Coat Roughness"].default_value = ROUGH_WATER
    bsdf.inputs["Coat IOR"].default_value = COAT_IOR

    bump = _node(nt, "ShaderNodeBump", {"Height": water_ripples(nt, pos), "Distance": 0.03, "Strength": 0.55})
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Coat Normal"])
    return mat


# ---------------------------------------------------------------- wet mud decal

def wet_mud_material():
    """A film of dark, glossy mud laid over the skin where the ground is saturated; its opacity is the
    vertex attribute `wet` and its edge is ragged."""
    mat = bpy.data.materials.get("west_wet_mud")
    if mat is not None:
        return mat
    mat = bpy.data.materials.new("west_wet_mud")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    pos = _node(nt, "ShaderNodeTexCoord").outputs["Object"]
    attr = _node(nt, "ShaderNodeAttribute", attribute_name="wet", attribute_type="GEOMETRY")
    wet = _xyz(nt, attr.outputs["Vector"])[0]
    grain = _noise(nt, pos, 9.0, 4.0, "2D")
    alpha = _range(nt, _math(nt, "MULTIPLY", wet, _math(nt, "MULTIPLY_ADD", grain, 0.8, 0.6)), 0.14, 0.5, 0.0, 0.96,
                   smooth=True)
    color = _mix(nt, _range(nt, grain, 0.35, 0.65, smooth=True), WET_MUD_DARK, WET_MUD_LIGHT)
    nt.links.new(color, bsdf.inputs["Base Color"])
    nt.links.new(alpha, bsdf.inputs["Alpha"])
    nt.links.new(_range(nt, wet, 0.3, 1.0, 0.5, 0.2), bsdf.inputs["Roughness"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.45
    nt.links.new(_range(nt, wet, 0.4, 1.0, 0.0, 0.12), bsdf.inputs["Coat Weight"])
    bsdf.inputs["Coat Roughness"].default_value = 0.12
    bsdf.inputs["Coat IOR"].default_value = COAT_IOR
    bump = _node(nt, "ShaderNodeBump", {"Height": water_ripples(nt, pos), "Distance": 0.03, "Strength": 0.7})
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Coat Normal"])
    return mat


def build_wet_mud(kit, root):
    """Decal grid over the strip between the wall and the outer bank; quads that stay dry are left out."""
    x0, x1 = -19.8, -13.0
    y0, y1 = -16.2, 13.5
    step = 0.09
    nx, ny = int(round((x1 - x0) / step)), int(round((y1 - y0) / step))
    verts, wet = [], []
    for j in range(ny + 1):
        y = y0 + j * step
        for i in range(nx + 1):
            x = x1 - i * step
            z = F.ground(x, y)
            verts.append((x, y, z + 0.006))
            wet.append(F.wetness(x, y, z))
    faces = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            q = (a, a + 1, a + nx + 2, a + nx + 1)
            if max(wet[v] for v in q) > 0.05:
                faces.append(q)
    ob = _world_object(kit, "wet_mud", verts, faces, wet_mud_material(), root)
    _vertex_attribute(ob, "wet", wet)
    ob.visible_shadow = False
    return ob


# ---------------------------------------------------------------- ditch pool

def build_pool(kit, root):
    """One flat sheet at the water level over the ditch. Ground higher than the sheet hides it, so the
    waterline is wherever the ground crosses the water level; cells are kept only where the skin there
    still holds the ditch, so the sheet ends inside the ground at both ends."""
    W = F.water_level()
    verts, faces, shore = [], [], []
    step_y = 0.2
    cols = 28
    rows = []
    y = F.Y_MIN
    while y <= F.Y_MAX + 1e-6:
        if F.depth_weight(y) >= 0.34:
            c, hw = F.centre(y), F.half_width(y)
            reach = hw + 0.55
            row = []
            for i in range(cols + 1):
                x = c - reach + 2 * reach * i / cols
                row.append(len(verts))
                verts.append((x, y, W))
                shore.append(1.0 - min(1.0, max(0.0, (W - F.ground(x, y)) / 0.22)))
            rows.append((y, row))
        y += step_y
    for (y0, a), (y1, b) in zip(rows, rows[1:]):
        if y1 - y0 > step_y * 1.5:
            continue
        for i in range(cols):
            faces.append((a[i], a[i + 1], b[i + 1], b[i]))
    ob = _world_object(kit, "ditch_water", verts, faces, water_material(), root)
    _vertex_attribute(ob, "shore", shore)
    ob.visible_shadow = False
    return ob


# ---------------------------------------------------------------- puddles and rill

def build_puddles(kit, root):
    """A flat disc of water at the lowest point of each hollow, a little above its floor."""
    rng = random.Random(77)
    verts, faces, shore = [], [], []
    for px, py, rx, ry, depth in F.PUDDLES:
        level = F.ground(px, py) + 0.030
        base = len(verts)
        verts.append((px, py, level))
        shore.append(0.7)
        n = 22
        phase = rng.uniform(0, 6.28)
        for i in range(n):
            a = 2 * math.pi * i / n
            wob = 1.0 + 0.18 * math.sin(3 * a + phase) + 0.1 * math.sin(5 * a + phase * 2)
            verts.append((px + math.cos(a) * rx * 1.55 * wob, py + math.sin(a) * ry * 1.55 * wob, level))
            shore.append(0.7)
        for i in range(n):
            faces.append((base, base + 1 + i, base + 1 + (i + 1) % n))
    ob = _world_object(kit, "track_puddles", verts, faces, water_material(), root)
    _vertex_attribute(ob, "shore", shore)
    ob.visible_shadow = False
    return ob


def build_rill(kit, root):
    """The drain's runoff, a thin bright thread of water in the gully, following the ground down to the ditch."""
    pts = [(F.WALL_X - e, y) for e, y in F.GULLY]
    path = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = 10
        for i in range(n):
            t = i / n
            path.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    path.append(pts[-1])
    verts, faces, shore = [], [], []
    for i, (x, y) in enumerate(path):
        if i + 1 < len(path):
            tx, ty = path[i + 1][0] - x, path[i + 1][1] - y
        else:
            tx, ty = x - path[i - 1][0], y - path[i - 1][1]
        ln = math.hypot(tx, ty) or 1.0
        nx_, ny_ = -ty / ln, tx / ln
        w = 0.075 * (1.0 + 0.5 * i / len(path))
        for s in (-1, 1):
            vx, vy = x + nx_ * w * s, y + ny_ * w * s
            verts.append((vx, vy, F.ground(x, y) + 0.020))
            shore.append(0.75)
    for i in range(len(path) - 1):
        a = i * 2
        faces.append((a, a + 1, a + 3, a + 2))
    ob = _world_object(kit, "gully_rill", verts, faces, water_material(), root)
    _vertex_attribute(ob, "shore", shore)
    ob.visible_shadow = False
    return ob

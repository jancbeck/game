"""Building pieces shared by the props of the commander's chamber: the splayed window, candles, cloth, half cylinders.

Not a prop module: the leading underscore keeps it out of assets.available().

Wall props use the cookhouse's frame: origin on the wall's inner face at floor level, the wall
toward +Y, the room toward -Y.
"""

import math

import bpy

from . import _fire, _lights

COOL = (0.42, 0.58, 1.0)           # dusk coming through an opening
WARM = (1.0, 0.52, 0.18)           # a candle or a lamp


def dressed(mats):
    from .gate_door import _dressed
    return _dressed(mats["stone_wall"])


def prism(kit, name, a, b, mat=None, parent=None):
    """Closed solid between two quads of 4 points each (the same winding): a splayed cut, a tapering post."""
    verts = list(a) + list(b)
    faces = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return kit.mesh(name, verts, faces, mat=mat, parent=parent)


def quad_uv(kit, name, corners, mat, parent):
    """A flat quad with UVs 0..1: corners are (x, y, z) in the order bottom-left, bottom-right, top-right, top-left."""
    ob = kit.mesh(name, corners, [(0, 1, 2, 3)], mat=mat, parent=parent)
    uv = ob.data.uv_layers.new(name="UVMap")
    for loop, co in zip(uv.data, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop.uv = co
    return ob


def half_cyl(kit, name, length, radius, z, mat, parent, axis="x", loc=(0.0, 0.0), segments=14, bevel=0.0):
    """Upper half of a cylinder lying along `axis`, flat side down at height z: a chest lid, a barrel vault."""
    verts, faces = [], []
    for i in range(segments + 1):
        a = math.pi * i / segments
        verts.append((math.cos(a) * radius, math.sin(a) * radius))
    pts = []
    for e in (-length / 2, length / 2):
        for (c, s) in verts:
            pts.append((e, c, s) if axis == "x" else (c, e, s))
    n = segments + 1
    f = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    for i in range(n - 1):
        f.append((i, i + 1, n + i + 1, n + i))
    f.append((n - 1, 0, n, 2 * n - 1))
    ob = kit.mesh(name, pts, f, loc=(loc[0], loc[1], z), mat=mat, parent=parent, bevel=bevel)
    return ob


def candle(kit, mats, root, name, loc, h=0.18, r=0.012, lit=True, tall=1.0):
    """A tallow candle in a holder: a wax stub, a wick, a small flame when lit."""
    x, y, z = loc
    kit.cylinder(f"{name}_wax", r, h, (x, y, z + h / 2), mat=mats["candle"], segments=8, parent=root)
    kit.cylinder(f"{name}_wick", 0.0015, 0.012, (x, y, z + h + 0.005), mat=mats["iron"], segments=4, parent=root)
    if lit:
        _fire.flame(kit, mats["fire"], root, f"{name}_flame", (x, y, z + h + 0.008), 0.042 * tall, 0.0075, lean=(0.02, 0.0),
                    twist=0.8, phase=x * 40.0 + y * 17.0, rings=10, sides=6)


def cloth(kit, name, x_of, z_top, z_bottom, y0, y1, nz, ny, fold, phase, mat, parent, hem=0.04, wave_axis="y"):
    """A hanging curtain: `ny` columns from y0 to y1, `nz` rows from z_top down to a ragged hem. The cloth folds in x by
    `fold` m with the column phase; `x_of(y)` is the line it hangs from. Returns the object, thickened a little."""
    verts, faces = [], []
    for j in range(ny + 1):
        t = j / ny
        y = y0 + (y1 - y0) * t
        bottom = z_bottom + hem * math.sin(11.0 * t + phase) * 0.5 + hem * 0.5
        for i in range(nz + 1):
            s = i / nz
            z = z_top + (bottom - z_top) * s
            amp = fold * (0.45 + 0.55 * s)
            x = x_of(y) + amp * math.sin(2 * math.pi * 3.2 * t + phase + 0.6 * s)
            verts.append((x, y, z))
    for j in range(ny):
        for i in range(nz):
            a = j * (nz + 1) + i
            faces.append((a, a + 1, a + nz + 2, a + nz + 1))
    ob = kit.mesh(name, verts, faces, mat=mat, parent=parent)
    for p in ob.data.polygons:
        p.use_smooth = True
    kit.solidify(ob, 0.012)
    return ob


def window(kit, mats, root, block, T, *, lights_w=0.34, wi=1.3, z0=1.05, z1=2.35, throat=0.3, sill_drop=0.1,
           head_rise=0.2, leaves=(125.0, 125.0), light_watts=100.0, name="win", straps=True, light_y=None):
    """A deep embrasure of two lights cut into the wall block `block` (thickness T): a narrow throat on the outer face,
    a splay widening to `wi` on the inner one, a timber lintel, a mullion and one shutter leaf per side.

    `leaves` are the opening angles of the right and left leaf in degrees: 0 closed in the plane of the inner face,
    90 standing out square, negative folded into the reveal, flat against the splayed jamb. Returns nothing; the parts hang under root.
    """
    st, wd, wo, iron = mats["stone_wall"], mats["wood_dark"], mats["wood_old"], mats["iron"]
    wt = 2 * lights_w + 0.12
    y_t = T - throat
    zi0, zi1 = z0 - sill_drop, z1 + head_rise
    d = 0.06                                   # the cut starts a little into the room, for a clean boolean
    k = d / y_t
    ex = wi / 2 + (wi - wt) / 2 * k
    inner = [(-ex, -d, zi0 - (z0 - zi0) * k), (ex, -d, zi0 - (z0 - zi0) * k),
             (ex, -d, zi1 + (zi1 - z1) * k), (-ex, -d, zi1 + (zi1 - z1) * k)]
    outer = [(-wt / 2, y_t, z0), (wt / 2, y_t, z0), (wt / 2, y_t, z1), (-wt / 2, y_t, z1)]
    block_ob = bpy.data.objects.get(block)
    cutters = [prism(kit, f"cut_{name}_splay", inner, outer, parent=root),
               kit.box(f"cut_{name}_throat", (wt, throat + 0.2, z1 - z0), (0, y_t + (throat + 0.2) / 2 - 0.04, (z0 + z1) / 2),
                       parent=root)]
    if block_ob is not None:
        for i, c in enumerate(cutters):
            mod = block_ob.modifiers.new(f"{name}_{i}", "BOOLEAN")
            mod.operation = "DIFFERENCE"
            mod.object = c
            c.hide_render = True
            c.display_type = "WIRE"
    # timber lintel over the inner opening, a stone slab on the sill, the mullion in the throat
    kit.box(f"{name}_lintel", (wi + 0.34, 0.2, 0.16), (0, 0.06, zi1 + 0.02), mat=wd, bevel=0.01, parent=root)
    kit.box(f"{name}_mullion", (0.12, throat * 0.9, z1 - z0), (0, y_t + throat * 0.5, (z0 + z1) / 2), mat=dressed(mats),
            bevel=0.01, parent=root)
    kit.box(f"{name}_transom", (wt, throat * 0.6, 0.07), (0, y_t + throat * 0.5, z0 + (z1 - z0) * 0.58), mat=dressed(mats),
            bevel=0.008, parent=root)
    # shutter leaves, hinged at the corners of the inner face
    h = zi1 - zi0 + 0.04
    zc = (zi0 + zi1) / 2
    for side, ang in ((1, leaves[0]), (-1, leaves[1])):
        a = math.radians(ang)
        hinge = (side * (wi / 2 + 0.02), -0.03)
        dx, dy = -side * math.cos(a), -math.sin(a)
        ln = wi / 2 - 0.01
        if ang < 0:      # folded into the reveal: the leaf lies along the splayed jamb and is as long as the jamb
            ln = math.hypot((wi - wt) / 2, y_t) - 0.03
            dx, dy = -side * (wi - wt) / 2 / math.hypot((wi - wt) / 2, y_t), y_t / math.hypot((wi - wt) / 2, y_t)
        cx, cy = hinge[0] + dx * ln / 2, hinge[1] + dy * ln / 2
        rz = math.degrees(math.atan2(dy, dx))
        leaf = kit.group(f"{name}_leaf_{side}", (cx, cy, zc), parent=root)
        leaf.rotation_euler = (0, 0, math.radians(rz))
        kit.box("boards", (ln, 0.04, h), (0, 0, 0), mat=wo, bevel=0.004, parent=leaf)
        if straps:
            for zz in (-h * 0.33, h * 0.33):
                kit.box("strap", (ln * 0.92, 0.012, 0.07), (-0.02, -0.026, zz), mat=iron, parent=leaf)
            kit.box("batten", (0.07, 0.014, h * 0.92), (ln * 0.3, 0.027, 0), mat=wd, parent=leaf)
    _lights.add(root, name, pos=(0.0, light_y if light_y is not None else T - 0.12, (z0 + z1) / 2 + 0.05), color=COOL,
                watts=light_watts, radius=0.25, specular=0.1)

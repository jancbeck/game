"""The wall above the ditch: rain streaks, damp, algae, ivy, spouts and a drain.

Helper of west_ditch.py. Two faces are dressed:

- the platform's west retaining wall, the plane x = -13.0 from the ground up to the cobble ledge at z = 0;
- the curtain wall's outer face, the plane x = -12.4 from the ledge to the parapet (7 m), and the same
  plane on the NW tower, 0.6 m behind the retaining wall.

Everything hangs 1 cm in front of its plane, so no wall needs to change. The stains are see-through films
made by one material with a ragged, streaked edge; the rest is geometry.
"""

import math

import bpy
from mathutils import Vector, noise

from mats.cobble_wet import _math, _mix, _node, _noise, _range, _xyz

from . import _ditch_field as F
from . import _ditch_ground as G
from . import _tube
from .grass_tuft import _blades

FACE_X = F.WALL_X - 0.012       # ribbons hang this far out of the wall
UPPER_X = -12.4 - 0.012         # the curtain wall's outer face above the ledge
CURTAIN_TOP = 7.0               # top of the parapet on the curtain wall
TOWER_TOP = 12.0                # and on the tower
STAIN = (0.034, 0.036, 0.034)  # the wall's own stone, damp: about two thirds of its dry value
STAIN_GREEN = (0.030, 0.038, 0.024)  # a thin green film of algae
STAIN_LIME = (0.080, 0.080, 0.075)  # pale lime washed out of the joints, in thin strands
STAIN_ALPHA = 0.62  # densest cover of a film: the stone grain always shows through


def _local(x, y, z):
    return Vector(F.to_local(x, y, z))


# ---------------------------------------------------------------- materials

def stain_material(damp=False, strength=1.0):
    """Water staining: a see-through film of damp, darker stone with algae and lime strands in it, whose
    edge is soft, ragged and streaked downward. With `damp`, the film is densest at the bottom and thins
    out upward: rising damp at the wall foot."""
    name = ("west_wall_damp" if damp else "west_wall_stain") + ("" if strength == 1.0 else f"_{strength:.2f}")
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    uv = _node(nt, "ShaderNodeTexCoord").outputs["UV"]
    u, v, _ = _xyz(nt, uv)                                  # u across the ribbon -1..1, v down it 0..1
    pos = _node(nt, "ShaderNodeTexCoord").outputs["Object"]
    px, py, pz = _xyz(nt, pos)
    # stretched noise: long thin streaks, since y is across the face and z down it
    streak = _node(nt, "ShaderNodeCombineXYZ", {"X": _math(nt, "MULTIPLY", py, 7.0),
                                                   "Y": _math(nt, "MULTIPLY", pz, 0.9)}).outputs[0]
    n = _noise(nt, streak, 1.0, 4.0, "2D", rough=0.6)
    if damp:
        across = _range(nt, _math(nt, "ABSOLUTE", u), 0.7, 1.0, 1.0, 0.0, smooth=True)
        up = _range(nt, v, 0.05, 0.85, 0.0, 1.0, smooth=True)
        body = _math(nt, "MULTIPLY", across, up)
    else:
        across = _range(nt, _math(nt, "ABSOLUTE", u), 0.05, 1.0, 1.0, 0.0, smooth=True)
        down = _range(nt, v, 0.25, 1.0, 1.0, 0.0, smooth=True)
        top = _range(nt, v, 0.0, 0.05, 0.0, 1.0)
        body = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", across, down), top)
    alpha = _range(nt, _math(nt, "MULTIPLY", body, _math(nt, "MULTIPLY_ADD", n, 1.2, 0.35)), 0.12, 0.75, 0.0, STAIN_ALPHA,
                   smooth=True)
    color = _mix(nt, _range(nt, _noise(nt, pos, 3.0, 3.0, "3D"), 0.4, 0.65, smooth=True), STAIN, STAIN_GREEN)
    fine = _node(nt, "ShaderNodeCombineXYZ", {"X": _math(nt, "MULTIPLY", py, 26.0),
                                                 "Y": _math(nt, "MULTIPLY", pz, 1.4)}).outputs[0]
    color = _mix(nt, _range(nt, _noise(nt, fine, 1.0, 2.0, "2D"), 0.60, 0.72, 0.0, 0.7, smooth=True), color, STAIN_LIME)
    nt.links.new(color, bsdf.inputs["Base Color"])
    nt.links.new(_math(nt, "MULTIPLY", alpha, strength), bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.85          # dull: a glossy film would mirror the bright sky and
    bsdf.inputs["Specular IOR Level"].default_value = 0.1  # come out paler than the dry stone around it
    return mat


def void_material():
    mat = bpy.data.materials.get("west_drain_void")
    if mat is None:
        mat = bpy.data.materials.new("west_drain_void")
        mat.use_nodes = True
        b = mat.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.002, 0.002, 0.003, 1.0)
        b.inputs["Roughness"].default_value = 0.9
        b.inputs["Specular IOR Level"].default_value = 0.0
    return mat


# ---------------------------------------------------------------- ribbons on the face

def _ribbon(kit, root, name, strips, mat, uvs=True, x=None):
    """strips: list of (y_center, half_width_top, half_width_bottom, z_top, z_bottom). One quad grid each,
    with UVs: u -1..1 across, v 0..1 down."""
    verts, faces, uv = [], [], []
    for (yc, wt, wb, zt, zb) in strips:
        rows = max(2, int(abs(zt - zb) / 0.12))
        cols = 6
        base = len(verts)
        for r in range(rows + 1):
            t = r / rows
            hw = wt + (wb - wt) * t
            z = zt + (zb - zt) * t
            for c in range(cols + 1):
                s = -1.0 + 2.0 * c / cols
                verts.append(F.to_local(FACE_X if x is None else x, yc + s * hw, z))
                uv.append((s, t))
        for r in range(rows):
            for c in range(cols):
                a = base + r * (cols + 1) + c
                faces.append((a, a + 1, a + cols + 2, a + cols + 1))
    ob = kit.mesh(name, verts, faces, mat=mat, parent=root)
    if uvs:
        layer = ob.data.uv_layers.new(name="UVMap")
        for loop in ob.data.loops:
            layer.data[loop.index].uv = uv[loop.vertex_index]
    return ob


def streaks(kit, rng, root):
    """Dark water streaks from the ledge lip toward the ground, many short, a few the full height."""
    strips = []
    y = -13.0
    while y < 9.0:
        y += rng.uniform(0.35, 1.5)
        top = 0.0 + rng.uniform(-0.02, 0.1)
        ground = F.ground(F.WALL_X - 0.05, y)
        reach = rng.choice((0.9, 1.4, 2.0, 2.7, 3.3)) * rng.uniform(0.8, 1.1)
        strips.append((y, rng.uniform(0.08, 0.28), rng.uniform(0.12, 0.45), top, max(top - reach, ground - 0.1)))
    # under the drain: a broad stain
    strips.append((F.DRAIN_Y, 0.16, 0.5, F.DRAIN_Z + 0.35, F.ground(F.WALL_X - 0.05, F.DRAIN_Y) - 0.1))
    strips.append((F.DRAIN_Y + 0.05, 0.08, 0.2, F.DRAIN_Z + 0.9, F.DRAIN_Z - 0.2))
    _ribbon(kit, root, "face_streaks", strips, stain_material())


def damp(kit, rng, root):
    """Rising damp: a dark, wet band along the foot of the face, ragged and uneven in height."""
    strips = []
    y = -13.4
    while y < 9.2:
        seg = rng.uniform(1.2, 2.6)
        height = rng.uniform(0.45, 1.25)
        yc = y + seg / 2
        ground = F.ground(F.WALL_X - 0.05, yc)
        strips.append((yc, seg / 2 * 1.15, seg / 2 * 1.15, ground + height, ground - 0.1))
        y += seg * rng.uniform(0.7, 1.0)
    _ribbon(kit, root, "face_damp", strips, stain_material(damp=True))


def algae(kit, mats, rng, root):
    """Green-black algae and moss on the stone at the foot: patches with ragged tops."""
    verts, faces = [], []
    y = -13.2
    while y < 9.0:
        width = rng.uniform(0.5, 2.2)
        y1 = min(9.0, y + width)
        height = rng.uniform(0.18, 0.7)
        cols = max(3, int(width / 0.08))
        base = len(verts)
        off = rng.uniform(0, 50)
        for c in range(cols + 1):
            t = c / cols
            yy = y + (y1 - y) * t
            g = F.ground(F.WALL_X - 0.05, yy)
            h = height * math.sin(math.pi * t) ** 0.6 * (0.55 + 0.45 * noise.noise(Vector((yy * 4.0, off, 0.0))))
            verts.append(F.to_local(FACE_X, yy, g - 0.05))
            verts.append(F.to_local(FACE_X, yy, g + max(0.03, h)))
        for c in range(cols):
            a = base + c * 2
            faces.append((a, a + 2, a + 3, a + 1))
        y = y1 + rng.uniform(0.2, 1.6)
    ob = kit.mesh("face_algae", verts, faces, mat=mats["moss"], parent=root)
    for p in ob.data.polygons:
        p.use_smooth = True


# ---------------------------------------------------------------- ivy and weeds

def ivy(kit, mats, rng, root):
    """Strands of ivy hanging from the ledge over the face, with dead and living leaves."""
    stems, green, dead = _tube.Mesh(), _tube.Mesh(), _tube.Mesh()
    for i in range(34):
        y = rng.uniform(-12.8, 8.8)
        x = FACE_X - 0.015
        z = 0.02
        length = rng.uniform(0.6, 2.4)
        n = int(length / 0.07)
        pts, sway = [], rng.uniform(0, 6.28)
        for k in range(n + 1):
            t = k / n
            pts.append(_local(x - 0.01 - 0.02 * math.sin(k * 0.7), y + 0.07 * math.sin(sway + k * 0.45), z - length * t))
        stems.tube(pts, [0.006 * (1 - 0.6 * k / n) + 0.0015 for k in range(n + 1)], 3)
        for k in range(1, n + 1):
            if rng.random() < 0.8:
                p = pts[k]
                side = rng.choice((-1, 1))
                sz = rng.uniform(0.035, 0.07)
                a = rng.uniform(-0.6, 0.6)
                tgt = green if rng.random() < 0.7 else dead
                b = len(tgt.verts)
                e1 = Vector((-0.4, side * math.cos(a), -0.35 * math.sin(a) - 0.3)) * sz
                e2 = Vector((0.0, side * 0.5, 0.0)) * sz
                tgt.verts += [tuple(p), tuple(p + e1 * 0.55 + e2), tuple(p + e1 * 1.3), tuple(p + e1 * 0.55 - e2)]
                tgt.faces.append((b, b + 1, b + 2, b + 3))
    stems.to_object("ivy_stems", mats["wood_dark"], root)
    green.to_object("ivy_leaves", mats["moss"], root)
    dead.to_object("ivy_leaves_dead", mats["burlap"], root)


def ledge_weeds(kit, mats, rng, root):
    """Dead grass and weeds rooted in the silt on the ledge, bowed over its edge."""
    straw, green = _tube.Mesh(), _tube.Mesh()
    for i in range(46):
        y = rng.uniform(-12.8, 8.8)
        tmp = _tube.Mesh()
        _blades(tmp, rng, rng.randint(16, 34), rng.uniform(0.25, 0.55), rng.uniform(20, 45))
        tgt = straw if rng.random() < 0.35 else green
        tgt.append(tmp, offset=tuple(_local(F.WALL_X + rng.uniform(0.05, 0.3), y, 0.01)))
    straw.to_object("ledge_weeds", mats["burlap"], root)
    green.to_object("ledge_weeds_green", mats["moss"], root)


# ---------------------------------------------------------------- the drain

def spout(kit, mats, rng, root):
    """A stone spout through the retaining wall: a lintel, a sill with a drip lip, jambs and a dark mouth,
    with the thread of water that falls from the lip to the basin at the wall foot."""
    y, z = F.DRAIN_Y, F.DRAIN_Z
    stone = mats["stone_wall"]
    wx = F.WALL_X
    kit.box("spout_sill", (0.66, 0.42, 0.14), tuple(_local(wx - 0.20, y, z - 0.165)), (0, 4, 0), stone, bevel=0.015,
            parent=root)
    kit.box("spout_lintel", (0.5, 0.42, 0.14), tuple(_local(wx - 0.14, y, z + 0.17)), (0, 0, 0), stone, bevel=0.015,
            parent=root)
    for s in (-1, 1):
        kit.box(f"spout_jamb_{s}", (0.5, 0.10, 0.22), tuple(_local(wx - 0.14, y + s * 0.16, z)), (0, 0, 0), stone,
                bevel=0.012, parent=root)
    kit.box("spout_mouth", (0.03, 0.23, 0.21), tuple(_local(wx - 0.005, y, z)), mat=void_material(), parent=root)
    # the thread of water: short thin threads from the lip down to the basin, with gaps where it breaks into drops
    lip_x = wx - 0.52
    ground = F.ground(lip_x, y)
    top = z - 0.19
    mesh = _tube.Mesh()
    zc = top
    while zc > ground + 0.05:
        seg = rng.uniform(0.12, 0.3)
        z1 = max(ground + 0.03, zc - seg)
        n = 3
        pts = [_local(lip_x - 0.02 * (zc - z) ** 2 + 0.006 * math.sin(k * 2.0 + zc * 9), y + 0.006 * math.sin(k * 1.4),
                      zc + (z1 - zc) * k / n) for k in range(n + 1)]
        mesh.tube(pts, [0.007, 0.0085, 0.0075, 0.007], 4)
        zc = z1 - rng.uniform(0.06, 0.14)
    me = mesh.to_object("spout_trickle", G.water_material(), root)
    G._vertex_attribute(me, "shore", [0.9] * len(mesh.verts))
    me.visible_shadow = False


# ---------------------------------------------------------------- the curtain wall's outer face above the ledge

def _crenel_gaps(cy, length, top):
    """(y, top z) of every gap between merlons along a wall edge, where rain runs off the wall-walk."""
    step = 0.75 + 0.55
    n = max(1, int((length + 0.55) // step))
    start = -(n - 1) * step / 2
    return [(cy + start + i * step + step / 2, top) for i in range(n - 1)]


def upper_streaks(kit, rng, root):
    """Dark rain streaks down the 7 m face: one from most crenel gaps, some from the mortar, and broad pale
    washes of staining between them."""
    strips, washes = [], []
    gaps = _crenel_gaps(-4.95, 15.9, CURTAIN_TOP) + _crenel_gaps(5.5, 5.0, TOWER_TOP)
    for y, top in gaps:
        if rng.random() < 0.8:
            reach = rng.choice((2.5, 3.5, 4.5, 6.0, 7.0)) * rng.uniform(0.8, 1.1)
            strips.append((y + rng.uniform(-0.15, 0.15), rng.uniform(0.16, 0.3), rng.uniform(0.35, 0.8), top,
                           max(top - reach, 0.05)))
        if rng.random() < 0.7:
            washes.append((y + rng.uniform(-0.3, 0.3), rng.uniform(0.35, 0.7), rng.uniform(0.8, 1.5), top,
                           max(top - rng.uniform(3.0, 7.0), 0.05)))
    for i in range(16):
        y = rng.uniform(-12.6, 7.8)
        top = (TOWER_TOP if y > 3.0 else CURTAIN_TOP) - rng.uniform(0.3, 3.5)
        strips.append((y, rng.uniform(0.08, 0.2), rng.uniform(0.15, 0.4), top, max(top - rng.uniform(1.0, 3.5), 0.05)))
    _ribbon(kit, root, "wall_streaks", strips, stain_material(), x=UPPER_X)
    _ribbon(kit, root, "wall_washes", washes, stain_material(strength=0.4), x=UPPER_X)


def upper_damp(kit, rng, root):
    """Wet, dark stone and green growth where the ledge's mud splashes the base of the wall."""
    strips = []
    y = -12.8
    while y < 7.9:
        seg = rng.uniform(1.0, 2.4)
        height = rng.uniform(0.35, 1.0)
        strips.append((y + seg / 2, seg / 2 * 1.15, seg / 2 * 1.15, height, -0.05))
        y += seg * rng.uniform(0.7, 1.0)
    _ribbon(kit, root, "wall_damp", strips, stain_material(damp=True), x=UPPER_X)


def upper_ivy(kit, mats, rng, root):
    """Ivy climbing the face from the ledge: a few long strands that branch, thick with dark leaves."""
    stems, green, dead = _tube.Mesh(), _tube.Mesh(), _tube.Mesh()

    def strand(y0, z0, height, depth):
        n = max(4, int(height / 0.09))
        pts, sway = [], rng.uniform(0, 6.28)
        y = y0
        for k in range(n + 1):
            y += 0.035 * math.sin(sway + k * 0.4) + rng.uniform(-0.012, 0.012)
            pts.append(_local(UPPER_X - 0.012 - 0.02 * (k % 2), y, z0 + height * k / n))
        stems.tube(pts, [0.008 * (1 - 0.7 * k / n) + 0.002 for k in range(n + 1)], 3)
        for k in range(1, n + 1):
            for side in (-1, 1):
                if rng.random() < 0.85:
                    p = pts[k]
                    sz = rng.uniform(0.04, 0.085)
                    a = rng.uniform(-0.7, 0.7)
                    tgt = green if rng.random() < 0.75 else dead
                    b = len(tgt.verts)
                    e1 = Vector((-0.35, side * math.cos(a), 0.4 * math.sin(a) + 0.15)) * sz
                    e2 = Vector((0.0, 0.0, 0.5)) * sz
                    tgt.verts += [tuple(p), tuple(p + e1 * 0.55 + e2), tuple(p + e1 * 1.3), tuple(p + e1 * 0.55 - e2)]
                    tgt.faces.append((b, b + 1, b + 2, b + 3))
                if depth < 1 and k > 3 and rng.random() < 0.08:
                    strand(pts[k].y + F.ORIGIN[1] + side * 0.05, z0 + height * k / n, height * rng.uniform(0.25, 0.5),
                           depth + 1)

    for i in range(14):
        strand(rng.uniform(-12.4, 7.6), 0.0, rng.uniform(1.5, 5.0), 0)
    stems.to_object("wall_ivy_stems", mats["wood_dark"], root)
    green.to_object("wall_ivy_leaves", mats["moss"], root)
    dead.to_object("wall_ivy_dead", mats["burlap"], root)


def wall_spouts(kit, mats, rng, root):
    """Stone water spouts at the foot of the parapet that shed the wall-walk's rain, each with a broad stain below."""
    stone = mats["stone_wall"]
    strips = []
    for y in (-10.1, -6.3, -2.0, 1.4):
        z = 6.15
        x = F.WALL_X + 0.6      # curtain face
        kit.box(f"wall_spout_{y}", (0.55, 0.26, 0.2), tuple(_local(x - 0.2, y, z)), (0, 3, 0), stone, bevel=0.02, parent=root)
        kit.box(f"wall_spout_mouth_{y}", (0.04, 0.12, 0.09), tuple(_local(x - 0.47, y, z + 0.02)), mat=void_material(),
                parent=root)
        strips.append((y, 0.14, 0.55, z - 0.1, rng.uniform(1.8, 3.0)))
        strips.append((y + 0.05, 0.07, 0.2, z - 0.1, rng.uniform(3.5, 5.5)))
    _ribbon(kit, root, "spout_stains", strips, stain_material(), x=UPPER_X)


def ledge_cover(kit, root):
    """Silt and wet mud lying on the ledge's cobbles: thin, patchy, ragged at its lip."""
    xs = [F.WALL_X + i * 0.06 for i in range(0, 12)]
    y0, y1, step = -13.3, 9.0, 0.1
    ny = int(round((y1 - y0) / step))
    verts, wet = [], []
    for j in range(ny + 1):
        y = y0 + j * step
        for x in xs:
            n = noise.noise(Vector((x * 2.0, y * 1.6, 3.0)))
            verts.append((x, y, 0.012 + 0.05 * max(0.0, n + 0.3)))
            wet.append(min(1.0, 0.75 + 0.3 * noise.noise(Vector((x * 5.0, y * 5.0, 8.0)))))
    nx = len(xs)
    faces = []
    for j in range(ny):
        for i in range(nx - 1):
            a = j * nx + i
            lip = noise.noise(Vector(((y0 + j * step) * 1.4, 0.0, 11.0)))
            if i == 0 and lip < -0.1:
                continue                                           # the silt has not reached the lip here
            if noise.noise(Vector((xs[i] * 3.0, (y0 + j * step) * 2.2, 5.0))) < -0.38:
                continue                                           # bare cobbles show through
            faces.append((a, a + 1, a + nx + 1, a + nx))
    ob = G._world_object(kit, "ledge_silt", verts, faces, G.wet_mud_material(), root)
    G._vertex_attribute(ob, "wet", wet)
    ob.visible_shadow = False

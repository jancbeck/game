"""Geometry helpers for procedural props.

Every helper builds mesh data at real size (object scale stays 1), so bevel
modifiers and object-space textures behave the same on every part.
Rotations are Euler XYZ in degrees. Pass `parent` to hang a part under a
prop's root empty; build props around the origin with the root at identity.
"""

import math

import bmesh
import bpy
from mathutils import Euler, Vector


def _link(ob):
    bpy.context.collection.objects.link(ob)
    return ob


def _finish(name, bm, loc, rot_deg, mat, parent, bevel):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = _link(bpy.data.objects.new(name, me))
    ob.location = loc
    ob.rotation_euler = Euler([math.radians(a) for a in rot_deg])
    if mat is not None:
        me.materials.append(mat)
    if parent is not None:
        ob.parent = parent
    if bevel:
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 1
        mod.limit_method = "ANGLE"
    for p in me.polygons:
        p.use_smooth = False
    return ob


def group(name, loc=(0, 0, 0), parent=None):
    """Empty used as a prop root or sub-assembly pivot."""
    ob = _link(bpy.data.objects.new(name, None))
    ob.empty_display_size = 0.3
    ob.location = loc
    if parent is not None:
        ob.parent = parent
    return ob


def box(name, size, loc=(0, 0, 0), rot_deg=(0, 0, 0), mat=None, bevel=0.0, parent=None):
    """Box of `size` (x, y, z) meters, centered on `loc`."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    return _finish(name, bm, loc, rot_deg, mat, parent, bevel)


def cylinder(name, radius, depth, loc=(0, 0, 0), rot_deg=(0, 0, 0), mat=None, segments=16,
             radius_top=None, bevel=0.0, parent=None):
    """Cylinder (or cone/frustum with `radius_top`) along local Z, centered on `loc`."""
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=segments,
        radius1=radius, radius2=radius if radius_top is None else radius_top, depth=depth,
    )
    return _finish(name, bm, loc, rot_deg, mat, parent, bevel)


def sphere(name, radius, loc=(0, 0, 0), scale=(1, 1, 1), rot_deg=(0, 0, 0), mat=None,
           segments=12, parent=None):
    """UV sphere; `scale` squashes it into an ellipsoid in mesh data."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=max(6, segments // 2), radius=radius)
    for v in bm.verts:
        v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
    return _finish(name, bm, loc, rot_deg, mat, parent, 0.0)


def torus(name, major, minor, loc=(0, 0, 0), rot_deg=(0, 0, 0), mat=None,
          major_segments=24, minor_segments=6, parent=None):
    """Ring in the local XY plane: barrel hoops, wheel rims, rope coils."""
    bm = bmesh.new()
    verts = []
    for i in range(major_segments):
        a = 2 * math.pi * i / major_segments
        ring = []
        for j in range(minor_segments):
            b = 2 * math.pi * j / minor_segments
            r = major + minor * math.cos(b)
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), minor * math.sin(b))))
        verts.append(ring)
    for i in range(major_segments):
        for j in range(minor_segments):
            a, b = verts[i], verts[(i + 1) % major_segments]
            bm.faces.new((a[j], b[j], b[(j + 1) % minor_segments], a[(j + 1) % minor_segments]))
    return _finish(name, bm, loc, rot_deg, mat, parent, 0.0)


def beam(name, p0, p1, section=(0.15, 0.15), mat=None, bevel=0.0, roll_deg=0.0, parent=None):
    """Square-section timber from point p0 to point p1 (posts, braces, rails)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    length = d.length
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * section[0], v.co.y * section[1], v.co.z * length))
    ob = _finish(name, bm, (p0 + p1) / 2, (0, 0, 0), mat, parent, bevel)
    q = d.to_track_quat("Z", "Y")
    if roll_deg:
        from mathutils import Quaternion
        q = q @ Quaternion((0, 0, 1), math.radians(roll_deg))
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = q
    return ob


def mesh(name, verts, faces, loc=(0, 0, 0), rot_deg=(0, 0, 0), mat=None, parent=None, bevel=0.0):
    """Arbitrary mesh from vertex and face lists."""
    bm = bmesh.new()
    bv = [bm.verts.new(v) for v in verts]
    for f in faces:
        bm.faces.new([bv[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish(name, bm, loc, rot_deg, mat, parent, bevel)


def solidify(ob, thickness):
    """Give a flat mesh (cloth, sheet metal) thickness."""
    mod = ob.modifiers.new("solidify", "SOLIDIFY")
    mod.thickness = thickness
    return ob


def jitter(rng, amount):
    """Uniform random offset in [-amount, amount]; use for weathered, uneven placement."""
    return rng.uniform(-amount, amount)

"""Mesh gathering for the stable and the forge: many small boxes and domes merged into one object.

A shingle roof has hundreds of pieces, so one object per piece would be slow to build and to
render. `Mesh` collects boxes in prop space (optionally through a `frame` matrix, for pieces laid
on a sloped plane) and `finish` makes one object whose origin is its bounding-box center.

A merged object has one Object Info random value and one bounding box, so `finish` also writes two
face attributes per piece (each connected island of the mesh) that the wood shader reads
(scene/mats/_wood.py): `piece`, a random 0..1 that gives every board its own tone and texture
offset, and `piece_size`, the piece's own bounding-box size, which turns the grain along it.

Not a prop module: the leading underscore keeps it out of assets.available().
"""

import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

_DEG = 0.017453292519943295


def frame(origin, u, v, n):
    """Matrix that maps a plane space (u, v, n axes) to prop space with `origin` as its zero."""
    m = Matrix((u, v, n)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def piece_attributes(bm, name):
    """Per-face (random, size) of the connected island each face belongs to, in face order."""
    bm.verts.index_update()
    parent = list(range(len(bm.verts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for e in bm.edges:
        a, b = find(e.verts[0].index), find(e.verts[1].index)
        if a != b:
            parent[a] = b
    lo, hi = {}, {}
    for v in bm.verts:
        r = find(v.index)
        if r in lo:
            lo[r] = Vector(map(min, lo[r], v.co))
            hi[r] = Vector(map(max, hi[r], v.co))
        else:
            lo[r], hi[r] = v.co.copy(), v.co.copy()
    rng = random.Random(name)
    value = {r: rng.random() for r in sorted(lo)}
    roots = [find(f.verts[0].index) for f in bm.faces]
    return [value[r] for r in roots], [tuple(hi[r] - lo[r]) for r in roots]


def write_pieces(me, pieces):
    """Store the output of `piece_attributes` on the mesh as face attributes."""
    values, sizes = pieces
    if not values:
        return
    me.attributes.new("piece", "FLOAT", "FACE").data.foreach_set("value", values)
    me.attributes.new("piece_size", "FLOAT_VECTOR", "FACE").data.foreach_set(
        "vector", [c for s in sizes for c in s])


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def box(self, size, loc, rot_deg=(0, 0, 0), xform=None):
        geom = bmesh.ops.create_cube(self.bm, size=1.0)
        m = (Matrix.Translation(loc) @ Euler([a * _DEG for a in rot_deg]).to_matrix().to_4x4()
             @ Matrix.Diagonal((size[0], size[1], size[2], 1.0)))
        if xform is not None:
            m = xform @ m
        bmesh.ops.transform(self.bm, matrix=m, verts=geom["verts"])

    def dome(self, loc, radii, rng, jitter=0.25, xform=None):
        """Lumpy half-ellipsoid resting on `loc`: moss cushions."""
        geom = bmesh.ops.create_icosphere(self.bm, subdivisions=2, radius=1.0)
        verts = geom["verts"]
        for v in verts:
            k = 1.0 + rng.uniform(-jitter, jitter)
            v.co = Vector((v.co.x * radii[0] * k, v.co.y * radii[1] * k, v.co.z * radii[2] * k)) + Vector(loc)
        low = [v for v in verts if v.co.z < loc[2] - 0.15 * radii[2]]
        bmesh.ops.delete(self.bm, geom=low, context="VERTS")
        if xform is not None:
            bmesh.ops.transform(self.bm, matrix=xform, verts=[v for v in verts if v.is_valid])

    def finish(self, name, mat, parent, bevel=0.0, smooth=False):
        bm = self.bm
        if not bm.verts:
            bm.free()
            return None
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        lo = Vector((min(v.co.x for v in bm.verts), min(v.co.y for v in bm.verts),
                     min(v.co.z for v in bm.verts)))
        hi = Vector((max(v.co.x for v in bm.verts), max(v.co.y for v in bm.verts),
                     max(v.co.z for v in bm.verts)))
        c = (lo + hi) / 2
        bmesh.ops.translate(bm, vec=-c, verts=bm.verts)
        pieces = piece_attributes(bm, name)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        write_pieces(me, pieces)
        ob = bpy.data.objects.new(name, me)
        bpy.context.collection.objects.link(ob)
        ob.location = c
        if mat is not None:
            me.materials.append(mat)
        ob.parent = parent
        for p in me.polygons:
            p.use_smooth = smooth
        if bevel:
            mod = ob.modifiers.new("bevel", "BEVEL")
            mod.width = bevel
            mod.segments = 1
            mod.limit_method = "ANGLE"
        return ob

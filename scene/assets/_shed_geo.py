"""Mesh gathering for the cookhouse: many wedges, boards and domes merged into a few objects.

A shingle roof has hundreds of pieces; one object per piece would be slow to build and to
render. `Mesh` collects pieces in shed space and `finish` turns them into one object whose
origin is its bounding-box center. Like _se_mesh.Mesh, it writes the per-piece `piece` and
`piece_size` face attributes that the wood shader reads.
"""

import math

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

from ._se_mesh import piece_attributes, write_pieces


def rect(x0, x1, y0, y1, z):
    """Horizontal rectangle at height z as a cyclic quad, counter-clockwise seen from above."""
    return [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def prism(self, a, b):
        """Solid between two cyclic quads `a` and `b` (4 points each, same winding)."""
        va = [self.bm.verts.new(p) for p in a]
        vb = [self.bm.verts.new(p) for p in b]
        for f in ((vb[0], vb[1], vb[2], vb[3]), (va[0], va[3], va[2], va[1]),
                  (va[0], va[1], vb[1], vb[0]), (va[1], va[2], vb[2], vb[1]),
                  (va[2], va[3], vb[3], vb[2]), (va[3], va[0], vb[0], vb[3])):
            self.bm.faces.new(f)

    def loft(self, sections):
        """Chain of prisms through consecutive cross-sections (quads)."""
        for a, b in zip(sections, sections[1:]):
            self.prism(a, b)

    def box(self, size, loc, rot_deg=(0, 0, 0)):
        geom = bmesh.ops.create_cube(self.bm, size=1.0)
        m = (Matrix.Translation(loc) @ Euler([x * 0.017453292519943295 for x in rot_deg]).to_matrix().to_4x4()
             @ Matrix.Diagonal((size[0], size[1], size[2], 1.0)))
        bmesh.ops.transform(self.bm, matrix=m, verts=geom["verts"])

    def cyl(self, p0, p1, r0, r1=None, sides=8, twist=0.0):
        """Prism with a regular polygon section from p0 to p1; the radius runs from r0 to r1."""
        a, b = Vector(p0), Vector(p1)
        d = b - a
        if d.length < 1e-6:
            return
        d.normalize()
        ref = Vector((1, 0, 0)) if abs(d.x) < 0.9 else Vector((0, 1, 0))
        u = d.cross(ref).normalized()
        v = d.cross(u)
        r1 = r0 if r1 is None else r1
        rings = []
        for p, r in ((a, r0), (b, r1)):
            rings.append([self.bm.verts.new(p + (u * math.cos(2 * math.pi * i / sides + twist)
                                                 + v * math.sin(2 * math.pi * i / sides + twist)) * r)
                          for i in range(sides)])
        for i in range(sides):
            j = (i + 1) % sides
            self.bm.faces.new((rings[0][i], rings[0][j], rings[1][j], rings[1][i]))
        self.bm.faces.new(rings[0][::-1])
        self.bm.faces.new(rings[1])

    def ellipsoid(self, loc, radii, rot_deg=(0, 0, 0), segments=10):
        """Closed ellipsoid: hams, onions, loaves."""
        geom = bmesh.ops.create_uvsphere(self.bm, u_segments=segments, v_segments=max(5, segments // 2), radius=1.0)
        m = (Matrix.Translation(loc) @ Euler([x * 0.017453292519943295 for x in rot_deg]).to_matrix().to_4x4()
             @ Matrix.Diagonal((radii[0], radii[1], radii[2], 1.0)))
        bmesh.ops.transform(self.bm, matrix=m, verts=geom["verts"])

    def dome(self, loc, radii, rng, jitter=0.25):
        """Lumpy half-ellipsoid resting on `loc`: moss cushions."""
        geom = bmesh.ops.create_icosphere(self.bm, subdivisions=2, radius=1.0)
        verts = geom["verts"]
        for v in verts:
            k = 1.0 + rng.uniform(-jitter, jitter)
            v.co = Vector((v.co.x * radii[0] * k, v.co.y * radii[1] * k, v.co.z * radii[2] * k)) + Vector(loc)
        low = [v for v in verts if v.co.z < loc[2] - 0.15 * radii[2]]
        bmesh.ops.delete(self.bm, geom=low, context="VERTS")

    def finish(self, name, mat, parent, bevel=0.0, smooth=False):
        bm = self.bm
        if not bm.verts:
            bm.free()
            return None
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        lo = Vector((min(v.co.x for v in bm.verts), min(v.co.y for v in bm.verts), min(v.co.z for v in bm.verts)))
        hi = Vector((max(v.co.x for v in bm.verts), max(v.co.y for v in bm.verts), max(v.co.z for v in bm.verts)))
        c = (lo + hi) / 2
        bmesh.ops.translate(bm, vec=-c, verts=bm.verts)
        pieces = piece_attributes(bm, name)  # per-board tone and grain for the wood shader
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

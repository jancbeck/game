"""What the game's figure shader reads from the mesh besides the vertex colour: a second UV map 'ao'.

    UV2.x   baked ambient occlusion in the idle pose: 0 open, 1 closed (creases under the chin, between
            the arm and the body, inside a skirt). On hair it is instead the distance to the ragged edge,
            1 at the edge, which the shader breaks up with noise so the hair is not a solid cap.
    UV2.y   which cloth the vertex is: 0 wool, 0.33 leather, 0.66 linen, 1 hair (garments.tag kinds). A mesh
            without the map reads as wool. (The glTF exporter flips v, so the map holds 1 - kind.)

game/shaders/figure.gdshader reads both. Runs inside Blender (build_human.py).
"""

import math
import random

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import posefit

# garments.tag kind -> cloth code
KIND_CODE = {
    "leather": 0.33, "boots": 0.33, "belt": 0.33, "coif": 0.33,
    "linen": 0.66, "apron": 0.66,
    "hair": 1.0,
}
EDGE_REACH_M = 0.03


def srgb_encode(c):
    """Linear to sRGB, per channel: the game stores the colour of a vertex in 8 bits, and linear values
    would band in dark wool."""
    out = []
    for x in c:
        x = max(0.0, min(1.0, x))
        out.append(12.92 * x if x <= 0.0031308 else 1.055 * x ** (1.0 / 2.4) - 0.055)
    return tuple(out)


def set_attribute(obj, name, value):
    attr = obj.data.attributes.get(name) or obj.data.attributes.new(name, "FLOAT", "POINT")
    attr.data.foreach_set("value", [value] * len(obj.data.vertices))


def hair_edge(obj):
    """Attribute 'edge' on a hair mesh: 1 on its boundary, falling to 0 over EDGE_REACH_M along the surface."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    dist = {v.index: (0.0 if any(e.is_boundary for e in v.link_edges) else 9.0) for v in bm.verts}
    todo = [v for v in bm.verts if dist[v.index] == 0.0]
    while todo:
        v = todo.pop()
        for e in v.link_edges:
            w = e.other_vert(v)
            d = dist[v.index] + e.calc_length()
            if d < dist[w.index] and d < EDGE_REACH_M:
                dist[w.index] = d
                todo.append(w)
    bm.free()
    attr = obj.data.attributes.new("edge", "FLOAT", "POINT")
    attr.data.foreach_set("value", [max(0.0, 1.0 - dist[i] / EDGE_REACH_M) for i in range(len(obj.data.vertices))])


def bake_occlusion(mesh, rig, action, frame=1, rays=28, reach=0.26, seed=11):
    """Per-vertex ambient occlusion of the joined mesh in a pose (the idle clip's first frame, so the arm
    already lies against the body). Returns a list, one 0..1 value per vertex."""
    posefit.set_pose(rig, action, frame)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    verts = [v.co.copy() for v in me.vertices]
    normals = [v.normal.copy() for v in me.vertices]
    tris = [tuple(t.vertices) for t in me.loop_triangles]
    tree = BVHTree.FromPolygons(verts, tris)
    ev.to_mesh_clear()
    rng = random.Random(seed)
    occl = []
    for co, n in zip(verts, normals):
        if n.length < 1e-6:
            occl.append(0.0)
            continue
        n = n.normalized()
        t1 = n.cross(Vector((0.0, 0.0, 1.0)) if abs(n.z) < 0.9 else Vector((1.0, 0.0, 0.0))).normalized()
        t2 = n.cross(t1)
        total = 0.0
        for _ in range(rays):
            # cosine-weighted direction in the hemisphere
            u, v = rng.random(), rng.random()
            r, a = math.sqrt(u), 2.0 * math.pi * v
            d = (t1 * (r * math.cos(a)) + t2 * (r * math.sin(a)) + n * math.sqrt(max(0.0, 1.0 - u))).normalized()
            hit = tree.ray_cast(co + n * 0.004, d, reach)
            if hit is not None and hit[0] is not None:
                total += 1.0 - hit[3] / reach
        occl.append(total / rays)
    return occl


def smooth_values(mesh_data, values, iterations=2, factor=0.5):
    nb = [[] for _ in values]
    for e in mesh_data.edges:
        a, b = e.vertices
        nb[a].append(b)
        nb[b].append(a)
    for _ in range(iterations):
        values = [v * (1.0 - factor) + factor * (sum(values[j] for j in nb[i]) / len(nb[i]) if nb[i] else v)
                  for i, v in enumerate(values)]
    return values


def write_uv2(mesh, occlusion, strength=1.35):
    """The 'ao' UV map: (occlusion or hair edge, cloth kind) per loop, from the vertex attributes 'kind' and
    'edge' that build_human.py set on the parts before the join."""
    data = mesh.data
    kind = [d.value for d in data.attributes["kind"].data]
    edge = [d.value for d in data.attributes["edge"].data] if "edge" in data.attributes else [0.0] * len(kind)
    smooth_occ = smooth_values(data, occlusion)
    layer = data.uv_layers.get("ao") or data.uv_layers.new(name="ao")
    for loop in data.loops:
        i = loop.vertex_index
        x = edge[i] if kind[i] > 0.9 else min(1.0, smooth_occ[i] * strength)
        layer.data[loop.index].uv = (x, 1.0 - kind[i])      # the glTF exporter flips v

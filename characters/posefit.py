"""Free cloth that follows the pose it is in: shape keys for a skirt, a cloak hem or a doublet's skirts.

A garment's loft is skinned to the pelvis and the thighs, so it moves like a rigid cone. A walking leg then
comes through it, and a lying or sitting body leaves it standing like a tent. For each pose that matters
this module evaluates the rig, moves the cloth vertices (attribute 'fit', garments.mark_fit) to where cloth
would be, and stores the move as a shape key on the joined mesh. The game switches the keys on with the
clips (game/scripts/player.gd reads `fit` in <id>.json):

  clear   push the cloth out of the body, then smooth: a walking skirt. One key per sampled frame of the
          clip, blended by the clip's phase.
  drape   let the cloth fall onto what is under it (the body, the floor or a seat), then push it out of the
          body and smooth: a cloak on a sleeper, a skirt over a sitter's thighs. One key for the clip.

A shape key is a move in rest space, the space of the vertex before skinning, so a world move d of a
vertex whose skinning matrix is A (the weighted sum of its bones' matrices) is stored as A^-1 d.

Runs inside Blender after the clips exist (build_human.py). The bare body, posed by the same rig, is the
collider.
"""

import math

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

CLEARANCE_M = 0.012          # cloth sits this far off the skin
SMOOTH_ITERATIONS = 4


def log(*a):
    print("[posefit]", *a, flush=True)


# ---------------------------------------------------------------- pose evaluation

def set_pose(rig, action, frame):
    rig.animation_data.action = action
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def evaluated_points(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    pts = [ev.matrix_world @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    return pts


def body_tree(ground):
    dg = bpy.context.evaluated_depsgraph_get()
    return BVHTree.FromObject(ground, dg)


def bone_matrices(rig):
    """{bone name: 3x3 skinning matrix at the current pose}: pose matrix times the inverse rest matrix."""
    out = {}
    for pb in rig.pose.bones:
        m = pb.matrix @ pb.bone.matrix_local.inverted()
        out[pb.name] = m.to_3x3()
    return out


def skinning_matrix(mesh, vertex, bones):
    names = {g.index: g.name for g in mesh.vertex_groups}
    a = None
    for g in vertex.groups:
        name = names.get(g.group)
        if name in bones and g.weight > 0.0:
            part = bones[name] * g.weight
            a = part if a is None else a + part
    return a


# ---------------------------------------------------------------- cloth moves

def neighbours(mesh_data, fit):
    """{vertex: [neighbour vertices]} among the fit vertices."""
    nb = {i: [] for i in fit}
    for e in mesh_data.edges:
        a, b = e.vertices
        if a in nb and b in nb:
            nb[a].append(b)
            nb[b].append(a)
    return nb


def push_out(points, fit, tree, clearance=CLEARANCE_M):
    """Move every fit point that is inside the body, or closer than `clearance` to it, to the clearance."""
    moved = 0
    for i in fit:
        p = points[i]
        hit = tree.find_nearest(p)
        if hit is None or hit[0] is None:
            continue
        loc, normal, _, dist = hit
        inside = (p - loc).dot(normal) < 0.0
        if inside or dist < clearance:
            points[i] = loc + normal * clearance
            moved += 1
    return moved


def smooth_moves(points, base, fit, nb, factor=0.5):
    """Laplacian smoothing of the move (points - base), so one vertex does not poke out alone."""
    delta = {i: points[i] - base[i] for i in fit}
    new = {}
    for i in fit:
        ns = nb[i]
        if not ns:
            new[i] = delta[i]
            continue
        avg = sum((delta[j] for j in ns), Vector()) / len(ns)
        new[i] = delta[i].lerp(avg, factor)
    for i in fit:
        points[i] = base[i] + new[i]


def fall(points, fit, tree, floor_z, clearance=CLEARANCE_M, reach=1.2):
    """Drop each fit point straight down onto the body or the floor under it."""
    down = Vector((0.0, 0.0, -1.0))
    for i in fit:
        p = points[i]
        z = floor_z + clearance
        hit = tree.ray_cast(p + Vector((0.0, 0.0, 0.03)), down, reach)
        if hit is not None and hit[0] is not None:
            z = max(z, hit[0].z + clearance)
        if p.z > z:
            points[i] = Vector((p.x, p.y, z))
        elif p.z < floor_z + clearance:
            points[i] = Vector((p.x, p.y, floor_z + clearance))


def seat_height(ground):
    """The height of the seat under a sitting body: the lowest point of the pelvis and the thighs."""
    names = {g.index: g.name for g in ground.vertex_groups}
    pts = evaluated_points(ground)
    low = []
    for v, p in zip(ground.data.vertices, pts):
        share = sum(g.weight for g in v.groups if names.get(g.group) in ("pelvis", "thigh_l", "thigh_r"))
        if share > 0.6:
            low.append(p.z)
    return min(low) if low else 0.0


def solve(mesh, rig, ground, action, frame, fit, nb, mode, floor_z=0.0, smooth_iterations=SMOOTH_ITERATIONS):
    """The cloth's positions in this pose after the collision rules of `mode`, and the posed positions
    without them; both as {vertex index: world position}."""
    set_pose(rig, action, frame)
    pts = evaluated_points(mesh)
    base = {i: pts[i].copy() for i in fit}
    tree = body_tree(ground)
    points = {i: base[i].copy() for i in fit}
    if floor_z == "seat":
        floor_z = seat_height(ground)
    for it in range(3 if mode == "drape" else 2):
        push_out(points, fit, tree)
        if mode == "drape":
            fall(points, fit, tree, floor_z)
        for _ in range(smooth_iterations):
            smooth_moves(points, base, fit, nb, 0.5)
        push_out(points, fit, tree)
    return points, base, bone_matrices(rig)


def rest_delta(mesh, vertex, bones, world_move):
    a = skinning_matrix(mesh, vertex, bones)
    if a is None or abs(a.determinant()) < 1e-8:
        return Vector()
    return a.inverted() @ world_move


def add_shape_key(mesh, name, moves):
    """A shape key `name` whose vertices are the rest positions moved by moves {index: rest-space delta}."""
    if mesh.data.shape_keys is None:
        mesh.shape_key_add(name="Basis", from_mix=False)
    key = mesh.shape_key_add(name=name, from_mix=False)
    for i, d in moves.items():
        key.data[i].co = mesh.data.vertices[i].co + d
    key.value = 0.0
    return key


# ---------------------------------------------------------------- the entry point

def fit_clip(mesh, rig, ground, action, mode, keys=None, floor_z=0.0, frames=None):
    """Shape keys for one clip. Returns {"keys": [names], "frames": [frame numbers], "max_move_m": float}."""
    fit = [i for i, v in enumerate(mesh.data.attributes["fit"].data) if v.value > 0.5]
    if not fit:
        return {}
    nb = neighbours(mesh.data, fit)
    start, end = (int(round(x)) for x in action.frame_range)
    count = end - start + 1
    if frames is None:
        frames = [start] if mode == "drape" else list(range(start, end + 1, max(1, round(count / (keys or 8)))))
    names = []
    biggest = 0.0
    for k, frame in enumerate(frames):
        points, base, bones = solve(mesh, rig, ground, action, frame, fit, nb, mode, floor_z=floor_z)
        moves = {}
        for i in fit:
            move = points[i] - base[i]
            biggest = max(biggest, move.length)
            if move.length > 1e-5:
                moves[i] = rest_delta(mesh, mesh.data.vertices[i], bones, move)
        name = f"{action.name}_{k:02d}" if mode == "clear" else action.name
        add_shape_key(mesh, name, moves)
        names.append(name)
    out = {"keys": names, "frames": frames, "frame_count": count, "mode": mode, "max_move_m": round(biggest, 4)}
    if floor_z == "seat":
        set_pose(rig, action, start)
        out["seat_height_m"] = round(seat_height(ground), 3)
    log("clip", action.name, mode, "keys", len(names), "cloth vertices", len(fit), "largest move %.3f m" % biggest,
        "seat %.3f m" % out["seat_height_m"] if "seat_height_m" in out else "")
    return out


def penetration_report(mesh, rig, ground, action, step=2, fits=None):
    """How deep the cloth is inside the body over a clip: (worst depth in metres, share of frames that have
    a vertex deeper than 5 mm). With `fits` the clip's shape keys are on, as in the game."""
    fit = [i for i, v in enumerate(mesh.data.attributes["fit"].data) if v.value > 0.5]
    start, end = (int(round(x)) for x in action.frame_range)
    worst = 0.0
    bad = 0
    n = 0
    for frame in range(start, end + 1, step):
        set_pose(rig, action, frame)
        if fits is not None:
            apply_weights(mesh, fits, action.name, frame)
            bpy.context.view_layer.update()
        pts = evaluated_points(mesh)
        tree = body_tree(ground)
        depth = 0.0
        for i in fit:
            hit = tree.find_nearest(pts[i])
            if hit and hit[0] is not None and (pts[i] - hit[0]).dot(hit[1]) < 0.0:
                depth = max(depth, hit[3])
        worst = max(worst, depth)
        bad += depth > 0.005
        n += 1
    return worst, bad / max(n, 1)


def apply_weights(mesh, fits, clip, frame):
    """Set the shape key values the game would set for `clip` at `frame` (a 'clear' clip blends its two
    nearest keys by phase, a 'drape' clip has its key on); every other key is off."""
    keys = mesh.data.shape_keys
    if keys is None:
        return
    for k in keys.key_blocks:
        if k.name != "Basis":
            k.value = 0.0
    got = fits.get(clip)
    if not got:
        return
    names = got["keys"]
    if got["mode"] == "drape":
        keys.key_blocks[names[0]].value = 1.0
        return
    frames = got["frames"]
    start, count = frames[0], got["frame_count"]
    n = len(names)
    phase = ((frame - start) % count) / count * n
    i0 = int(math.floor(phase)) % n
    w = phase - math.floor(phase)
    keys.key_blocks[names[i0]].value = 1.0 - w
    keys.key_blocks[names[(i0 + 1) % n]].value += w

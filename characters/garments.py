"""Medieval garments cut from the surface of the body, so they fit every body shape.

Each garment is a shell: a copy of some faces of the body, pushed out along the vertex normals.
The copy keeps the body's bone weights, so a garment bends with the rig exactly where the skin
would. The skirt and the cloak hem are lofted from the waist ring and weighted from the
hips. Runs inside Blender (see build_human.py).

All heights come from the rig's own joints, so a tall or a heavy body needs no new numbers.
"""

import json
import math

import bmesh
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

WOOL_BONES = ("pelvis", "spine_01", "spine_02", "spine_03", "clavicle_l", "clavicle_r",
              "upperarm_l", "upperarm_r", "lowerarm_l", "lowerarm_r", "neck_01")
HAND_BONES = ("hand_l", "hand_r")
FOREARM_BONES = ("lowerarm_l", "lowerarm_r")
TORSO_BONES = ("pelvis", "spine_01", "spine_02", "spine_03", "clavicle_l", "clavicle_r", "neck_01")


class Measures:
    """Rest-pose heights and positions taken from the rig, in metres."""

    def __init__(self, body, rig):
        b = rig.data.bones
        self.height = max(v.co.z for v in body.data.vertices)
        self.pelvis_z = b["pelvis"].head_local.z
        self.waist_z = b["spine_01"].head_local.z
        self.chest_z = b["spine_03"].head_local.z
        self.neck_z = b["neck_01"].head_local.z
        self.head_z = b["head"].head_local.z
        self.knee_z = b["calf_l"].head_local.z
        self.ankle_z = b["foot_l"].head_local.z
        # the crotch is the lowest vertex on the centre line between the legs
        centre = [v.co.z for v in body.data.vertices if abs(v.co.x) < 0.012 and 0.4 * self.height < v.co.z < self.pelvis_z]
        self.crotch_z = min(centre) if centre else self.pelvis_z - 0.1
        # the body's half width and half depth at the hips, for the floor shadow's width
        hips = [v.co for v in body.data.vertices if abs(v.co.z - self.pelvis_z) < 0.06 and abs(v.co.x) < 0.30]
        if hips:
            wx = max(p.x for p in hips) - min(p.x for p in hips)
            wy = max(p.y for p in hips) - min(p.y for p in hips)
            self.hip_radius = 0.5 * 0.5 * (wx + wy)
        else:
            self.hip_radius = 0.17
        head_top = self.height
        lips = [v.co for v in body.data.vertices if "lips" in body.vertex_groups
                and any(g.group == body.vertex_groups["lips"].index and g.weight > 0.3 for g in v.groups)]
        self.lips_z = sum(v.z for v in lips) / len(lips) if lips else head_top - 0.185
        self.chin_z = self.lips_z - 0.065
        self.eye_z = self.lips_z + 0.072
        self.brow_z = self.lips_z + 0.105
        self.collar_z = self.chin_z - 0.045
        skull = [v.co for v in body.data.vertices if v.co.z > self.chin_z]
        ys = [v.y for v in skull]
        self.head_centre = Vector((0.0, (min(ys) + max(ys)) * 0.5, (self.chin_z + head_top) * 0.5))


def vertex_weight_sum(vertex, deform, indices):
    return sum(w for i, w in vertex[deform].items() if i in indices)


def group_indices(body, names):
    return {body.vertex_groups[n].index for n in names if n in body.vertex_groups}


def new_bm_from(body):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.layers.deform.verify()
    return bm


def keep_faces(bm, keep):
    doomed = [f for f in bm.faces if not keep(f)]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")


def face_centre(f):
    return f.calc_center_median()


def cut_z(bm, z, keep):
    """Cut the mesh with the plane z, so the edge of the garment is a clean loop; keep 'below' or 'above'."""
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Vector((0, 0, z)), plane_no=Vector((0, 0, 1)),
                           clear_inner=(keep == "above"), clear_outer=(keep == "below"))
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")


def offset(bm, amount_fn):
    """Push every vertex out along its normal by amount_fn(vertex, normal)."""
    bm.normal_update()
    moves = [(v, v.normal.copy() * amount_fn(v, v.normal)) for v in bm.verts]
    for v, d in moves:
        v.co += d


def smooth(bm, iterations=2, factor=0.5):
    for _ in range(iterations):
        bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=factor, use_axis_x=True, use_axis_y=True, use_axis_z=True)


def to_object(bm, name, material=None):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def copy_groups(src, dst):
    for g in src.vertex_groups:
        dst.vertex_groups.new(name=g.name)


def mark_fit(obj):
    """Mark every vertex of obj as free cloth: posefit.py moves these vertices out of the legs in a stride,
    or drapes them over a body that lies or sits (attribute 'fit', kept by the join)."""
    attr = obj.data.attributes.new("fit", "FLOAT", "POINT")
    attr.data.foreach_set("value", [1.0] * len(obj.data.vertices))


def tag(obj, kind, color, wear=None):
    """Colour, kind and wear overrides (dirt, wet, stain) of a garment, read when the mesh is merged."""
    obj["garment"] = kind
    obj["color"] = list(color)
    if wear:
        obj["wear"] = json.dumps(wear)


# ---------------------------------------------------------------- garments

ARM_BONES = ("upperarm_l", "upperarm_r", "lowerarm_l", "lowerarm_r")


def arm_end(rig, side, above=0.0):
    """The point `above` metres up the upper arm from the elbow, and the direction of the upper arm
    (shoulder to elbow), in the rest pose."""
    b = rig.data.bones
    elbow = b[f"lowerarm_{side}"].head_local.copy()
    axis = (elbow - b[f"upperarm_{side}"].head_local).normalized()
    return elbow - axis * above, axis


def tunic(body, rig, m, spec):
    """Torso, sleeves and collar, cut from the body between the neck and the hip.

    "sleeves": "elbow" ends the sleeves `cuff_above_elbow` (m) above the elbow, with a cut plane
    across the upper arm, and rolls the cuff ("roll": how far the roll stands off the sleeve); the
    forearm is bare skin (garments.skin, "forearms")."""
    idx = group_indices(body, WOOL_BONES)
    hand_idx = group_indices(body, HAND_BONES)
    arm_idx = group_indices(body, ARM_BONES)
    elbow_sleeves = spec.get("sleeves") == "elbow"
    bm = new_bm_from(body)
    deform = bm.verts.layers.deform.active

    def keep(f):
        c = face_centre(f)
        if c.z < m.pelvis_z + 0.06 and abs(c.x) < 0.30:
            return True       # the hips: the whole column, whichever bone owns the skin
        wool = sum(vertex_weight_sum(v, deform, idx) for v in f.verts) / 4.0
        hand = sum(vertex_weight_sum(v, deform, hand_idx) for v in f.verts) / 4.0
        return wool > 0.5 and hand < 0.5

    keep_faces(bm, keep)
    cut_z(bm, m.collar_z + spec.get("collar_rise", 0.0), "below")
    cut_z(bm, m.pelvis_z - 0.02, "above")
    ends = {side: arm_end(rig, side, spec.get("cuff_above_elbow", 0.02)) for side in "lr"}
    if elbow_sleeves:
        for side, (point, axis) in ends.items():
            arm = {v for v in bm.verts if vertex_weight_sum(v, deform, arm_idx) > 0.5
                   and (v.co.x > 0) == (rig.data.bones[f"upperarm_{side}"].head_local.x > 0)}
            geom = list(arm) + [e for e in bm.edges if all(v in arm for v in e.verts)] + \
                [f for f in bm.faces if all(v in arm for v in f.verts)]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=point, plane_no=axis, clear_outer=True)
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    ease = spec.get("ease", 0.016)
    sleeve_ease = spec.get("sleeve_ease", 0.012)
    roll = spec.get("roll", 0.014)

    def amount(v, n):
        if abs(v.co.x) <= 0.2:
            return ease
        if not elbow_sleeves:
            return sleeve_ease
        point, axis = min(ends.values(), key=lambda e: (v.co - e[0]).length)
        s = (v.co - point).dot(axis)               # < 0 on the shoulder side of the cuff
        return sleeve_ease + roll * smoothstep((s + 0.040) / 0.010)

    offset(bm, amount)
    smooth(bm, 2, 0.4)
    obj = to_object(bm, "tunic")
    copy_groups(body, obj)
    tag(obj, "tunic", spec["color"], spec.get("wear"))
    return obj


def hose(body, rig, m, spec):
    bm = new_bm_from(body)
    keep_faces(bm, lambda f: abs(face_centre(f).x) < 0.30 and face_centre(f).z < m.pelvis_z)
    cut_z(bm, m.pelvis_z - 0.03, "below")
    offset(bm, lambda v, n: spec.get("ease", 0.005))
    obj = to_object(bm, "hose")
    copy_groups(body, obj)
    tag(obj, "hose", spec["color"], spec.get("wear"))
    return obj


def boots(body, rig, m, spec):
    top = m.ankle_z + spec.get("height", 0.26)
    bm = new_bm_from(body)
    keep_faces(bm, lambda f: face_centre(f).z < top + 0.05 and abs(face_centre(f).x) < 0.30)
    cut_z(bm, top, "below")

    def amount(v, n):
        t = max(0.0, (v.co.z - m.ankle_z) / (top - m.ankle_z))
        flare = 0.012 * max(0.0, t - 0.75) / 0.25      # the cuff stands off the calf
        return spec.get("ease", 0.010) + flare

    offset(bm, amount)
    smooth(bm, 1, 0.3)
    obj = to_object(bm, "boots")
    copy_groups(body, obj)
    tag(obj, "boots", spec["color"], spec.get("wear"))
    return obj


def skin(body, rig, m, spec):
    """What shows: head and neck above the collar, and the hands below the cuffs."""
    hand_idx = group_indices(body, HAND_BONES)
    arm_idx = group_indices(body, ARM_BONES)
    bm = new_bm_from(body)
    deform = bm.verts.layers.deform.active
    neck_cut = m.collar_z - spec.get("neck_cut", 0.025)
    forearms = spec.get("forearms", False)    # bare below the sleeves that tunic ends above the elbow
    ends = {side: arm_end(rig, side, spec.get("cuff_above_elbow", 0.02) + 0.04) for side in "lr"}

    def keep(f):
        c = face_centre(f)
        if c.z > neck_cut:
            return True
        hand = sum(vertex_weight_sum(v, deform, hand_idx) for v in f.verts) / 4.0
        if forearms and abs(c.x) > 0.2 and \
                sum(vertex_weight_sum(v, deform, arm_idx) for v in f.verts) / 4.0 > 0.5:
            point, axis = min(ends.values(), key=lambda e: (c - e[0]).length)
            if (c - point).dot(axis) > 0.0:       # 4 cm of skin goes under the cuff
                return True
        return hand > 0.3 and c.z < m.chest_z

    keep_faces(bm, keep)
    # the base mesh has a few collapsed quads at the nostrils and the lip corners: their normals are
    # undefined and shade black, single specks on the face
    bmesh.ops.dissolve_degenerate(bm, dist=0.0004, edges=list(bm.edges))
    flat = [f for f in bm.faces if f.calc_area() < 1e-7]
    bmesh.ops.delete(bm, geom=flat, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = to_object(bm, "skin")
    copy_groups(body, obj)
    obj["garment"] = "skin"
    return obj


def hood(body, rig, m, spec):
    """A hood over the back and top of the head, the face open toward -Y, and a cowl on the shoulders."""
    bm = new_bm_from(body)
    cowl_z = m.collar_z - spec.get("cowl_drop", 0.12)
    if "bottom_above_chin" in spec:
        cowl_z = m.chin_z + spec["bottom_above_chin"]      # a cap: it ends at the nape, with no cowl
    hc = m.head_centre
    open_bottom = m.chin_z - 0.012
    open_top = m.brow_z + spec.get("open_top", 0.035)
    zc = (open_bottom + open_top) * 0.5
    face_h = (open_top - open_bottom) * 0.5
    face_w = spec.get("face_half_width", 0.080)
    keep_faces(bm, lambda f: face_centre(f).z > cowl_z - 0.03 and abs(face_centre(f).x) < 0.30)
    cut_z(bm, cowl_z, "above")
    # shoulders end where the arms start
    for sign in (1, -1):
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Vector((sign * spec.get("cowl_half_width", 0.20), 0, 0)),
                               plane_no=Vector((sign, 0, 0)), clear_outer=True)
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")

    def keep(f):
        c = face_centre(f)
        facing_front = c.y < hc.y - spec.get("open_depth", 0.0) and (f.normal.y < -0.15 or spec.get("open_through"))
        if facing_front and c.z > open_bottom - 0.02:
            nx = c.x / face_w
            nz = (c.z - zc) / face_h
            if nx * nx + nz * nz < 1.0:
                return False
        if c.z < m.collar_z + 0.01 and f.normal.y < -0.1:
            # the cowl is open in a V on the chest
            if abs(c.x) < 0.035 + (m.collar_z + 0.01 - c.z) * 0.3:
                return False
        return True

    keep_faces(bm, keep)
    head_ease = spec.get("head_ease", 0.022)
    cowl_ease = spec.get("cowl_ease", 0.040)

    def amount(v, n):
        z = v.co.z
        if z > m.collar_z + 0.03:
            back = max(0.0, v.co.y - hc.y) / 0.1
            return head_ease + 0.014 * min(1.0, back)
        t = min(1.0, (m.collar_z + 0.03 - z) / max(1e-3, (m.collar_z + 0.03 - cowl_z)))
        return head_ease + (cowl_ease - head_ease) * t

    offset(bm, amount)
    peak = spec.get("peak", 0.045)
    for v in bm.verts:
        if v.co.z > hc.z + 0.02 and v.co.y > hc.y + 0.01:
            k = min(1.0, (v.co.z - hc.z - 0.02) / 0.08) * min(1.0, (v.co.y - hc.y) / 0.08)
            v.co.y += 0.6 * peak * k
            v.co.z += 0.5 * peak * k
    smooth(bm, 2, 0.4)
    obj = to_object(bm, "hood")
    copy_groups(body, obj)
    tag(obj, spec.get("kind", "hood"), spec["color"], spec.get("wear"))
    return obj


def belt(body, rig, m, spec):
    z0 = m.waist_z - 0.02 + spec.get("raise", 0.0)
    z1 = z0 + spec.get("width", 0.045)
    bm = new_bm_from(body)

    def keep(f):
        c = face_centre(f)
        return z0 - 0.03 < c.z < z1 + 0.03 and abs(c.x) < spec.get("half_width", 0.24)

    keep_faces(bm, keep)
    cut_z(bm, z0, "above")
    cut_z(bm, z1, "below")
    offset(bm, lambda v, n: spec.get("ease", 0.028))
    obj = to_object(bm, "belt")
    copy_groups(body, obj)
    tag(obj, spec.get("kind", "belt"), spec["color"], spec.get("wear"))
    return obj


def smoothstep(x):
    """0 below -1, 1 above +1, smooth between."""
    t = max(0.0, min(1.0, 0.5 + 0.5 * x))
    return t * t * (3 - 2 * t)


def skirt(body, rig, m, tunic_obj, spec):
    """The tunic skirt: the tunic's hip edge extruded down in rings, with room for the legs.

    The hem swings with the thighs only partly, so the skirt is wide in front and behind: a leg that
    steps forward 0.15 m must not come through the cloth.
    """
    hem_z = spec.get("hem_z", m.knee_z + spec.get("hem_above_knee", 0.07))
    if "hem_above_ankle" in spec:
        hem_z = m.ankle_z + spec["hem_above_ankle"]
    rows = spec.get("rows", 5)
    flare = spec.get("flare", 0.06)
    stride_room = spec.get("stride_room", 0.07)    # per row, so it grows with the row count
    stride_total = spec.get("stride_total")        # the whole extra room at the hem, instead
    thigh_share = spec.get("thigh_share", 0.45)    # of the hem's weight, the part carried by the thighs
    side_bias = spec.get("side_bias", 1.0)         # 1: each side follows its own thigh; 0: both thighs alike
    fold_amp = spec.get("fold_amp", 0.0)           # radial folds of the cloth, as a share of the radius at the hem
    fold_count = spec.get("fold_count", 7)
    bm = bmesh.new()
    bm.from_mesh(tunic_obj.data)
    deform = bm.verts.layers.deform.verify()
    z_min = min(v.co.z for v in bm.verts if abs(v.co.x) < 0.25)
    # the hem edge of the shell, whose height wavers a few cm after smoothing (the sleeve and collar edges are far above)
    edges = [e for e in bm.edges if e.is_boundary and all(v.co.z < z_min + spec.get("ring_tol", 0.06) for v in e.verts)]
    ring = {v for e in edges for v in e.verts}
    centre = sum((v.co for v in ring), Vector()) / len(ring)
    centre.z = z_min
    leg_idx = group_indices(body, ("thigh_l", "thigh_r", "calf_l", "calf_r", "foot_l", "foot_r", "ball_l", "ball_r"))
    legs = [v.co for v in body.data.vertices if hem_z - 0.05 < v.co.z < z_min and abs(v.co.x) < 0.3
            and sum(g.weight for g in v.groups if g.group in leg_idx) > 0.5]

    kd = KDTree(len(body.data.vertices))
    for v in body.data.vertices:
        kd.insert(v.co, v.index)
    kd.balance()
    body_w = {v.index: {body.vertex_groups[g.group].name: g.weight for g in v.groups} for v in body.data.vertices}
    group_index = {g.name: g.index for g in body.vertex_groups}

    skirt_faces = set()
    lower = []
    for k in range(1, rows + 1):
        t, t_prev = k / rows, (k - 1) / rows
        ret = bmesh.ops.extrude_edge_only(bm, edges=edges)
        new_verts = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
        edges = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMEdge) and g.is_boundary]
        skirt_faces.update(g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace))
        z = z_min + (hem_z - z_min) * t
        for v in new_verts:
            d = Vector((v.co.x - centre.x, v.co.y - centre.y, 0.0))
            r_prev = d.length
            direction = d / r_prev if r_prev > 1e-6 else Vector((1, 0, 0))
            reach = r_prev
            for p in legs:
                if abs(p.z - z) < 0.04:
                    q = Vector((p.x - centre.x, p.y - centre.y, 0.0))
                    along = q.dot(direction)
                    if along > 0 and (q - direction * along).length < 0.08:
                        reach = max(reach, along + 0.04)
            front_back = abs(direction.y)
            if stride_total is None:
                r = max(r_prev + flare * (t * t - t_prev * t_prev), reach + stride_room * t * (0.4 + 0.6 * front_back))
            else:       # the extra room is spread over the rows, whatever their number
                r = max(r_prev + flare * (t * t - t_prev * t_prev) + stride_total * (t - t_prev) * (0.4 + 0.6 * front_back), reach)
            if fold_amp:
                # pleats: a wave around the skirt that grows toward the hem, a little different per row
                theta = math.atan2(direction.y, direction.x)
                r *= 1.0 + fold_amp * t * t * math.sin(fold_count * theta + 1.7 * t)
            v.co = Vector((centre.x + direction.x * r, centre.y + direction.y * r, z))
            # the hem follows the thigh on its own side: left of the middle with the left leg, right with the
            # right, blended across the middle so the front and back do not tear
            side = smoothstep((v.co.x - centre.x) / 0.08)
            share = thigh_share * t
            for g in list(v[deform].keys()):
                del v[deform][g]
            side = 0.5 + side_bias * (side - 0.5)
            v[deform][group_index["pelvis"]] = 1.0 - share
            v[deform][group_index["thigh_l"]] = share * side
            v[deform][group_index["thigh_r"]] = share * (1.0 - side)
        lower.extend(new_verts)
    bmesh.ops.smooth_vert(bm, verts=lower, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=False)
    bmesh.ops.smooth_vert(bm, verts=lower, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=False)
    doomed = [f for f in bm.faces if f not in skirt_faces]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = to_object(bm, "skirt")
    copy_groups(body, obj)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    tag(obj, spec.get("kind", "tunic"), spec["color"], spec.get("wear"))
    mark_fit(obj)
    return obj


def hose_trim(obj, m, hem_z, boot_top):
    """Drop the part of the hose that the skirt and the boots always cover."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    cut_z(bm, hem_z + 0.12, "below")
    cut_z(bm, boot_top - 0.03, "above")
    bm.to_mesh(obj.data)
    bm.free()


def coif(body, rig, m, spec):
    """A close collar over the neck and shoulders, seen between the hood and the tunic."""
    bm = new_bm_from(body)
    keep_faces(bm, lambda f: m.collar_z - 0.10 < face_centre(f).z < m.chin_z + 0.04 and abs(face_centre(f).x) < 0.22)
    cut_z(bm, m.chin_z + 0.005, "below")
    cut_z(bm, m.collar_z - 0.10, "above")
    for sign in (1, -1):
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Vector((sign * 0.19, 0, 0)), plane_no=Vector((sign, 0, 0)),
                               clear_outer=True)
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    offset(bm, lambda v, n: spec.get("ease", 0.024) + (0.012 if v.co.z < m.collar_z else 0.0))
    smooth(bm, 2, 0.4)
    obj = to_object(bm, "coif")
    copy_groups(body, obj)
    tag(obj, "coif", spec["color"], spec.get("wear"))
    return obj


def satchel(body, rig, m, spec):
    """A strap across the chest from the right shoulder to the left hip, and a bag on the hip."""
    side = spec.get("side", 1.0)           # +1: bag on the character's left (+X)
    a = Vector((-side * 0.17, 0.0, m.collar_z - 0.05))     # shoulder
    b = Vector((side * 0.25, 0.02, m.pelvis_z - 0.06))     # hip
    bm = new_bm_from(body)
    ab = b - a

    # the band is straight in the front view, so it is cut out with planes along the line, which
    # leaves clean edges on the chest, over the shoulder and on the back
    a2, ab2 = Vector((a.x, 0.0, a.z)), Vector((ab.x, 0.0, ab.z))
    along = ab2.normalized()
    across = Vector((-along.z, 0.0, along.x))
    width = spec.get("strap_width", 0.024)

    def dist(p):
        q = Vector((p.x, 0.0, p.z)) - a2
        return abs(q.dot(across))

    keep_faces(bm, lambda f: dist(face_centre(f)) < width + 0.035 and m.pelvis_z - 0.12 < face_centre(f).z < m.collar_z
               and abs(face_centre(f).x) < 0.27)
    for sign in (1.0, -1.0):
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=a2 + across * sign * width, plane_no=across * sign, clear_outer=True)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=a2 + ab2 + along * 0.02, plane_no=along, clear_outer=True)
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    offset(bm, lambda v, n: spec.get("strap_ease", 0.028))
    strap = to_object(bm, "strap")
    copy_groups(body, strap)
    tag(strap, "leather", spec["color"], spec.get("wear"))
    # the bag: a flattened, softened box hanging at the hip
    bag_bm = bmesh.new()
    deform = bag_bm.verts.layers.deform.verify()
    w, d, h = spec.get("bag", (0.075, 0.20, 0.17))
    centre = Vector((side * spec.get("bag_x", 0.255), 0.10, m.pelvis_z - 0.15))
    bmesh.ops.create_cube(bag_bm, size=1.0)
    for v in bag_bm.verts:
        v.co = Vector((v.co.x * w, v.co.y * d, v.co.z * h)) + centre
    bmesh.ops.bevel(bag_bm, geom=list(bag_bm.verts) + list(bag_bm.edges), offset=0.02, segments=1, affect="EDGES")
    gi = {g.name: g.index for g in body.vertex_groups}
    for v in bag_bm.verts:
        v[deform][gi["pelvis"]] = 0.75
        v[deform][gi["spine_01"]] = 0.25
    bag = to_object(bag_bm, "bag")
    copy_groups(body, bag)
    tag(bag, "leather", spec["color"], spec.get("wear"))
    return [strap, bag]


def jerkin(body, rig, m, spec):
    """A leather jerkin over the tunic: the torso from the hip to below the collar bones, without sleeves."""
    idx = group_indices(body, ("pelvis", "spine_01", "spine_02", "spine_03"))
    bm = new_bm_from(body)
    deform = bm.verts.layers.deform.active
    keep_faces(bm, lambda f: abs(face_centre(f).x) < 0.30 and (face_centre(f).z < m.pelvis_z + 0.06 or (
        sum(vertex_weight_sum(v, deform, idx) for v in f.verts) / 4.0 > 0.55 and abs(face_centre(f).x) < 0.17)))
    cut_z(bm, m.pelvis_z - 0.02, "above")
    cut_z(bm, m.chest_z + spec.get("top", 0.22), "below")
    offset(bm, lambda v, n: spec.get("ease", 0.030))
    smooth(bm, 2, 0.4)
    obj = to_object(bm, "jerkin")
    copy_groups(body, obj)
    tag(obj, "leather", spec["color"], spec.get("wear"))
    return obj


# ---------------------------------------------------------------- the cook's and the courier's pieces

def apron(body, rig, m, dress_parts, spec):
    """A bib apron over a dress: the front of the dress's own shell, pushed out a little further.

    dress_parts are the dress objects (bodice and skirt); the apron follows their surface, so the
    flare of the skirt carries over. "bib_half_width" and "skirt_half_width" are the widths above
    and below the waist, "top" is how far above the chest joint the bib ends, "hem_above_floor" where
    the apron ends. Returns the bib, the skirt panel and the waist tie."""
    waist = m.waist_z + spec.get("waist_shift", 0.0)
    top = m.chest_z + spec.get("top", 0.10)
    hem = spec.get("hem_above_floor", 0.30)

    def panel(name, z0, z1, half):
        bm = bmesh.new()
        bm.verts.layers.deform.verify()
        for part in dress_parts:
            bm.from_mesh(part.data)
        keep_faces(bm, lambda f: f.normal.y < -0.05 and z0 - 0.05 < face_centre(f).z < z1 + 0.05
                   and abs(face_centre(f).x) < half + 0.05)
        cut_z(bm, z1, "below")
        cut_z(bm, z0, "above")
        for sign in (1, -1):
            geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Vector((sign * half, 0, 0)), plane_no=Vector((sign, 0, 0)),
                                   clear_outer=True)
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        offset(bm, lambda v, n: spec.get("ease", 0.010))
        smooth(bm, 1, 0.3)
        obj = to_object(bm, name)
        copy_groups(body, obj)
        tag(obj, "apron", spec["color"], spec.get("wear"))
        return obj

    bib = panel("apron_bib", waist, top, spec.get("bib_half_width", 0.14))
    skirt_panel = panel("apron_skirt", hem, waist, spec.get("skirt_half_width", 0.27))
    tie = belt(body, rig, m, {"color": spec.get("tie_color", spec["color"]), "width": 0.035,
                              "raise": waist - m.waist_z - 0.015, "ease": spec.get("tie_ease", 0.060),
                              "half_width": spec.get("tie_half_width", 0.30), "kind": "apron",
                              "wear": spec.get("wear")})
    return [bib, skirt_panel, tie]


def front_y(body, x, z, reach=0.012):
    """The front-most (smallest) y of the body near (x, z)."""
    ys = [v.co.y for v in body.data.vertices if abs(v.co.x - x) < reach and abs(v.co.z - z) < reach]
    return min(ys) if ys else 0.0


def kerchief(body, rig, m, spec):
    """A linen kerchief tied under the chin: a close hood with a wide face opening and a throat band,
    a knot at the chin and two short tails lying on the chest."""
    hood_spec = dict(spec)
    hood_spec.setdefault("cowl_drop", 0.025)
    hood_spec.setdefault("cowl_half_width", 0.085)
    hood_spec.setdefault("cowl_ease", 0.020)
    hood_spec.setdefault("head_ease", 0.018)
    hood_spec.setdefault("peak", 0.015)
    hood_spec.setdefault("open_top", 0.045)
    hood_spec.setdefault("open_depth", 0.02)       # the whole front of the face is open, not only what faces forward
    hood_spec.setdefault("open_through", True)
    hood_spec["kind"] = "linen"
    cloth = hood(body, rig, m, hood_spec)
    knot_z = m.chin_z - spec.get("knot_drop", 0.040)
    ease = spec.get("knot_ease", 0.034)
    gi = {g.name: g.index for g in body.vertex_groups}
    bm = bmesh.new()
    deform = bm.verts.layers.deform.verify()
    y0 = front_y(body, 0.0, knot_z) - ease
    # the knot: a soft lump
    bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * 0.030, v.co.y * 0.020, v.co.z * 0.022)) + Vector((0.0, y0 - 0.004, knot_z))
        v[deform][gi["neck_01"]] = 0.5
        v[deform][gi["head"]] = 0.5
    # two tails: strips that follow the chest, splayed a little
    length = spec.get("tail_length", 0.15)
    for sign in (-1.0, 1.0):
        rows = []
        for k in range(6):
            t = k / 5.0
            z = knot_z - 0.012 - length * t
            xc = sign * (0.012 + 0.030 * t)
            ring = []
            for dx in (-0.011, 0.011):
                x = xc + dx
                y = front_y(body, x, z, 0.02) - ease - 0.012
                v = bm.verts.new(Vector((x, y, z)))
                share = min(1.0, t * 1.5)
                v[deform][gi["neck_01"]] = (1.0 - share) * 0.5
                v[deform][gi["head"]] = (1.0 - share) * 0.5
                v[deform][gi["spine_03"]] = share
                ring.append(v)
            rows.append(ring)
        for a, b in zip(rows, rows[1:]):
            bm.faces.new((a[0], a[1], b[1], b[0]))
    bm.normal_update()
    tails = to_object(bm, "kerchief_ties")
    copy_groups(body, tails)
    for poly in tails.data.polygons:
        poly.use_smooth = True
    tag(tails, "linen", spec["color"], spec.get("wear"))
    return [cloth, tails]


def hair_cap(body, rig, m, spec):
    """Hair as a thin cap over the skull that ends at the nape, with a fringe over the brow."""
    cap_spec = dict(spec)
    cap_spec.setdefault("bottom_above_chin", 0.045)
    cap_spec.setdefault("head_ease", 0.008)
    cap_spec.setdefault("peak", 0.0)
    cap_spec.setdefault("open_top", 0.050)
    cap_spec.setdefault("face_half_width", 0.082)
    cap_spec["kind"] = "hair"
    obj = hood(body, rig, m, cap_spec)
    roughen_hair(obj, spec.get("ragged", 0.010), spec.get("bumpy", 0.004))
    return obj


WRINKLES = {   # garment kind -> (amplitude in metres, spatial frequency per metre)
    "tunic": (0.0035, 11.0), "hose": (0.0015, 12.0), "hood": (0.0060, 9.0), "cloak": (0.0060, 8.0),
    "linen": (0.0090, 11.0), "apron": (0.0045, 12.0), "coif": (0.0020, 14.0),
}


def wrinkle(obj, kind, seed=0.0):
    """Soft wrinkles on a cloth garment: noise along the normals, a few millimetres, so wool is not a
    perfectly smooth shell. Leather, boots and hair are left alone."""
    if kind not in WRINKLES:
        return
    from mathutils import noise
    amp, freq = WRINKLES[kind]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    for v in bm.verts:
        n = noise.fractal(v.co * freq + Vector((seed, 2.0 * seed, 0.5 * seed)), 0.5, 2.0, 2)
        v.co += v.normal * (amp * n)
    bm.to_mesh(obj.data)
    bm.free()


def roughen_hair(obj, ragged, bumpy):
    """Take the perfect smoothness off a hair cap: a few millimetres of noise along the surface, and a
    hairline that wanders by `ragged` metres, so the cap is not a swim cap."""
    from mathutils import noise
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    for v in bm.verts:
        p = v.co * 46.0
        n = noise.fractal(p, 0.5, 2.0, 3)
        v.co += v.normal * (bumpy * n)
        if any(e.is_boundary for e in v.link_edges):
            w = noise.fractal(v.co * 70.0 + Vector((9.0, 3.0, 1.0)), 0.5, 2.0, 2)
            v.co.z += ragged * w
    bm.to_mesh(obj.data)
    bm.free()


def cloak(body, rig, m, spec):
    """A cloak: the back and shoulders as a shell, open in front, and a hem lofted down to the calf.

    Returns the shell and the loft; both follow the rig, the hem partly with the thighs."""
    idx = group_indices(body, TORSO_BONES + ("upperarm_l", "upperarm_r"))
    bm = new_bm_from(body)
    deform = bm.verts.layers.deform.active
    half = spec.get("half_width", 0.215)
    opening = spec.get("opening", 0.105)

    def keep(f):
        c = face_centre(f)
        if abs(c.x) > half:
            return False
        if f.normal.y < -0.30 and abs(c.x) < opening and c.z < m.collar_z - 0.02:
            return False
        if c.z < m.pelvis_z + 0.06:
            return True
        return sum(vertex_weight_sum(v, deform, idx) for v in f.verts) / 4.0 > 0.5

    keep_faces(bm, keep)
    cut_z(bm, m.collar_z + spec.get("collar_rise", 0.015), "below")
    cut_z(bm, m.pelvis_z - 0.02, "above")
    ease = spec.get("ease", 0.040)
    offset(bm, lambda v, n: ease + (0.016 if v.co.y > m.head_centre.y - 0.02 else 0.0))   # the back stands off more
    smooth(bm, 3, 0.5)
    shell = to_object(bm, "cloak")
    copy_groups(body, shell)
    tag(shell, "cloak", spec["color"], spec.get("wear"))
    hem = dict(spec)
    hem.setdefault("hem_z", m.knee_z - spec.get("hem_below_knee", 0.20))
    hem.setdefault("rows", 6)
    hem.setdefault("flare", 0.15)
    hem.setdefault("stride_room", 0.11)
    hem.setdefault("thigh_share", 0.30)
    hem["kind"] = "cloak"
    skirt_obj = skirt(body, rig, m, shell, hem)
    return [shell, skirt_obj]

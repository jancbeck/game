"""Retarget CMU BVH motion onto the MPFB game_engine rig and cut it into game clips.

Runs inside Blender (mathutils). The method is a world-space orientation retarget:

1. Frame 0 of every CMU file is a T pose. Each source joint's orientation change from frame 0
   (world space) is applied to the matching rig bone, starting from a reference orientation
   that points the bone the way the source bone pointed on frame 0. The rig's own rest pose
   (arms down at 45 degrees) therefore does not matter.
2. The pelvis moves by the hips' travel, scaled by the ratio of leg lengths.
3. A walk is cut from one gait cycle (left heel strike to the next), made in place, and
   cross-faded at the seam so it loops. Its duration is scaled so that the ground speed is
   exactly SPEED, so the feet do not slide.

Clips are returned as lists of per-frame {bone: (quaternion, location)} in pose space, and
written to actions by `make_action`.
"""

import math

import bpy
from mathutils import Matrix, Quaternion, Vector

import bvh as bvhlib

# BVH (Y up, +Z forward) to Blender (Z up, -Y forward)
C = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))

# rig bone -> (source joint, source child joint that gives the bone's direction on frame 0)
MAP = {
    "pelvis": ("Hips", "Spine"),
    "spine_01": ("LowerBack", "Spine"),
    "spine_02": ("Spine", "Spine1"),
    "spine_03": ("Spine1", "Neck1"),
    "neck_01": ("Neck", "Head"),
    "head": ("Head", None),
    "clavicle_l": ("LeftShoulder", "LeftArm"),
    "upperarm_l": ("LeftArm", "LeftForeArm"),
    "lowerarm_l": ("LeftForeArm", "LeftHand"),
    "hand_l": ("LeftHand", "LeftHandIndex1"),
    "clavicle_r": ("RightShoulder", "RightArm"),
    "upperarm_r": ("RightArm", "RightForeArm"),
    "lowerarm_r": ("RightForeArm", "RightHand"),
    "hand_r": ("RightHand", "RightHandIndex1"),
    "thigh_l": ("LeftUpLeg", "LeftLeg"),
    "calf_l": ("LeftLeg", "LeftFoot"),
    "foot_l": ("LeftFoot", "LeftToeBase"),
    "ball_l": ("LeftToeBase", None),
    "thigh_r": ("RightUpLeg", "RightLeg"),
    "calf_r": ("RightLeg", "RightFoot"),
    "foot_r": ("RightFoot", "RightToeBase"),
    "ball_r": ("RightToeBase", None),
}


def _m3(rows):
    return Matrix(rows)


def to_blender(m):
    """3x3 BVH rotation (list of rows) to a Blender rotation matrix."""
    return C @ _m3(m) @ C.transposed()


def v_to_blender(v):
    return C @ Vector(v)


class Source:
    """One BVH clip: per frame, world orientation of each joint and the hips position, in Blender axes."""

    def __init__(self, path):
        self.path = path
        self.bvh = bvhlib.parse(path)
        self.fps = self.bvh.fps
        self.rot = []   # per frame {joint: Matrix 3x3}
        self.pos = []   # per frame {joint: Vector} (metres)
        for f in range(len(self.bvh.frames)):
            w = bvhlib.fk(self.bvh, f)
            self.rot.append({n: to_blender(r) for n, (r, p) in w.items()})
            self.pos.append({n: v_to_blender(p) * bvhlib.CMU_UNIT_M for n, (r, p) in w.items()})

    def child_dir(self, joint, child, frame=0):
        if child is None:
            end = self.bvh.end_offset.get(joint)
            if end is None:
                return None
            d = self.rot[frame][joint] @ v_to_blender_local(end)
            return d.normalized()
        return (self.pos[frame][child] - self.pos[frame][joint]).normalized()

    def leg_length(self):
        return self.pos[0]["LeftUpLeg"].z - self.pos[0]["LeftFoot"].z

    def hip_height(self):
        return self.pos[0]["LeftUpLeg"].z


def v_to_blender_local(v):
    return C @ Vector(v)


class Retargeter:
    def __init__(self, rig):
        self.rig = rig
        self.bones = rig.data.bones
        self.order = [b.name for b in self.bones]          # parents before children
        self.rest = {b.name: b.matrix_local.copy() for b in self.bones}
        self.rest_rel = {}
        for b in self.bones:
            self.rest_rel[b.name] = (self.rest[b.parent.name].inverted() @ self.rest[b.name]) if b.parent else self.rest[b.name]
        self.scale = 1.0

    # ---- reference orientations
    def reference(self, src):
        """Armature-space reference orientation of every mapped bone: its rest orientation turned so
        that it points where the source bone pointed on frame 0."""
        ref = {}
        for bone, (joint, child) in MAP.items():
            b = self.bones[bone]
            rest_dir = (b.tail_local - b.head_local).normalized()
            d_src = src.child_dir(joint, child, 0)
            q = rest_dir.rotation_difference(d_src)
            ref[bone] = q.to_matrix() @ self.rest[bone].to_3x3()
        self.ref = ref
        self.ref_rot = {bone: src.rot[0][MAP[bone][0]] for bone in MAP}
        self.scale = (self.bones["thigh_l"].head_local.z - self.bones["foot_l"].head_local.z) / src.leg_length()
        self.ref_hips = src.pos[0]["Hips"].copy()
        self.pelvis_rest = self.bones["pelvis"].head_local.copy()
        return ref

    # ---- per frame
    def desired(self, src, frame):
        """{bone: (Quaternion armature-space orientation)}, pelvis position (armature space)."""
        out = {}
        for bone, (joint, _child) in MAP.items():
            delta = src.rot[frame][joint] @ self.ref_rot[bone].inverted()
            out[bone] = (delta @ self.ref[bone]).to_quaternion()
        hips = (src.pos[frame]["Hips"] - self.ref_hips) * self.scale
        return out, self.pelvis_rest + hips

    def basis(self, orient, pelvis_pos):
        """Pose-space {bone: (rotation quaternion, location)} for desired armature-space orientations."""
        pose = {}
        result = {}
        for name in self.order:
            b = self.bones[name]
            parent_pose = pose[b.parent.name] if b.parent else Matrix.Identity(4)
            a = parent_pose @ self.rest_rel[name]
            if name in orient:
                d = orient[name].to_matrix()
                rot = a.to_3x3().inverted() @ d
                loc = Vector((0, 0, 0))
                if name == "pelvis":
                    loc = a.to_3x3().inverted() @ (pelvis_pos - a.translation)
                bm = rot.to_4x4()
                bm.translation = loc
            else:
                bm = Matrix.Identity(4)
                rot = Matrix.Identity(3)
                loc = Vector((0, 0, 0))
            pose[name] = a @ bm
            result[name] = (rot.to_quaternion(), loc)
        return result, pose


# ---------------------------------------------------------------- clip cutting

def find_cycle(src, retargeter, min_period_s=0.55, max_period_s=1.6):
    """Left heel strikes: maxima of the left foot's forward position relative to the hips."""
    n = len(src.pos)
    travel = src.pos[n - 1]["Hips"] - src.pos[0]["Hips"]
    fwd = Vector((travel.x, travel.y, 0.0)).normalized()
    f = [(src.pos[i]["LeftFoot"] - src.pos[i]["Hips"]).dot(fwd) for i in range(n)]
    # smooth over 5 frames to skip jitter
    peaks = []
    for i in range(6, n - 6):
        if f[i] == max(f[i - 6:i + 7]) and f[i] > 0.0:
            if not peaks or i - peaks[-1] > min_period_s * src.fps * 0.8:
                peaks.append(i)
    pairs = [(a, b) for a, b in zip(peaks, peaks[1:]) if min_period_s * src.fps < b - a < max_period_s * src.fps]
    if not pairs:
        return None
    # the steadiest cycle: the one nearest the middle of the clip
    mid = n / 2
    a, b = min(pairs, key=lambda p: abs((p[0] + p[1]) / 2 - mid))
    return a, b, fwd


def slerp_list(qa, qb, t):
    return qa.slerp(qb, t)


def blend_loop(frames_orient, frames_pelvis, a, b, overlap):
    """Frames a..b-1 as a loop: the start cross-fades from frames b.. so that frame b-1 -> a is smooth."""
    n = b - a
    orient = []
    pelvis = []
    for i in range(n):
        o = {k: q.copy() for k, q in frames_orient[a + i].items()}
        p = frames_pelvis[a + i].copy()
        if i < overlap and b + i < len(frames_orient):
            w = i / overlap
            o2 = frames_orient[b + i]
            for k in o:
                o[k] = o2[k].slerp(o[k], w)
            p = frames_pelvis[b + i].lerp(p, w)
        orient.append(o)
        pelvis.append(p)
    return orient, pelvis


def walk_clip(src, retargeter, speed, fps_out=30, overlap_s=0.12, heading=Vector((0, -1, 0))):
    """One looping, in-place walk cycle whose ground speed is `speed` m/s.

    Returns (frames, info): frames is a list of {bone: (quaternion, location)}; info has the cycle
    duration, the step length and the foot slide.
    """
    found = find_cycle(src, retargeter)
    if not found:
        raise RuntimeError(f"no gait cycle in {src.path}")
    a, b, fwd = found
    overlap = int(overlap_s * src.fps)
    last = len(src.pos) - 1
    b_end = min(last, b + overlap)
    # align the walking direction with the rig's forward axis
    ang = math.atan2(fwd.y, fwd.x) - math.atan2(heading.y, heading.x)
    align = Matrix.Rotation(-ang, 3, "Z")
    orient_all = []
    pelvis_all = []
    for i in range(0, b_end + 1):
        o, p = retargeter.desired(src, i)
        o = {k: (align @ q.to_matrix()).to_quaternion() for k, q in o.items()}
        p = retargeter.pelvis_rest + align @ (p - retargeter.pelvis_rest)
        orient_all.append(o)
        pelvis_all.append(p)
    # in place: remove the forward travel and lateral drift linearly over the cycle
    start = Vector((pelvis_all[a].x, pelvis_all[a].y, 0.0))
    drift = pelvis_all[b] - pelvis_all[a]
    horizontal = Vector((drift.x, drift.y, 0.0))
    v_src = horizontal.length / ((b - a) / src.fps)
    for i in range(len(pelvis_all)):
        k = (i - a) / (b - a)
        pelvis_all[i] = pelvis_all[i] - start - horizontal * k
    # centre the cycle on the rig's origin, so the character's position is the middle of the step
    mean = sum((pelvis_all[i] for i in range(a, b)), Vector()) / (b - a)
    for i in range(len(pelvis_all)):
        pelvis_all[i] = pelvis_all[i] - Vector((mean.x, mean.y, 0.0))
    orient, pelvis = blend_loop(orient_all, pelvis_all, a, b, overlap)
    # the cross-fade starts at frame a; the cycle runs frames a..b-1
    period_src = (b - a) / src.fps
    def resample(period_out):
        n_out = max(4, round(period_out * fps_out))
        frames = []
        for j in range(n_out):
            s = (j / n_out) * (b - a)
            i0 = int(math.floor(s))
            w = s - i0
            i1 = (i0 + 1) % (b - a)
            o = {k: orient[i0][k].slerp(orient[i1][k], w) for k in orient[i0]}
            p = pelvis[i0].lerp(pelvis[i1], w)
            frames.append((o, p))
        return frames

    period_src = (b - a) / src.fps
    # time scale so that the pelvis travels at `speed`, then so that the planted feet do
    period_out = period_src * v_src / speed
    for _ in range(2):
        frames = resample(period_out)
        period_out *= stance_speed(retargeter, frames, fps_out) / speed
    frames = resample(period_out)
    n_out = len(frames)
    return frames, dict(period_s=n_out / fps_out, source_period_s=period_src, source_speed=v_src * retargeter.scale,
                        step_m=speed * (n_out / fps_out) / 2.0, cycle=(a, b), fps=fps_out)


def stance_speed(retargeter, frames, fps):
    """Mean speed (m/s) of a planted foot relative to the pelvis, over the cycle: what the ground speed must be."""
    n = len(frames)
    ball = {s: [] for s in "lr"}
    for o, p in frames:
        _, mats = retargeter.basis(o, p)
        for s in "lr":
            ball[s].append(mats[f"ball_{s}"].translation.copy())
    speeds = []
    for s in "lr":
        zmin = min(b.z for b in ball[s])
        for i in range(n):
            j = (i + 1) % n
            if ball[s][i].z < zmin + 0.02 and ball[s][j].z < zmin + 0.02:
                speeds.append((ball[s][j].y - ball[s][i].y) * fps)
    return sum(speeds) / len(speeds)


def mean_quaternion(qs):
    """The average orientation of a list of quaternions that are close to each other."""
    ref = qs[0]
    total = Quaternion((0, 0, 0, 0))
    for q in qs:
        total += q if ref.dot(q) >= 0 else -q
    return total.normalized()


def damp(orient, pelvis, amplitude, a, b):
    """Scale the motion of frames a..b-1 about its own mean pose by `amplitude` (1 keeps it, 0.5 halves
    every swing of every bone); returns new (orient, pelvis) lists for all frames given."""
    mean = {k: mean_quaternion([orient[i][k] for i in range(a, b)]) for k in orient[0]}
    mean_p = sum((pelvis[i] for i in range(a, b)), Vector()) / (b - a)
    damped = [{k: mean[k].slerp(q, amplitude) for k, q in o.items()} for o in orient]
    return damped, [mean_p + (p - mean_p) * amplitude for p in pelvis]


def clip_from_range(src, retargeter, a, b, fps_out=30, loop_overlap_s=0.5, rate=1.0, amplitude=1.0):
    """A non-locomotion clip (idle or gesture): frames a..b of the source, standing on the spot,
    the end cross-faded into the start so it loops. amplitude < 1 damps the motion (a drier gesture)."""
    overlap = int(loop_overlap_s * src.fps)
    b_end = min(len(src.pos) - 1, b + overlap)
    # face the rig's forward axis: the hips' facing on frame a
    hips_rot = src.rot[a]["Hips"] @ retargeter.ref_rot["pelvis"].inverted()
    hip_fwd = hips_rot @ Vector((0, -1, 0))
    hip_fwd.z = 0
    ang = math.atan2(hip_fwd.y, hip_fwd.x) - math.atan2(-1, 0)
    align = Matrix.Rotation(-ang, 3, "Z")
    orient_all, pelvis_all = [], []
    for i in range(a, b_end + 1):
        o, p = retargeter.desired(src, i)
        o = {k: (align @ q.to_matrix()).to_quaternion() for k, q in o.items()}
        p = retargeter.pelvis_rest + align @ (p - retargeter.pelvis_rest)
        orient_all.append(o)
        pelvis_all.append(p)
    if amplitude != 1.0:
        orient_all, pelvis_all = damp(orient_all, pelvis_all, amplitude, 0, b - a)
    mean = sum((pelvis_all[i] for i in range(0, b - a)), Vector()) / (b - a)
    pelvis_all = [p - Vector((mean.x - retargeter.pelvis_rest.x, mean.y - retargeter.pelvis_rest.y, 0.0)) for p in pelvis_all]
    orient, pelvis = blend_loop(orient_all, pelvis_all, 0, b - a, overlap)
    n = b - a
    n_out = max(4, round(n / src.fps / rate * fps_out))
    frames = []
    for j in range(n_out):
        s = (j / n_out) * n
        i0 = int(math.floor(s))
        w = s - i0
        i1 = (i0 + 1) % n
        o = {k: orient[i0][k].slerp(orient[i1][k], w) for k in orient[i0]}
        p = pelvis[i0].lerp(pelvis[i1], w)
        frames.append((o, p))
    return frames, dict(period_s=n_out / fps_out, fps=fps_out)


def ground_clip(retargeter, frames, rig):
    """Lower or raise the pelvis so the planted foot stands on the ground: the mean of the lower ankle,
    frame by frame, equals the rest pose's ankle height."""
    rest = retargeter.bones["foot_l"].head_local.z
    lows = []
    for o, p in frames:
        _, mats = retargeter.basis(o, p)
        lows.append(min(mats["foot_l"].translation.z, mats["foot_r"].translation.z))
    offset = sum(lows) / len(lows) - rest
    return [(o, p - Vector((0, 0, offset))) for o, p in frames]


def walk_metadata(retargeter, frames, meta):
    """Heel strike times, the standing-start phase and the foot slide of a baked walk cycle."""
    fps = meta["fps"]
    n = len(frames)
    ankle = {s: [] for s in "lr"}
    ball = {s: [] for s in "lr"}
    for o, p in frames:
        _, mats = retargeter.basis(o, p)
        for s in "lr":
            ankle[s].append(mats[f"foot_{s}"].translation.copy())
            ball[s].append(mats[f"ball_{s}"].translation.copy())
    strike = {s: min(range(n), key=lambda i: ankle[s][i].y) / fps for s in "lr"}
    # legs pass each other with the left foot planted and the right swinging through
    best = min((i for i in range(n) if ankle["r"][i].z > ankle["l"][i].z + 0.02),
               key=lambda i: abs(ankle["l"][i].y - ankle["r"][i].y), default=0)
    slides = []
    speed = meta["step_m"] * 2.0 / meta["period_s"]
    for s in "lr":
        zmin = min(b.z for b in ball[s])
        for i in range(n):
            j = (i + 1) % n
            if ball[s][i].z < zmin + 0.02 and ball[s][j].z < zmin + 0.02:
                slides.append(abs((ball[s][j].y - ball[s][i].y) * fps - speed))
    return dict(contacts=[strike["l"], strike["r"]], pass_phase_s=best / fps,
                slide_mean_cm_s=100 * sum(slides) / max(1, len(slides)), slide_max_cm_s=100 * max(slides, default=0.0))


def motion_energy(src, a, b, joints=("LeftHand", "RightHand", "Head", "LeftForeArm", "RightForeArm")):
    """Mean joint speed (m/s) in frames a..b, to find quiet or lively stretches."""
    total = 0.0
    for i in range(a + 1, b):
        for j in joints:
            total += (src.pos[i][j] - src.pos[i - 1][j]).length
    return total / ((b - a) / src.fps) / len(joints)


# ---------------------------------------------------------------- resting poses

BREATH_SHARE = {"spine_01": 0.3, "spine_02": 0.7, "spine_03": 1.0}


def lying_frame(src, retargeter, t, head_dir=Vector((0, -1, 0))):
    """One source pose (time t, in seconds), turned about Z so that the spine points along head_dir
    (horizontally): ({bone: Quaternion}, pelvis position)."""
    orient, pelvis = retargeter.desired(src, int(t * src.fps))
    _, pose = retargeter.basis(orient, pelvis)
    d = pose["head"].translation - pose["pelvis"].translation
    ang = math.atan2(d.y, d.x) - math.atan2(head_dir.y, head_dir.x)
    align = Matrix.Rotation(-ang, 3, "Z")
    orient = {k: (align @ q.to_matrix()).to_quaternion() for k, q in orient.items()}
    return orient, align @ pelvis


def twist(retargeter, orient, bone, euler_deg):
    """Turn a bone about its own axes (x, y, z in degrees), for a posed rest."""
    from mathutils import Euler
    m = orient[bone].to_matrix() @ Euler([math.radians(a) for a in euler_deg], "XYZ").to_matrix()
    orient[bone] = m.to_quaternion()


def rest_clip(src, retargeter, t, period_s=9.0, breaths=2, breath_deg=2.5, fps_out=30, head_dir=Vector((0, -1, 0)),
              tweaks=None):
    """A looping posed rest: one pose of the source clip at time t, held, with the chest breathing.

    Each breath raises the chest by turning the spine about its own lateral axis (spine_03 by
    breath_deg, the lower bones less) and lifts the shoulders a little; the breaths of one loop differ
    in depth by 15 %. tweaks {bone: (x, y, z) degrees} turn bones about their own axes first.
    Returns (frames, info) like clip_from_range."""
    orient, pelvis = lying_frame(src, retargeter, t, head_dir)
    for bone, euler in (tweaks or {}).items():
        twist(retargeter, orient, bone, euler)
    lateral = {}
    for bone in BREATH_SHARE:
        lateral[bone] = retargeter.rest[bone].to_3x3().inverted() @ Vector((1, 0, 0))
    n = max(4, round(period_s * fps_out))
    frames = []
    for j in range(n):
        phase = j / n * breaths
        depth = 1.0 - 0.15 * (math.floor(phase) % 2)
        w = depth * 0.5 * (1.0 - math.cos(2.0 * math.pi * phase))     # 0 at the end of an exhale, 1 at the top of an inhale
        o = {k: q.copy() for k, q in orient.items()}
        for bone, share in BREATH_SHARE.items():
            axis = o[bone].to_matrix() @ lateral[bone]
            turn = Matrix.Rotation(-math.radians(breath_deg * share * w), 3, axis)
            o[bone] = (turn @ o[bone].to_matrix()).to_quaternion()
        frames.append((o, pelvis.copy()))
    return frames, dict(period_s=n / fps_out, fps=fps_out)


def lying_ground(retargeter, rig, ground, frames):
    """Put a lying figure on the floor at the origin: z so that the lowest point of the bare body
    is 0, x and y so that the middle of its footprint is 0. The bare body (ground) is evaluated on
    the first frame."""
    make_action(rig, retargeter, "_probe", frames[:1])
    bpy.context.scene.frame_set(1)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ground.evaluated_get(dg)
    me = ev.to_mesh()
    pts = [ev.matrix_world @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    rig.animation_data.action = None
    bpy.data.actions.remove(bpy.data.actions["_probe"])
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    shift = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    return [(o, p - shift) for o, p in frames], dict(footprint_m=[hi.x - lo.x, hi.y - lo.y], height_m=hi.z - lo.z)


# ---------------------------------------------------------------- actions

def make_action(rig, retargeter, name, frames, fps=30):
    """Bake frames [(orient, pelvis_pos)] into a new action on the rig (rotation quaternion + pelvis location)."""
    action = bpy.data.actions.new(name)
    rig.animation_data_create()
    rig.animation_data.action = action
    for bone in rig.pose.bones:
        bone.rotation_mode = "QUATERNION"
    scene = bpy.context.scene
    scene.render.fps = fps
    previous = {}
    for j, (orient, pelvis_pos) in enumerate(frames):
        pose, _ = retargeter.basis(orient, pelvis_pos)
        for bone_name, (q, loc) in pose.items():
            pb = rig.pose.bones[bone_name]
            if bone_name in previous and previous[bone_name].dot(q) < 0.0:
                q = -q
            previous[bone_name] = q.copy()
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=j + 1)
            if bone_name == "pelvis":
                pb.location = loc
                pb.keyframe_insert("location", frame=j + 1)
    action.use_fake_user = True
    action.use_frame_range = True
    action.frame_start = 1
    action.frame_end = len(frames)
    action.use_cyclic = True
    return action

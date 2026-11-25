"""Crow motion for anim.py: perched crows idle, one crow circles the yard, one crosses it.

Perched crows (`prop_crow#...`): setup() puts the head and bill, each wing and the tail under
pivot empties, so they can turn without rebuilding the bird. Each crow has its own schedule of
events, drawn once from its seed over HORIZON seconds:

- head: snaps to a new direction every 0.4-3.5 s (crows turn their heads in quick jerks and then
  hold still), mostly within 55 degrees of straight ahead, with a little pitch; crows on the
  ground also peck;
- hop: every 6-20 s or so a short hop, 6-8 cm high, that often turns the bird on its perch;
- shuffle: now and then the wings lift off the body and settle again, with the body fluffed up;
- tail flick: a quick flick up and down every few seconds.

Flying crows: the plan's static `crow_flying` birds are hidden and replaced by animated ones
built here from the parts of assets/crow_flying.py. Each has its wings built at WING_PHASES
points of the wingbeat, from the up-stroke to the down-stroke; a frame shows the one nearest the
beat phase. A crow beats about 3.5-4.5 times a second, so at 24 fps a beat spans 5-7 frames.

- The circler rides a loose, wandering circle over the yard at about 10 m, banking into the
  turn, with bursts of flapping between glides.
- The crosser is the crow on the gallows beam (CROSSER): it takes off, flies over the yard to a
  merlon on the west curtain, sits there, and flies back, on a CROSS_PERIOD-second cycle. While
  it flies, the perched bird is hidden; it reappears where the flier lands, facing the way it
  came in, and turns back to its old heading at home.
"""

import bisect
import math
import random

import numpy as np

HORIZON = 1200.0            # seconds of idle events drawn per crow
WING_PHASES = 7
CROSSER = "crow#p1"          # perched crow that crosses the yard (on the gallows beam)
CROSS_TO = (-12.1, -3.0)     # it lands on the merlon top nearest to this point
CROSS_PERIOD = 24.0
# (start, end) of the two flights in each period: out to the wall and home
CROSS_FLIGHTS = ((3.5, 7.7), (15.0, 19.4))
CIRCLE = dict(center=(0.5, -4.0), radius=5.5, height=10.5, period=9.0)   # clear of the towers (11 m) and the gatehouse
GRAVITY = 9.81
MAX_BANK = math.radians(35.0)


def _smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def _pulse(events, t, dur):
    """sin-shaped 0..1..0 envelope of the latest event (start, ...) within `dur` before t; and the event."""
    i = bisect.bisect_right(events, (t, math.inf)) - 1
    if i < 0:
        return 0.0, None
    e = events[i]
    u = (t - e[0]) / dur
    if u >= 1.0:
        return 0.0, e
    return math.sin(math.pi * u), e


def _base(name):
    return name.split(".")[0]


# ---------- perched ----------

def _local_verts(ob):
    """Vertices of a part in its parent's space."""
    me = ob.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    m = np.array(ob.matrix_parent_inverse @ ob.matrix_basis, np.float32)
    return co.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]


def _pivot(root, name, point, parts):
    """Empty at root-space `point`, parent of `parts`, which keep their place."""
    import bpy
    from mathutils import Matrix, Vector
    piv = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(piv)
    piv.parent = root
    piv.location = point
    shift = Matrix.Translation(-Vector(point))
    for ob in parts:
        local = ob.matrix_parent_inverse @ ob.matrix_basis
        ob.parent = piv
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.matrix_basis = shift @ local
    return piv


class Perched:
    def __init__(self, root, seed):
        self.root = root
        self.loc0 = tuple(root.location)
        self.yaw0 = root.rotation_euler.z
        self.scale = root.scale[0]
        self.ground = self.loc0[2] < 0.1
        self.home = (self.loc0, self.yaw0)
        self.override = None        # (loc, yaw) while the crosser sits somewhere else
        self.hops_on = True
        parts = {}
        for ob in root.children:
            parts.setdefault(_base(ob.name), []).append(ob)
        self.meshes = [ob for ob in root.children_recursive if ob.type == "MESH"]

        head = [ob for n in ("head", "throat", "beak_upper", "beak_lower") for ob in parts.get(n, [])]
        self.head = _pivot(root, f"{root.name}_head", tuple(parts["head"][0].location), head) if head else None
        self.wings = []
        for side, sx in (("r", 1), ("l", -1)):
            obs = [ob for n in (f"wing_{side}", f"feathers_{side}", f"arm_{side}", f"hand_{side}")
                   for ob in parts.get(n, [])]
            if not obs:
                continue
            v = np.concatenate([_local_verts(ob) for ob in obs])
            near = v[np.argsort(np.abs(v[:, 0]))[:24]]          # where the wing meets the body
            self.wings.append((_pivot(root, f"{root.name}_wing_{side}", tuple(near.mean(0)), obs), sx))
        tail = parts.get("tail", [])
        if tail:
            v = _local_verts(tail[0])
            base = v[np.argsort(v[:, 1])[:16]].mean(0)
            self.tail = _pivot(root, f"{root.name}_tail", tuple(base), tail)
        else:
            self.tail = None
        self.body = parts.get("body", [None])[0]
        self.body_scale = tuple(self.body.scale) if self.body else None
        self._schedule(random.Random(seed))

    def _schedule(self, rng):
        t, keys = 0.0, [(-1.0, 0.0, 0.0)]
        while t < HORIZON:
            t += rng.uniform(0.4, 3.5)
            if rng.random() < 0.25:
                keys.append((t, 0.0, rng.uniform(-4, 6)))
            else:
                keys.append((t, rng.uniform(-55, 55), rng.uniform(-8, 14)))
            if self.ground and rng.random() < 0.3:          # peck: down and back up
                keys.append((t + 0.25, keys[-1][1], 48.0))
                keys.append((t + 0.55, keys[-1][1], 5.0))
                t += 0.6
        self.head_keys = keys
        self.head_times = [k[0] for k in keys]

        def events(mean, lo, make):
            out, t = [], rng.uniform(0, mean)
            while t < HORIZON:
                out.append((t, *make()))
                t += max(lo, rng.expovariate(1.0 / mean))
            return out

        self.hops = events(11.0, 5.0, lambda: (rng.choice((0.0, 1, -1)) * rng.uniform(25, 150),))
        turns = np.cumsum([0.0] + [h[1] for h in self.hops])
        self.hop_turns = turns
        self.shuffles = events(9.0, 3.0, lambda: (rng.uniform(14, 30),))
        self.flicks = events(4.5, 1.2, lambda: (rng.uniform(8, 18),))

    def head_angles(self, t):
        i = bisect.bisect_right(self.head_times, t) - 1
        t0, y1, p1 = self.head_keys[i]
        _, y0, p0 = self.head_keys[i - 1] if i > 0 else self.head_keys[0]
        u = _smooth((t - t0) / 0.13)
        return y0 + (y1 - y0) * u, p0 + (p1 - p0) * u

    def apply(self, t):
        loc, yaw = self.override or self.home
        z, turn, lift = 0.0, 0.0, 0.0
        if self.hops_on:
            HOP = 0.34
            i = bisect.bisect_right(self.hops, (t, math.inf)) - 1
            if i >= 0:
                u = (t - self.hops[i][0]) / HOP
                turn = self.hop_turns[i] + self.hops[i][1] * _smooth(u * 1.2)
                if u < 1.0:
                    z = 0.07 * self.scale * math.sin(math.pi * u)
                    lift = 30.0 * math.sin(math.pi * u)
                else:
                    turn = self.hop_turns[i + 1]
        self.root.location = (loc[0], loc[1], loc[2] + z)
        self.root.rotation_euler.z = yaw + math.radians(turn)

        if self.head:
            hy, hp = self.head_angles(t)
            self.head.rotation_euler = (math.radians(hp), 0.0, math.radians(hy))
        env, e = _pulse(self.shuffles, t, 0.55)
        amp = (e[1] if e else 0.0) * env
        flap = max(lift, amp)
        for piv, sx in self.wings:
            piv.rotation_euler = (math.radians(0.3 * flap), math.radians(-sx * 0.5 * flap),
                                  math.radians(-sx * flap))
        if self.body is not None:
            f = 1.0 + 0.10 * env
            self.body.scale = tuple(s * f for s in self.body_scale)
        if self.tail:
            env2, e2 = _pulse(self.flicks, t, 0.28)
            self.tail.rotation_euler = (math.radians((e2[1] if e2 else 0.0) * env2 + 0.3 * flap), 0.0, 0.0)

    def show(self, on):
        for ob in self.meshes:
            ob.hide_render = not on


# ---------- flying ----------

class _Mats:
    def __getitem__(self, key):
        import bpy
        return bpy.data.materials[key]


def _lerp_pose(a, b, u):
    return {k: a[k] + (b[k] - a[k]) * u for k in a}


def build_flier(name, seed):
    """A flying crow whose wings exist at WING_PHASES beat phases; returns (root, wing mesh lists)."""
    import kit
    from assets import crow_flying as cf
    rng = random.Random(seed)
    mats = _Mats()
    bird = mats["feather"]
    root = kit.group(name)
    k = rng.uniform(1.05, 1.2)
    tf = cf.make_tf(0.0, (0.0, 0.0, 0.0), k, 0.0)
    cf.sweep(kit, "body", [tf((0.0, y, cz)) for y, cz, _, _ in cf.BODY], [r * k for _, _, r, _ in cf.BODY],
             [r * k for _, _, _, r in cf.BODY], bird, root, sides=14)
    cf.head_and_beak(kit, bird, root, tf, k, 0.0, (0.0, -0.168, 0.016), rng.uniform(-9, 9), rng.uniform(4, 12),
                     neck_from=(0.0, -0.10, 0.012), via=(0.0, -0.135, 0.014))
    cf.tail_fan(kit, bird, root, tf, count=7, step_deg=7.5, length=0.21, base=(0.0, 0.12, -0.014),
                lift=-4.0, width=0.036)
    for sx in (1, -1):
        leg = [tf((sx * 0.032, 0.040, -0.045)), tf((sx * 0.030, 0.085, -0.040)), tf((sx * 0.028, 0.130, -0.030))]
        cf.sweep(kit, f"leg_{'r' if sx > 0 else 'l'}", leg, [0.0075 * k, 0.0065 * k, 0.0050 * k],
                 mat=bird, parent=root, sides=6, step=0.02)
    offs = [(rng.uniform(-4, 4), rng.uniform(-4, 4)) for _ in (1, -1)]
    phases = []
    for j in range(WING_PHASES):
        u = j / (WING_PHASES - 1)          # 0 top of the up-stroke, 1 bottom of the down-stroke
        P = cf.POSES
        pose = _lerp_pose(P["up"], P["glide"], u * 2) if u < 0.5 else _lerp_pose(P["glide"], P["down"], u * 2 - 1)
        grp = kit.group(f"{name}_wings_{j}", parent=root)
        wr = random.Random(seed + 1)
        for (sx, (ao, ho)) in zip((1, -1), offs):
            cf._wing(kit, bird, grp, tf, cf.Wing(sx, pose, ao, ho), pose, wr, "r" if sx > 0 else "l")
        phases.append(list(grp.children))
    body = [ob for ob in root.children if ob.type == "MESH"]
    return root, body, phases


def _orient(fwd, acc):
    """World rotation matrix of a bird whose head (-Y) points along fwd, banked by the lateral acceleration."""
    from mathutils import Matrix, Vector
    f = Vector(fwd).normalized()
    y = -f
    a = Vector(acc)
    a.z = 0.0
    a -= f * a.dot(f)
    if a.length > GRAVITY * math.tan(MAX_BANK):
        a *= GRAVITY * math.tan(MAX_BANK) / a.length
    up = Vector((0.0, 0.0, GRAVITY)) + a
    z = (up - y * up.dot(y)).normalized()
    x = y.cross(z)
    return Matrix((x, y, z)).transposed()


class Flier:
    def __init__(self, name, seed):
        self.root, self.body, self.phases = build_flier(name, seed)
        self.seed = seed
        self.visible = None
        self.shown = None

    def pose(self, pos, fwd, acc, wing_u, pitch=0.0):
        from mathutils import Matrix
        m = _orient(fwd, acc)
        if pitch:
            m = m @ Matrix.Rotation(math.radians(pitch), 3, "X")
        self.root.matrix_world = Matrix.Translation(pos) @ m.to_4x4()
        j = int(round(min(max(wing_u, 0.0), 1.0) * (WING_PHASES - 1)))
        if j != self.shown or not self.visible:
            for i, obs in enumerate(self.phases):
                for ob in obs:
                    ob.hide_render = not (self.visible and i == j)
            self.shown = j

    def show(self, on):
        if on == self.visible:
            return
        self.visible = on
        for ob in self.body:
            ob.hide_render = not on
        self.shown = None
        if not on:
            for obs in self.phases:
                for ob in obs:
                    ob.hide_render = True


def wingbeat(t, freq, seed):
    """Beat phase 0 (up) .. 1 (down) for steady flapping at freq Hz, with a little irregularity."""
    from anim import noise
    ph = freq * t + 0.15 * noise(t * 0.7, seed)
    return 0.5 - 0.5 * math.cos(2 * math.pi * ph)


def glide_wings(t, seed):
    from anim import noise
    return 0.42 + 0.05 * noise(t * 1.8, seed)


def _diff(path, t, h=1 / 48):
    p0, p1, p2 = path(t - h), path(t), path(t + h)
    vel = [(b - a) / (2 * h) for a, b in zip(p0, p2)]
    acc = [(a - 2 * m + b) / (h * h) for a, m, b in zip(p0, p1, p2)]
    return p1, vel, acc


def circle_path(t, seed=7):
    """Position of the circling crow at time t: a loose circle that wanders in radius, speed and height."""
    from anim import fbm, noise
    c = CIRCLE
    th = 2 * math.pi * t / c["period"] + 0.5 * noise(t * 0.09, seed)
    r = c["radius"] * (1.0 + 0.18 * noise(t * 0.07, seed + 1))
    z = c["height"] + 0.9 * fbm(t * 0.11, seed + 2, 2)
    return (c["center"][0] + r * math.cos(th), c["center"][1] + r * math.sin(th), z)


class Circler:
    def __init__(self, seed=7):
        self.seed = seed
        self.flier = Flier("anim_crow_circler", seed)
        self.flier.show(True)

    def apply(self, t):
        from anim import fbm
        from mathutils import Vector
        pos, vel, acc = _diff(lambda x: circle_path(x, self.seed), t)
        flapping = fbm(t * 0.3, self.seed + 5, 2) > -0.1
        u = wingbeat(t, 3.8, self.seed) if flapping else glide_wings(t, self.seed)
        bob = 0.03 * math.cos(2 * math.pi * 3.8 * t) if flapping else 0.0
        self.flier.pose(Vector(pos) + Vector((0, 0, bob)), vel, acc, u)


class Crosser:
    """The perched crow that flies over the yard to a wall merlon and back."""

    def __init__(self, perched, perches, occupied, seed=11):
        from mathutils import Vector
        self.perched = perched
        self.perched.hops_on = False
        self.seed = seed
        a_loc, a_yaw = perched.home
        cands = [p for p in perches if p[2] > 5.0 and all(math.dist(p[:2], o[:2]) > 1.2 for o in occupied)]
        if not cands:
            raise ValueError("no free perch to land on")
        b = min(cands, key=lambda p: math.dist(p[:2], CROSS_TO))
        self.a = Vector(a_loc)
        self.b = Vector(b[:3])
        self.a_yaw = a_yaw
        self.lift = 0.19 * perched.scale         # body centre above the feet
        self.flier = Flier("anim_crow_crosser", seed)
        self.flier.show(False)
        d = self.b - self.a
        d.z = 0
        L = d.length
        d.normalize()
        side = Vector((-d.y, d.x, 0.0))
        up = Vector((0, 0, 1))
        self.out = [self.a + up * self.lift, self.a + up * (self.lift + 2.2) + d * 0.25 * L + side * 0.18 * L,
                    self.b + up * (self.lift + 2.6) - d * 0.30 * L + side * 0.18 * L, self.b + up * self.lift]
        # home: a different arc, on the other side
        self.back = [self.out[3], self.b + up * (self.lift + 2.0) - d * 0.25 * L - side * 0.22 * L,
                     self.a + up * (self.lift + 2.6) + d * 0.30 * L - side * 0.22 * L, self.out[0]]

    @staticmethod
    def _bez(P, s):
        u = 1 - s
        return P[0] * u ** 3 + P[1] * 3 * u * u * s + P[2] * 3 * u * s * s + P[3] * s ** 3

    @staticmethod
    def _bez_d(P, s):
        u = 1 - s
        return (P[1] - P[0]) * 3 * u * u + (P[2] - P[1]) * 6 * u * s + (P[3] - P[2]) * 3 * s * s

    def heading_yaw(self, P):
        d = self._bez_d(P, 1.0)
        return math.atan2(d.x, -d.y)

    def _flight(self, t):
        """(curve, u in 0..1) when flying, else None."""
        tc = t % CROSS_PERIOD
        for P, (t0, t1) in zip((self.out, self.back), CROSS_FLIGHTS):
            if t0 <= tc < t1:
                return P, (tc - t0) / (t1 - t0), t - tc + t0, t1 - t0
        return None

    def apply(self, t):
        from mathutils import Vector
        tc = t % CROSS_PERIOD
        fl = self._flight(t)
        if fl is None:
            self.flier.show(False)
            self.perched.show(True)
            (o0, o1), (h0, h1) = CROSS_FLIGHTS
            if o1 <= tc < h0:
                self.perched.override = (tuple(self.b), self.heading_yaw(self.out))
            else:
                # home again: lands facing the way it came, then turns back to its old heading
                arrive = self.heading_yaw(self.back)
                since = tc - h1 if tc >= h1 else tc + CROSS_PERIOD - h1
                k = _smooth((since - 1.0) / 0.35)
                d = (self.a_yaw - arrive + math.pi) % (2 * math.pi) - math.pi
                self.perched.override = (tuple(self.a), arrive + d * k)
            self.perched.apply(t)
            return
        P, u, t0, dur = fl
        self.perched.show(False)
        self.flier.show(True)

        def ease(uu):
            # half linear, half smoothstep: it leaves and lands at half the mean speed, not from rest
            uu = min(max(uu, 0.0), 1.0)
            return 0.5 * (uu + uu * uu * (3 - 2 * uu))

        def path(x):
            return tuple(self._bez(P, ease((x - t0) / dur)))

        pos, vel, acc = _diff(path, t)
        tangent = self._bez_d(P, ease(u))
        h = math.hypot(tangent.x, tangent.y)
        climb = max(-25.0, min(30.0, math.degrees(math.atan2(tangent.z, h))))
        fwd = Vector((tangent.x, tangent.y, 0.0)).normalized()
        # nose follows the climb on take-off; on the last stretch it flares up to land
        flare = _smooth((u - 0.78) / 0.2)
        nose_up = climb * (1 - flare) + 25.0 * flare
        if u < 0.35:
            wu = wingbeat(t, 4.6, self.seed)
        elif u < 0.72:
            wu = glide_wings(t, self.seed)
        else:
            wu = wingbeat(t, 4.2, self.seed) * (1 - 0.5 * flare)
        self.flier.pose(Vector(pos), fwd, acc, wu, pitch=-nose_up)


class Crows:
    def __init__(self):
        self.perched, self.fliers, self.hidden = [], [], []
        self.crosser = None

    def summary(self):
        return dict(perched_crows=len(self.perched), flying_crows=len(self.fliers) + bool(self.crosser))

    def apply(self, t):
        for p in self.perched:
            if self.crosser is None or p is not self.crosser.perched:
                p.apply(t)
        for f in self.fliers:
            f.apply(t)
        if self.crosser:
            self.crosser.apply(t)


def setup(objects, perches):
    from anim import seed_of
    crows = Crows()
    for root in objects:
        if not root.name.startswith("prop_") or root.parent is not None:
            continue
        key = root.name[len("prop_"):]
        base = key.split("#")[0]
        if base == "crow":
            crows.perched.append(Perched(root, seed_of(key)))
        elif base == "crow_flying":
            for ob in [root] + list(root.children_recursive):
                ob.hide_render = True
            crows.hidden.append(root)
    if crows.perched or crows.hidden:       # a place with no crows has no circling one either
        crows.fliers.append(Circler())
    home = next((p for p in crows.perched if p.root.name == f"prop_{CROSSER}"), None)
    if home and perches:
        occupied = [p.loc0 for p in crows.perched]
        crows.crosser = Crosser(home, perches, occupied)
    return crows

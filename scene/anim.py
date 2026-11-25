"""Ambient motion of the courtyard as deterministic functions of time.

    import anim
    anim.setup(perches=build_scene.PERCHES)   # once, after build_scene has built the scene
    anim.apply(t)                              # before each frame; t in seconds

`setup` finds the moving parts by name and material in the built scene and records their rest
state. `apply(t)` sets every animated value from `t` alone, so any frame can be rendered on its
own, in any order, and the same functions can bake loops for a real-time engine. Nothing here is
simulated and nothing reads the previous frame.

`setup` changes the scene: it adds a per-object glow factor to the `fire` and `embers` materials,
a flicker factor to each lit window's room material, an attribute pivot to crow parts and the
animated flying crows. Scenes that never call it, such as the Cycles main still of
build_scene.py, stay as they are.

What moves:

- Fire (brazier, cookhouse hearth and oven, passage torch, lanterns): every flame tongue
  stretches, narrows, leans and twists with its own noise on top of the fire's shared intensity;
  the fire's lights follow that intensity in energy and move a few cm; the tongues' emission and
  the coals' glow follow it too. Embers rise on a loop and cool as they go.
- Light from inside (lit windows, lit doors): a fire in the room behind, so a gentle, slower
  flicker of the room glow, the lamp flame and the spill lights, each opening with its own phase.
- Banked forge: no flicker; the coals and their light breathe slowly.
- Smoke plumes thicken and thin with their fire (the plume shader itself drifts with scene time).
- Trees, the tree line and dead scrub outside the walls sway in a gusty wind toward +X, the
  twigs more than the limbs, the trunks hardly at all (see `wind_offsets`).
- Crows: see anim_crows.py.

All noise is value noise on a hashed integer lattice (`noise`, `fbm`): smooth, not periodic,
and the same on every machine.
"""

import math
import re

import numpy as np

import anim_crows

WIND_YAW = 12.0           # deg counter-clockwise from +X, as assets/_fire.WIND_YAW
WIND_DIR = (math.cos(math.radians(WIND_YAW)), math.sin(math.radians(WIND_YAW)), 0.0)
GLOW_ATTR = "anim_glow"   # object custom property that scales the emission of fire and embers

# which flicker a prop's fire gets; props with flames that are not listed burn as an open fire
KINDS = {"lit_window": "interior", "lit_door": "interior", "forge": "banked",
         "lantern": "lamp", "lantern_standing": "lamp", "lantern_hanging": "lamp", "west_ditch": "lamp",
         "tower_desk": "lamp", "tower_shrine": "lamp"}
TREES = {"tree": dict(amp=0.10, flutter=0.045), "treeline": dict(amp=0.16, flutter=0.06),
         "dead_bush": dict(amp=0.05, flutter=0.03)}

_STATE = None


# ---------- noise ----------

def _hash(i, seed):
    """Deterministic pseudo-random value in [-1, 1] for integer lattice point i."""
    h = (i * 374761393 + seed * 668265263 + 0x9E3779B9) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 2147483647.5 - 1.0


def noise(x, seed=0):
    """Smooth 1D value noise in [-1, 1], one random value per unit, quintic between them."""
    i = math.floor(x)
    f = x - i
    u = f * f * f * (f * (f * 6 - 15) + 10)
    a, b = _hash(i, seed), _hash(i + 1, seed)
    return a + (b - a) * u


def fbm(x, seed=0, octaves=3, lacunarity=2.13, gain=0.5):
    """Sum of `octaves` noise layers, each faster and weaker; about [-1, 1]."""
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total += amp * noise(x * lacunarity ** o + 17.3 * o, seed + 101 * o)
        norm += amp
        amp *= gain
    return total / norm


def seed_of(text):
    """Stable integer seed from a name (Python's hash() changes per process)."""
    h = 2166136261
    for c in text.encode():
        h = ((h ^ c) * 16777619) & 0xFFFFFFFF
    return h & 0xFFFFFF


# ---------- light curves ----------

def fire_intensity(t, seed):
    """Open fire: fast, irregular flicker around 1 with slow swells and short dips (about 0.6-1.35)."""
    v = 1.0 + 0.17 * fbm(t * 2.3, seed, 3) + 0.09 * noise(t * 0.37, seed + 7)
    dip = max(0.0, noise(t * 0.9, seed + 13) - 0.55) * 0.55      # a gust smothers it for a moment
    return max(0.5, v - dip)


def interior_intensity(t, seed):
    """Firelight in a room seen through an opening: softer and slower than an open fire."""
    return 1.0 + 0.11 * fbm(t * 1.5, seed, 3) + 0.06 * noise(t * 0.29, seed + 5)


def lamp_intensity(t, seed):
    """Candle or oil lamp: nearly steady, with a rare gutter."""
    gutter = max(0.0, noise(t * 0.7, seed + 3) - 0.7) * 0.6
    return 1.0 + 0.05 * fbm(t * 2.0, seed, 3) - gutter


def banked_intensity(t, seed):
    """Banked forge: no flame, the coals breathe as the draught comes and goes (periods of 3-8 s)."""
    return 1.0 + 0.22 * fbm(t * 0.22, seed, 2) + 0.03 * noise(t * 1.1, seed + 9)


CURVES = {"fire": fire_intensity, "interior": interior_intensity, "lamp": lamp_intensity,
          "banked": banked_intensity}


def gust(t, seed=0):
    """Wind strength 0..1: long lulls, gusts of a few seconds."""
    g = 0.45 + 0.65 * fbm(t * 0.17, seed + 401, 3) + 0.2 * noise(t * 0.6, seed + 409)
    return min(1.0, max(0.0, g)) ** 1.5


# ---------- scene helpers ----------

def _base(name):
    return name.split(".")[0]


def _mat_names(ob):
    return {s.material.name for s in ob.material_slots if s.material} if ob.type == "MESH" else set()


def _uses(ob, mat):
    return any(_base(n) == mat for n in _mat_names(ob))


def _scale_emission(mat):
    """Multiply the material's emission strength by the object's GLOW_ATTR property."""
    nt = mat.node_tree
    if nt.nodes.get("anim_glow"):
        return
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return
    sock = bsdf.inputs["Emission Strength"]
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.name = "anim_glow"
    attr.attribute_type = "OBJECT"
    attr.attribute_name = f'["{GLOW_ATTR}"]'
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    if sock.is_linked:
        nt.links.new(sock.links[0].from_socket, mul.inputs[0])
    else:
        mul.inputs[0].default_value = sock.default_value
    nt.links.new(attr.outputs["Fac"], mul.inputs[1])
    nt.links.new(mul.outputs[0], sock)


def _flicker_value(mat):
    """Value node that scales the Emission shader's strength of a lit window's room material."""
    nt = mat.node_tree
    node = nt.nodes.get("anim_flicker")
    if node:
        return node
    emit = next(n for n in nt.nodes if n.type == "EMISSION")
    sock = emit.inputs["Strength"]
    node = nt.nodes.new("ShaderNodeValue")
    node.name = "anim_flicker"
    node.outputs[0].default_value = 1.0
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    if sock.is_linked:
        nt.links.new(sock.links[0].from_socket, mul.inputs[0])
    else:
        mul.inputs[0].default_value = sock.default_value
    nt.links.new(node.outputs[0], mul.inputs[1])
    nt.links.new(mul.outputs[0], sock)
    return node


def _set_glow(ob, value):
    ob[GLOW_ATTR] = value
    ob.update_tag()


# ---------- fire ----------

class Flame:
    """A flame tongue: origin at its base; stretches, narrows, leans and twists."""

    def __init__(self, ob, seed, scaled):
        self.ob, self.seed, self.scaled = ob, seed, scaled
        self.scale0 = tuple(ob.scale)
        self.rot0 = tuple(ob.rotation_euler)

    def apply(self, t, level, gain):
        s, ob = self.seed, self.ob
        own = fbm(t * 2.7, s, 2)
        if self.scaled:
            h = 1.0 + gain * (0.75 * (level - 1.0) + 0.20 * own)
            w = 1.0 - 0.45 * (h - 1.0) + gain * 0.05 * noise(t * 4.3, s + 3)
            ob.scale = (self.scale0[0] * w, self.scale0[1] * w, self.scale0[2] * max(0.3, h))
            lean = math.radians(5.0) * gain
            ob.rotation_euler = (self.rot0[0] + lean * fbm(t * 1.7, s + 5, 2),
                                 self.rot0[1] + lean * (0.6 * fbm(t * 1.3, s + 6, 2) + 0.4 * gust(t)),
                                 self.rot0[2] + math.radians(14.0) * gain * fbm(t * 1.1, s + 8, 2))
        _set_glow(ob, max(0.2, 1.0 + gain * (0.6 * (level - 1.0) + 0.15 * own)))


class Sparks:
    """Embers that rise from the emitter and drift downwind on a loop, cooling as they rise.

    Each flake of the static mesh (6 vertices, from assets/_fire.sparks) keeps its shape and its
    place in the loop: its starting height fraction is its phase, so t = 0 is the built layout.
    """

    def __init__(self, ob, wind=(0.9, 0.2), speed=1.0):
        me = ob.data
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 6, 3)
        heat = np.empty(len(me.vertices), np.float32)
        me.attributes["spark"].data.foreach_get("value", heat)
        self.ob, self.me = ob, me
        self.center = co.mean(axis=1)
        self.shape = co - self.center[:, None, :]
        self.height = max(0.2, float(self.center[:, 2].max()) * 1.05)
        self.phase = np.clip(self.center[:, 2] / self.height, 0.0, 0.999)
        self.wind = np.array([*wind, 0.0], np.float32)
        drift = self.wind[None, :] * (self.phase ** 1.4)[:, None] * self.height
        self.spread = (self.center - drift)[:, :2] / (0.3 + self.phase)[:, None]
        self.hot = heat.reshape(-1, 6)[:, 0] / np.maximum((1.0 - self.phase) ** 1.1, 1e-3)
        self.life = self.height / speed

    def apply(self, t):
        a = (self.phase + t / self.life) % 1.0
        wob = 0.03 * np.sin(7.0 * a + 13.0 * self.phase)
        c = np.empty_like(self.center)
        c[:, :2] = self.spread * (0.3 + a)[:, None] + self.wind[None, :2] * (a ** 1.4)[:, None] * self.height
        c[:, 0] += wob
        c[:, 2] = a * self.height
        size = np.clip((1.0 - 0.45 * a) / (1.0 - 0.45 * self.phase), 0.0, 2.0)
        size *= np.clip((1.0 - a) / 0.1, 0.0, 1.0)          # vanish just before the wrap
        co = c[:, None, :] + self.shape * size[:, None, None]
        self.me.vertices.foreach_set("co", co.astype(np.float32).ravel())
        heat = np.clip(self.hot * (1.0 - a) ** 1.1, 0.002, 1.0)
        self.me.attributes["spark"].data.foreach_set("value", np.repeat(heat, 6).astype(np.float32))
        self.me.update()


class Source:
    """One fire: its flame tongues, coals, lights and smoke share one intensity curve."""

    def __init__(self, kind, seed):
        self.kind, self.seed = kind, seed
        self.flames, self.coals, self.lights, self.smoke, self.rooms = [], [], [], [], []

    def level(self, t):
        return CURVES[self.kind](t, self.seed)

    def apply(self, t):
        lv = self.level(t)
        gain = {"fire": 1.0, "interior": 0.6, "lamp": 0.5, "banked": 0.0}[self.kind]
        for fl in self.flames:
            fl.apply(t, lv, gain)
        # coals answer the flames a moment later and more softly
        slow = self.level(t - 0.15)
        for ob in self.coals:
            k = 1.6 if self.kind == "banked" else 0.5
            _set_glow(ob, max(0.2, 1.0 + k * (slow - 1.0)))
        jig = {"fire": 0.035, "interior": 0.0, "lamp": 0.008, "banked": 0.0}[self.kind]
        for i, (li, e0, loc0) in enumerate(self.lights):
            li.data.energy = e0 * lv ** 1.3
            if jig:
                s = self.seed + 31 * i
                li.location = (loc0[0] + jig * fbm(t * 2.0, s + 1, 2), loc0[1] + jig * fbm(t * 2.0, s + 2, 2),
                               loc0[2] + jig * (0.5 * fbm(t * 2.5, s + 3, 2) + 1.2 * (lv - 1.0)))
        for node in self.rooms:
            node.outputs[0].default_value = lv
        for ob, d0 in self.smoke:
            ob["density"] = d0 * (1.0 + 0.25 * fbm(t * 0.4, self.seed + 77, 2) + 0.3 * (lv - 1.0))
            ob.update_tag()


def _cluster(points, gap):
    """Single-linkage groups of point indices closer than `gap`."""
    groups = []
    for i, p in enumerate(points):
        hits = [g for g in groups if any((points[j] - p).length < gap for j in g)]
        merged = [i] + [j for g in hits for j in g]
        groups = [g for g in groups if g not in hits] + [merged]
    return groups


def _setup_fires(objects):
    import bpy
    from mathutils import Vector

    for name in ("fire", "embers"):
        mat = bpy.data.materials.get(name)
        if mat:
            _scale_emission(mat)
            for ob in objects:
                if _uses(ob, name):
                    ob[GLOW_ATTR] = 1.0

    sources, sparks = [], []
    roots = [ob for ob in objects if ob.name.startswith("prop_") and ob.parent is None]
    loose_lights = [ob for ob in objects if ob.type == "LIGHT" and ob.parent is None]
    for root in roots:
        key = root.name[len("prop_"):]
        kind = KINDS.get(key.split("#")[0], "fire")
        desc = root.children_recursive
        pat = re.compile(rf"light_{re.escape(key)}_\d+$")
        lights = [o for o in desc if o.type == "LIGHT"] + [o for o in loose_lights if pat.match(o.name)]
        flames = [o for o in desc if _uses(o, "fire")]
        embers = [o for o in desc if _uses(o, "embers")]
        spark_obs = [o for o in embers if "spark" in o.data.attributes]
        coals = [o for o in embers if o not in spark_obs]
        smoke = [o for o in desc if _uses(o, "smoke") and "density" in o]
        rooms = [s.material for o in desc if o.type == "MESH" for s in o.material_slots
                 if s.material and _base(s.material.name) == "window_room"]
        sparks += [Sparks(o) for o in spark_obs]
        if not (flames or (kind in ("interior", "banked") and lights)):
            continue

        tongues = [o for o in flames if "flame" in _base(o.name) or _base(o.name).startswith(("inner_", "lick_"))]
        bases = [o.matrix_world.translation.copy() for o in tongues]
        groups = _cluster(bases, 0.7) if tongues else [[]]
        local = []
        for g, idx in enumerate(groups):
            src = Source(kind, seed_of(f"{key}/{g}"))
            src.flames = [Flame(tongues[i], seed_of(tongues[i].name), True) for i in idx]
            centre = (sum((bases[i] for i in idx), Vector()) / len(idx)) if idx else None
            local.append((src, centre))
        sources += [s for s, _ in local]

        def nearest(ob):
            if len(local) == 1 or local[0][1] is None:
                return local[0][0]
            p = ob.matrix_world.translation
            return min(local, key=lambda sc: (sc[1] - p).length)[0]

        for o in flames:
            if o not in tongues:                  # lantern panes and the like: glow only, no shape change
                nearest(o).flames.append(Flame(o, seed_of(o.name), False))
        for o in coals:
            nearest(o).coals.append(o)
        for li in lights:
            nearest(li).lights.append((li, li.data.energy, tuple(li.location)))
        for o in smoke:
            nearest(o).smoke.append((o, float(o["density"])))
        for mat in rooms:
            local[0][0].rooms.append(_flicker_value(mat))
    return sources, sparks


# ---------- wind in the trees ----------

class Sway:
    """Bends a tree mesh in the wind: offset = weight * (gusting lean + branch flutter).

    The weight grows with height above the ground and with distance from the trunk, so the
    trunk hardly moves, limbs a little and twigs most. The lean follows `gust` delayed by the
    wind's travel time to the tree, so a gust crosses the tree line; flutter has a phase that
    changes across a branch's length, so branches move against each other.
    """

    def __init__(self, ob, weight, amp, flutter):
        me = ob.data
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        self.ob, self.me = ob, me
        self.co0 = co.reshape(-1, 3)
        self.w = weight.astype(np.float32)[:, None]
        # world directions in mesh space, so a rotated or scaled prop bends the same way
        mw = np.array(ob.matrix_world, np.float32)
        inv = np.linalg.inv(mw[:3, :3])
        self.dirs = tuple((inv @ np.array(v, np.float32)).astype(np.float32)
                          for v in (WIND_DIR, (-WIND_DIR[1], WIND_DIR[0], 0.0), (0.0, 0.0, 1.0)))
        x, y, z = (self.co0 @ mw[:3, :3].T + mw[:3, 3]).T                  # world meters
        self.phase = (2.1 * np.sin(0.9 * x + 1.3 * y) + 1.7 * np.sin(1.1 * y - 0.7 * z + 0.4)
                      + 1.3 * np.sin(0.8 * z + 1.5 * x + 1.1)).astype(np.float32)
        p = mw[:3, 3]
        self.delay = float(p[0] * WIND_DIR[0] + p[1] * WIND_DIR[1]) / 7.0   # gusts travel about 7 m/s
        self.seed = seed_of(ob.name)
        self.amp, self.flutter = amp, flutter

    def apply(self, t):
        g = gust(t - self.delay)
        f = 0.35 + 0.65 * g
        sway = 0.12 * math.sin(2 * math.pi * 0.31 * t + (self.seed % 628) / 100.0)   # the crown's own swing
        lean = self.amp * (0.25 + 0.9 * g + sway * (0.4 + g))
        d, side, up = self.dirs
        ph = self.phase
        a = self.flutter * f
        off = (lean * d[None, :]
               +(a * 0.7 * np.sin(2 * np.pi * 0.55 * t + ph))[:, None] * d
               + (a * 0.5 * np.sin(2 * np.pi * 0.83 * t + 1.37 * ph))[:, None] * side
               + (a * 0.25 * np.sin(2 * np.pi * 1.21 * t + 0.71 * ph))[:, None] * up)
        co = self.co0 + self.w * off
        self.me.vertices.foreach_set("co", co.astype(np.float32).ravel())
        self.me.update()


def _tree_weights(ob, key, co):
    """Per-vertex sway weight 0..~1.3 of a tree, tree line or bush mesh (mesh-space coordinates)."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    if key == "treeline":
        from assets import treeline
        ground = np.array([treeline.hill_height(float(a), float(b)) for a, b in zip(x, y)], np.float32)
        h = np.clip((z - ground) / 11.0, 0.0, 1.0)
        return h ** 1.6
    top = max(float(z.max()), 0.3)
    h = np.clip(z / top, 0.0, 1.0)
    r = np.hypot(x, y)
    out = np.clip(r / (0.3 * top), 0.0, 1.0)
    w = h ** 1.6 * (0.35 + 0.65 * out)
    if "twigs" in _base(ob.name):
        w = w * 1.3
    return w


def _setup_trees(objects):
    sways = []
    for root in objects:
        if not root.name.startswith("prop_") or root.parent is not None:
            continue
        key = root.name[len("prop_"):].split("#")[0]
        if key not in TREES:
            continue
        for ob in root.children_recursive:
            if ob.type != "MESH" or _base(ob.name) == "treeline_hill":
                continue
            co = np.empty(len(ob.data.vertices) * 3, np.float32)
            ob.data.vertices.foreach_get("co", co)
            w = _tree_weights(ob, key, co.reshape(-1, 3))
            sways.append(Sway(ob, w, **TREES[key]))
    return sways


# ---------- entry points ----------

def setup(objects=None, perches=None):
    """Find and prepare everything that moves; returns a summary dict.

    objects: the scene's objects (default: the current scene). perches: merlon tops
    (x, y, z, rot_z) where a flying crow may land (build_scene.PERCHES).
    """
    import bpy
    global _STATE
    objects = list(objects if objects is not None else bpy.context.scene.objects)
    sources, sparks = _setup_fires(objects)
    sways = _setup_trees(objects)
    crows = anim_crows.setup(objects, perches or [])
    _STATE = dict(sources=sources, sparks=sparks, sways=sways, crows=crows)
    summary = dict(fires=sum(s.kind != "interior" for s in sources), interiors=sum(s.kind == "interior" for s in sources),
                   flames=sum(len(s.flames) for s in sources), lights=sum(len(s.lights) for s in sources),
                   sparks=len(sparks), trees=len(sways), **crows.summary())
    return summary


def apply(t):
    """Pose everything for time t (seconds)."""
    if _STATE is None:
        raise RuntimeError("anim.setup() first")
    for s in _STATE["sources"]:
        s.apply(t)
    for s in _STATE["sparks"]:
        s.apply(t)
    for s in _STATE["sways"]:
        s.apply(t)
    _STATE["crows"].apply(t)

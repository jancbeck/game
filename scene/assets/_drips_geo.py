"""Water geometry for assets/drips.py: falling strands, drip chains, splashes, rings and wet patches.

Everything is built from a few merged meshes (`Soup`), in world meters, with real thickness, so the
water reads from any camera. Nothing here depends on the camera.

Physics, kept simple:

- A drop that leaves an edge with a small horizontal speed follows a parabola, so after falling
  `h` meters it is `hv * sqrt(h)` out from the edge. A light wind leans it on top of that.
- A stream speeds up as it falls (v = sqrt(v0^2 + 2 g h)) and thins with it. It necks, then breaks
  into beads a short way below the edge; the beads keep falling and drift apart.
- A string of drips leaves an edge at a steady interval, so the drop that left k intervals ago has
  fallen 1/2 g (k T)^2: the chain opens up toward the ground. Fast drops are drawn as short streaks.
- A strand that lands throws a crown of droplets on parabolas, a ring spreads on the surface and
  the surface stays dark and mirror-wet around the spot.
"""

import math

import bpy
from mathutils import Vector

G = 9.81
THICKEN = 2.6                 # strands are drawn thicker than real water so they read at game distances
WIND = (0.025, 0.010)         # sideways lean in meters per meter of fall, for streams
V0 = 0.5                      # speed of a stream where it leaves the edge, m/s


class Soup:
    """Vertices, faces and float point attributes of many small parts, as one mesh."""

    def __init__(self, attrs=()):
        self.v, self.f = [], []
        self.a = {n: [] for n in attrs}

    def add(self, verts, faces, **attr):
        base = len(self.v)
        self.v += [tuple(p) for p in verts]
        self.f += [tuple(base + i for i in f) for f in faces]
        for name, values in self.a.items():
            val = attr.get(name, 0.0)
            values += list(val) if hasattr(val, "__len__") else [val] * len(verts)

    def to_object(self, name, mat, parent):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.update()
        for p in me.polygons:
            p.use_smooth = True
        for attr_name, values in self.a.items():
            at = me.attributes.new(attr_name, "FLOAT", "POINT")
            at.data.foreach_set("value", values)
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        bpy.context.collection.objects.link(ob)
        ob.parent = parent
        ob.visible_shadow = False      # water never shades the light that makes it glint
        return ob


def _frame(t):
    ref = Vector((1.0, 0.0, 0.0)) if abs(t.x) < 0.9 else Vector((0.0, 1.0, 0.0))
    u = (ref - t * ref.dot(t)).normalized()
    return u, t.cross(u)


def tube(soup, path, radii, sides=5):
    """Tube along `path` (Vectors) with a radius per point. A radius of 0 closes the end to a point."""
    n = len(path)
    verts, faces, rings = [], [], []
    for i, (p, r) in enumerate(zip(path, radii)):
        if r <= 1e-6:
            rings.append([len(verts)])
            verts.append(p)
            continue
        t = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)])
        t = t.normalized() if t.length > 1e-9 else Vector((0, 0, -1))
        u, w = _frame(t)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            ring.append(len(verts))
            verts.append(p + (u * math.cos(a) + w * math.sin(a)) * r)
        rings.append(ring)
    for ra, rb in zip(rings, rings[1:]):
        if len(ra) == 1 and len(rb) == 1:
            continue
        if len(ra) == 1:
            faces += [(ra[0], rb[(k + 1) % sides], rb[k]) for k in range(sides)]
        elif len(rb) == 1:
            faces += [(ra[k], ra[(k + 1) % sides], rb[0]) for k in range(sides)]
        else:
            faces += [(ra[k], ra[(k + 1) % sides], rb[(k + 1) % sides], rb[k]) for k in range(sides)]
    soup.add(verts, faces)


def spindle(soup, a, b, radius, sides=5):
    """A bead from `a` to `b`: fat in the middle, pointed at both ends."""
    a, b = Vector(a), Vector(b)
    stations = (0.0, 0.18, 0.5, 0.82, 1.0)
    prof = (0.0, 0.75, 1.0, 0.75, 0.0)
    tube(soup, [a.lerp(b, s) for s in stations], [radius * p for p in prof], sides)


def lateral(h, heading, hv, lean=WIND):
    """Sideways displacement (dx, dy) of water that has fallen `h` meters from an edge."""
    s = hv * math.sqrt(max(h, 0.0))
    return heading[0] * s + lean[0] * h, heading[1] * s + lean[1] * h


def _at(x, y, z0, h, heading, hv, lean):
    dx, dy = lateral(h, heading, hv, lean)
    return Vector((x + dx, y + dy, z0 - h))


def _smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def stream(soup, x, y, z0, z1, heading, hv, flow, rng):
    """Continuous jet from (x, y, z0) down to z1 that necks and breaks into beads.

    Radius at the edge is 2.5 to 7 mm times THICKEN, growing with `flow` (0..1).
    """
    H = z0 - z1
    r0 = THICKEN * (0.0025 + 0.0045 * flow)
    speed = lambda h: math.sqrt(V0 * V0 + 2 * G * h)          # noqa: E731
    radius = lambda h: r0 * (V0 / speed(h)) ** 0.35            # noqa: E731
    hb = min(H, rng.uniform(0.5, 1.0) * (0.8 + flow))
    lam = rng.uniform(0.05, 0.075)
    phase = rng.uniform(0, 2 * math.pi)
    step = 0.014
    n = max(2, int(hb / step))
    path, radii = [], []
    for i in range(n + 1):
        h = hb * i / n
        neck = 0.85 * _smooth((h - 0.25 * hb) / (0.75 * hb))
        path.append(_at(x, y, z0, h, heading, hv, WIND))
        radii.append(radius(h) * (1 + 0.55 * neck * math.sin(2 * math.pi * h / lam + phase)) * (1.0 - 0.25 * neck))
    tube(soup, path, radii, sides=5)
    # below the break-up point the jet is a string of beads that spread out as they fall
    h = hb + rng.uniform(0.0, 0.03)
    while h < H - 0.02:
        r = radius(h)
        gap = max(0.035, 8 * r) * (1 + 0.10 * h) * rng.uniform(0.85, 1.2)
        length = min(gap * rng.uniform(0.62, 0.85), H - h)
        spindle(soup, _at(x, y, z0, h, heading, hv, WIND), _at(x, y, z0, h + length, heading, hv, WIND),
                r * rng.uniform(0.85, 1.15), sides=4)
        h += gap


def chain(soup, x, y, z0, z1, heading, hv, flow, rng):
    """A string of drips leaving an edge at a steady interval; falling drops are drawn as streaks."""
    H = z0 - z1
    interval = rng.uniform(0.07, 0.2) * (1.3 - flow * 0.6)
    t = rng.uniform(0.0, interval)
    lean = (WIND[0] * 0.5, WIND[1] * 0.5)
    # drop about to let go: a pendant teardrop on the edge
    rb = THICKEN * rng.uniform(0.0016, 0.0024)
    spindle(soup, (x, y, z0 + 0.002), (x, y, z0 - 0.016), rb * 1.2, sides=4)
    k = 0
    while True:
        tk = t + k * interval
        h = 0.5 * G * tk * tk
        if h > H - 0.03:
            break
        v = G * tk
        length = min(0.014 + 0.007 * v, 0.14)
        top = max(h - length, 0.0)
        spindle(soup, _at(x, y, z0, top, heading, hv, lean), _at(x, y, z0, h, heading, hv, lean),
                rb * rng.uniform(0.8, 1.15), sides=4)
        k += 1


def crown(soup, x, y, z, flow, rng):
    """Droplets thrown out of the impact on small parabolas, and a short jet for a heavy strand."""
    n = 5 + int(5 * flow)
    for _ in range(n):
        az = rng.uniform(0, 2 * math.pi)
        hmax = rng.uniform(0.02, 0.06) * (0.6 + flow)
        reach = hmax * rng.uniform(1.3, 2.4)
        s = rng.uniform(0.12, 0.88)
        d = Vector((math.cos(az), math.sin(az), 0))
        pos = Vector((x, y, z + 0.004)) + d * (reach * s) + Vector((0, 0, 4 * hmax * s * (1 - s)))
        tan = (d * reach + Vector((0, 0, 4 * hmax * (1 - 2 * s)))).normalized()
        half = rng.uniform(0.003, 0.007)
        spindle(soup, pos - tan * half, pos + tan * half, THICKEN * rng.uniform(0.0011, 0.0018), sides=4)
    if flow > 0.4:
        top = z + rng.uniform(0.05, 0.11) * flow
        spindle(soup, (x, y, z + 0.004), (x + rng.uniform(-0.01, 0.01), y + rng.uniform(-0.01, 0.01), top),
                THICKEN * 0.0016, sides=4)


def ring(soup, x, y, z, r_in, r_out, segs=22):
    """Flat ripple ring, faded to nothing at both edges (attribute `fade`)."""
    mid = 0.5 * (r_in + r_out)
    verts, fade, faces = [], [], []
    for r, f in ((r_in, 0.0), (mid, 1.0), (r_out, 0.0)):
        for k in range(segs):
            a = 2 * math.pi * k / segs
            verts.append((x + r * math.cos(a), y + r * math.sin(a), z + 0.003))
            fade.append(f)
    for c in range(2):
        for k in range(segs):
            k2 = (k + 1) % segs
            faces.append((c * segs + k, c * segs + k2, (c + 1) * segs + k2, (c + 1) * segs + k))
    soup.add(verts, faces, fade=fade)


def patch(soup, x, y, z, radius, rng, stretch=(1.0, 1.0), segs=14):
    """Dark wet disc with a ragged outline that fades out toward its rim."""
    p1, p2 = rng.uniform(0, 6.28), rng.uniform(0, 6.28)
    verts, fade, faces = [(x, y, z + 0.0018)], [1.0], []
    for frac, f in ((0.45, 0.95), (0.8, 0.55), (1.0, 0.0)):
        for k in range(segs):
            a = 2 * math.pi * k / segs
            r = radius * frac * (1 + 0.18 * math.sin(2 * a + p1) + 0.1 * math.sin(3 * a + p2))
            verts.append((x + r * math.cos(a) * stretch[0], y + r * math.sin(a) * stretch[1], z + 0.0018))
            fade.append(f)
    for k in range(segs):
        faces.append((0, 1 + k, 1 + (k + 1) % segs))
    for c in range(2):
        for k in range(segs):
            k2 = (k + 1) % segs
            a0, a1 = 1 + c * segs, 1 + (c + 1) * segs
            faces.append((a0 + k, a0 + k2, a1 + k2, a1 + k))
    soup.add(verts, faces, fade=fade)


def sheet(soup, a, b, h_end, rng):
    """Veil of water between two neighbouring streams: heavy flows merge into a thin film that
    fades out (attribute `fade`) where it breaks up. `a` and `b` are (x, y, z, heading, hv) tuples."""
    rows = max(3, int(h_end / 0.04))
    verts, fade, faces = [], [], []
    for i in range(rows + 1):
        h = h_end * i / rows
        for (x, y, z, heading, hv) in (a, b):
            verts.append(tuple(_at(x, y, z, h, heading, hv, WIND)))
            fade.append(1.0 - _smooth(h / h_end) ** 1.3)
    for i in range(rows):
        base = 2 * i
        faces.append((base, base + 2, base + 3, base + 1))
    soup.add(verts, faces, fade=fade)

"""Tube, rope and feather-ribbon builders shared by the organic props.

Not a prop module: the leading underscore keeps it out of assets.available().
Points are plain 3-tuples or Vectors in the caller's frame (root-relative).
"""

import math

from mathutils import Vector


def curve(ctrl, step=0.01):
    """Catmull-Rom spline through `ctrl`, resampled every `step` meters of arc length."""
    P = [Vector(p) for p in ctrl]
    if len(P) < 3:
        dense = [P[0].lerp(P[-1], i / 16) for i in range(17)]
    else:
        dense = []
        for i in range(len(P) - 1):
            p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
            for k in range(16):
                t = k / 16
                dense.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                                    + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
        dense.append(P[-1])
    lens = [0.0]
    for a, b in zip(dense, dense[1:]):
        lens.append(lens[-1] + (b - a).length)
    total = lens[-1]
    n = max(2, int(round(total / step)) + 1)
    out, j = [], 0
    for i in range(n):
        s = total * i / (n - 1)
        while j < len(lens) - 2 and lens[j + 1] < s:
            j += 1
        seg = lens[j + 1] - lens[j]
        out.append(dense[j].lerp(dense[j + 1], 0.0 if seg < 1e-9 else (s - lens[j]) / seg))
    return out


def frames(P, ref=(0, 0, 1)):
    """Parallel-transport frames along polyline P: tangents, 'up' normals, 'side' vectors.

    `up` starts as `ref` made perpendicular to the path, so ref=(0, 0, 1) keeps rings level.
    """
    n = len(P)
    T = []
    for i in range(n):
        d = P[min(i + 1, n - 1)] - P[max(i - 1, 0)]
        T.append(d.normalized() if d.length > 1e-9 else (T[-1] if T else Vector((0, 0, 1))))
    ref = Vector(ref)
    up = ref - T[0] * ref.dot(T[0])
    if up.length < 1e-4:
        up = Vector((1, 0, 0)) - T[0] * T[0].x
    up.normalize()
    U = [up]
    for i in range(1, n):
        up = T[i - 1].rotation_difference(T[i]) @ up
        up = (up - T[i] * up.dot(T[i])).normalized()
        U.append(up)
    return T, U, [t.cross(u) for t, u in zip(T, U)]


def _interp(vals, t):
    """Catmull-Rom through control values spread evenly over t in [0, 1]."""
    if not isinstance(vals, (list, tuple)):
        return vals
    n = len(vals)
    if n == 1:
        return vals[0]
    x = min(max(t, 0.0), 1.0) * (n - 1)
    i = min(int(x), n - 2)
    f = x - i
    p0, p1, p2, p3 = vals[max(i - 1, 0)], vals[i], vals[i + 1], vals[min(i + 2, n - 1)]
    return 0.5 * (2 * p1 + (p2 - p0) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f
                  + (3 * p1 - p0 - 3 * p2 + p3) * f ** 3)


def tube_mesh(P, rx, rz=None, sides=8, ref=(0, 0, 1), cap=True, rng=None, rough=0.0):
    """Vertices and faces of a tube along P. rx/rz: scalar or control list along the path."""
    rz = rx if rz is None else rz
    n = len(P)
    _, U, S = frames(P, ref)
    verts, faces = [], []
    for i in range(n):
        t = i / (n - 1)
        a, b = max(_interp(rx, t), 4e-4), max(_interp(rz, t), 4e-4)
        for j in range(sides):
            ang = 2 * math.pi * j / sides
            f = 1.0 + (rng.uniform(-rough, rough) if rng is not None and rough else 0.0)
            verts.append(P[i] + S[i] * (a * math.cos(ang) * f) + U[i] * (b * math.sin(ang) * f))
    for i in range(n - 1):
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append((i * sides + j, i * sides + j2, (i + 1) * sides + j2, (i + 1) * sides + j))
    if cap:
        faces.append(tuple(range(sides - 1, -1, -1)))
        faces.append(tuple(range((n - 1) * sides, n * sides)))
    return verts, faces


def smooth(ob):
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def sweep(kit, name, ctrl, rx, rz=None, mat=None, parent=None, sides=8, ref=(0, 0, 1), cap=True,
          step=None, rng=None, rough=0.0):
    """Smooth-shaded tube through `ctrl` (resampled every `step` m when given)."""
    P = curve(ctrl, step) if step else [Vector(p) for p in ctrl]
    verts, faces = tube_mesh(P, rx, rz, sides, ref, cap, rng, rough)
    return smooth(kit.mesh(name, verts, faces, mat=mat, parent=parent))


def rope(kit, name, ctrl, radius, mat, parent, lay=0.1, step=0.01, phase=0.0, sides=6,
         origin=None):
    """Three-strand laid rope along a spline through `ctrl`.

    `lay` is the length of one full twist. The object origin sits at `origin` (default: the
    first point) because the rope material reads object coordinates.
    """
    P = curve(ctrl, step)
    _, U, S = frames(P)
    r_s, d = radius * 0.464, radius * 0.536
    verts, faces = [], []

    def add(v, f):
        faces.extend(tuple(i + len(verts) for i in face) for face in f)
        verts.extend(v)

    add(*tube_mesh(P, radius * 0.34, radius * 0.34, 5, cap=True))
    for k in range(3):
        pts, s = [], 0.0
        for i, p in enumerate(P):
            if i:
                s += (p - P[i - 1]).length
            ph = phase + 2 * math.pi * (k / 3 + s / lay)
            pts.append(p + (S[i] * math.cos(ph) + U[i] * math.sin(ph)) * d)
        add(*tube_mesh(pts, r_s, r_s, sides, cap=True))
    o = Vector(origin) if origin is not None else P[0]
    ob = kit.mesh(name, [v - o for v in verts], faces, loc=tuple(o), mat=mat, parent=parent)
    return smooth(ob)


def blade(p0, d, side, length, width, bend=(0, 0, 0), rach=0.003):
    """One feather as rows of three points: left edge, shaft ridge, right edge.

    p0 is the base, d the unit direction, side the unit width direction. `bend` is the
    displacement of the tip off the straight axis (applied quadratically along the length).
    """
    S = (0.0, 0.18, 0.4, 0.6, 0.78, 0.92, 1.0)
    W = (0.80, 1.0, 1.0, 0.96, 0.86, 0.6, 0.1)
    p0, d, side, bend = Vector(p0), Vector(d).normalized(), Vector(side), Vector(bend)
    nrm = side.cross(d).normalized()
    if nrm.z < 0:
        nrm = -nrm
    rows = []
    for s, w in zip(S, W):
        c = p0 + d * (length * s) + bend * (s * s)
        rows.append((c - side * (w * width / 2), c + nrm * (rach * w), c + side * (w * width / 2)))
    return rows


def ribbons(kit, name, blades, mat, parent, tf=None):
    """One smooth mesh from many blades (or any equal-width point rows); tf maps each point."""
    verts, faces = [], []
    for rows in blades:
        base, m = len(verts), len(rows[0])
        verts.extend(tf(p) if tf else p for row in rows for p in row)
        for i in range(len(rows) - 1):
            for j in range(m - 1):
                a = base + i * m + j
                faces.append((a, a + 1, a + m + 1, a + m))
    return smooth(kit.mesh(name, verts, faces, mat=mat, parent=parent))

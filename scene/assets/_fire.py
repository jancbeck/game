"""Shared fire-effect geometry: torch_sconce, brazier, forge, lanterns and the shed hearth.

- flame(): smooth, jagged, curled flame tongue (material `fire`); a fire is several of them.
- sparks(): one mesh of tiny glowing flakes drifting up with the wind (material `embers`).
- smoke(): box that carries the `smoke` volume material, which shapes the plume inside it.

Everything here is visual only: no part casts a shadow, otherwise the parts would block the
point light that sits inside the fire.
"""

import math

import bmesh
import bpy
from mathutils import Vector


def _link(ob, parent):
    bpy.context.collection.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    ob.visible_shadow = False
    return ob


def flame(kit, mat, parent, name, base, height, radius, lean=(0.0, 0.0), twist=1.2, phase=0.0,
          flat=0.5, curl=0.22, rings=24, sides=10):
    """One licking tongue of flame, smooth shaded. The object origin is the base of the tongue.

    A blade, not a cone: elliptical rings (width `radius`, depth `flat` of it) swell fast near the
    base and then run out to a point with concave sides. The width carries lobes, so the outline is
    ragged, the rings carry a ripple, so the edge is jagged, and the spine leans quadratically by
    `lean` (meters per meter of height), kinks twice, and curls over at the tip by `curl`. `phase`
    makes every tongue different; the rings twist by `twist` radians.
    """
    verts, faces = [], []
    ph = phase
    for i in range(rings):
        t = i / rings
        rise = 0.55 + 0.45 * math.sin(min(1.0, t / 0.2) * math.pi / 2)
        lobes = 1 + 0.30 * math.sin(8.5 * t + 1.7 * ph) * t ** 0.5 + 0.14 * math.sin(19 * t + 2.9 * ph) * t
        r = radius * rise * (1 - t) ** 1.2 * lobes
        cx = lean[0] * t * t * height + curl * height * t ** 3 * math.cos(ph) \
            + radius * (0.30 * math.sin(5.5 * t + ph) + 0.18 * math.sin(11 * t + 2 * ph) * t) * (0.4 + t)
        cy = lean[1] * t * t * height + curl * height * t ** 3 * math.sin(ph) \
            + radius * (0.30 * math.cos(4.5 * t + ph) + 0.18 * math.cos(9 * t + 2 * ph) * t) * (0.4 + t)
        phi = twist * t
        for k in range(sides):
            a = 2 * math.pi * k / sides
            jag = 1 + 0.16 * math.sin(5 * a + 12 * t + 3 * ph) * t
            ex, ey = r * jag * math.cos(a), flat * r * jag * math.sin(a)
            verts.append((cx + ex * math.cos(phi) - ey * math.sin(phi),
                          cy + ex * math.sin(phi) + ey * math.cos(phi), t * height))
    verts.append((lean[0] * height + curl * height * math.cos(ph),
                  lean[1] * height + curl * height * math.sin(ph), height))
    apex = len(verts) - 1
    for i in range(rings - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((i * sides + k, i * sides + k2, (i + 1) * sides + k2, (i + 1) * sides + k))
    top = (rings - 1) * sides
    for k in range(sides):
        faces.append((top + k, top + (k + 1) % sides, apex))
    faces.append(tuple(range(sides))[::-1])
    ob = kit.mesh(name, verts, faces, loc=base, mat=mat, parent=parent)
    for p in ob.data.polygons:
        p.use_smooth = True
    ob.visible_shadow = False
    return ob


def sparks(kit, mat, parent, name, rng, count, origin, height, spread, wind, size):
    """`count` tiny elongated diamonds rising from `origin`, drifting along `wind` (x, y).

    They thin out and cool with height: the per-point attribute `spark` (1 hot, 0 cold)
    drives the `embers` material, which reads it. Size is the typical length in meters.
    """
    bm = bmesh.new()
    heat = []
    ox = oy = oz = 0.0       # points are relative to the emitter; the object sits at `origin`
    for _ in range(count):
        t = rng.random() ** 1.5
        ang = rng.uniform(0, 2 * math.pi)
        rad = spread * (0.3 + t) * math.sqrt(rng.random())
        pos = Vector((ox + rad * math.cos(ang) + wind[0] * (t ** 1.4) * height,
                      oy + rad * math.sin(ang) + wind[1] * (t ** 1.4) * height,
                      oz + t * height))
        axis = Vector((wind[0] * 0.8 + rng.uniform(-0.3, 0.3),
                       wind[1] * 0.8 + rng.uniform(-0.3, 0.3), 1.0)).normalized()
        u = axis.cross(Vector((0.3, 1.0, 0.2))).normalized()
        v = axis.cross(u)
        half = size * (1.0 - 0.45 * t) * rng.uniform(0.6, 1.4) / 2
        wide = half * rng.uniform(0.35, 0.55)
        pts = [pos + axis * half, pos - axis * half, pos + u * wide, pos - u * wide,
               pos + v * wide, pos - v * wide]
        bv = [bm.verts.new(p) for p in pts]
        for a, b in ((2, 4), (4, 3), (3, 5), (5, 2)):
            bm.faces.new((bv[0], bv[a], bv[b]))
            bm.faces.new((bv[1], bv[b], bv[a]))
        heat += [(1.0 - t) ** 1.1 * rng.uniform(0.45, 1.0)] * 6
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    attr = me.attributes.new("spark", "FLOAT", "POINT")
    attr.data.foreach_set("value", heat)
    me.materials.append(mat)
    ob = _link(bpy.data.objects.new(name, me), parent)
    ob.location = origin
    return ob


WIND_YAW = 12.0       # world wind: toward +X, slightly +Y (degrees counter-clockwise from +X)


def smoke(kit, mat, parent, name, base, rise, drift, r0, r1, density, ang0=WIND_YAW, seed=0.0):
    """Smoke plume: a volume box whose `smoke` material shapes the plume inside it.

    The object origin is the base of the plume. The wind blows along world yaw `ang0`. The
    plume leaves the base at the angle atan(rise / drift) above the ground and flattens out
    to a height of `rise` meters above the base; `drift` is the distance downwind over which
    that happens (the plume is gone after about 2.7 * drift). The wind always wins: `rise` is
    capped at `drift`, so no plume leaves the base steeper than 45 degrees. `r0` and `r1` are
    the radius at the base and at the far end, `density` is the density per meter at the foot
    (about 1 is a plume that is just visible in the dark). The material spreads
    that density over the growing cross-section, so a plume that widens by 3x is about 5x
    thinner at the far end before it fades out. The mesh is a plain box big enough for the
    whole plume; the material fades to nothing before the walls, so the box never shows.

    EEVEE evaluates volumes in depth slices (`scene.eevee.volumetric_samples`). A plume thinner
    than about a slice drops out, so keep the plumes wide and set 192 samples.
    """
    rise = min(rise, drift)
    reach = 2.7 * drift + 2.4 * r1
    z0, z1 = -2.0 * r1, rise + 2.4 * r1
    verts = [(sx * reach, sy * reach, z) for z in (z0, z1) for sx, sy in
             ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = kit.mesh(name, verts, faces, loc=base, mat=mat, parent=parent)
    for key, value in (("rise", rise), ("drift", drift), ("r0", r0), ("r1", r1),
                       ("density", density), ("ang0", ang0), ("seed", seed)):
        ob[key] = float(value)
    ob.visible_shadow = False
    return ob

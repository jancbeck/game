"""Courtyard debris: broken planks, a snapped board, splinters, loose stones, a dropped bucket.

Spread over about 2.6 x 1.6 m on Z = 0, centered on the origin. Planks are
3 cm thick and 14 to 20 cm wide with jagged broken ends. One plank rests across
another, the snapped board has one half angled up, and the bucket lies tipped
on its side with its bail on the ground.
"""

import math

from . import bucket as bucket_mod


def _plank(kit, name, length, width, thick, rng, mat, parent, jag_left=False, jag_right=True, **place):
    """Plank along X, centered on the origin, with optional splintered ends."""
    hl, hw = length / 2, width / 2
    outline = []
    ys = [-hw + width * i / 5 for i in range(6)]
    if jag_right:
        outline += [(hl - rng.uniform(0, 0.14) * (1 if i % 2 else 0.35), y) for i, y in enumerate(ys)]
    else:
        outline += [(hl, -hw), (hl, hw)]
    if jag_left:
        outline += [(-hl + rng.uniform(0, 0.14) * (1 if i % 2 else 0.35), y) for i, y in reversed(list(enumerate(ys)))]
    else:
        outline += [(-hl, hw), (-hl, -hw)]
    n = len(outline)
    verts = [(x, y, -thick / 2) for x, y in outline] + [(x, y, thick / 2) for x, y in outline]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for i in range(n):
        k = (i + 1) % n
        faces.append((i, k, n + k, n + i))
    return kit.mesh(name, verts, faces, mat=mat, parent=parent, bevel=0.003, **place)


def _stone(kit, mats, rng, parent, name, x, y, r):
    sz = r * rng.uniform(0.55, 0.75)
    ob = kit.sphere(name, 1.0, (x, y, 0), scale=(r, r * rng.uniform(0.75, 1.0), sz),
                    rot_deg=(0, 0, rng.uniform(0, 180)), mat=mats["stone_wall"], segments=9, parent=parent)
    for v in ob.data.vertices:
        v.co *= rng.uniform(0.86, 1.12)
        v.co.z = max(v.co.z, -0.55 * sz)
    ob.location.z = 0.55 * sz - 0.004
    return ob


def build(kit, mats, rng):
    j = lambda a: kit.jitter(rng, a)  # noqa: E731
    root = kit.group("debris")
    wo, wd = mats["wood_old"], mats["wood_dark"]

    # two planks, one resting across the other
    _plank(kit, "plank_a", 1.3 + j(0.1), 0.19, 0.03, rng, wo, root, loc=(0.05, 0.25, 0.016),
           rot_deg=(0, 0, 12 + j(6)))
    _plank(kit, "plank_b", 0.9 + j(0.1), 0.15, 0.025, rng, wd, root, jag_left=True,
           loc=(0.2 + j(0.05), 0.28, 0.0445), rot_deg=(0, 4, -55 + j(8)))

    # snapped board: one half flat, the other still hinged at the break and lifted
    brk = kit.group("snapped", (-0.85, -0.4, 0), parent=root)
    brk.rotation_euler = (0, 0, math.radians(35 + j(10)))
    l1, l2, lift = 0.6, 0.55, math.radians(13)
    _plank(kit, "snap_a", l1, 0.16, 0.025, rng, wo, brk, loc=(-l1 / 2, 0, 0.0135))
    _plank(kit, "snap_b", l2, 0.16, 0.025, rng, wo, brk, jag_left=True, jag_right=False,
           loc=(l2 / 2 * math.cos(lift), 0, l2 / 2 * math.sin(lift) + 0.0135), rot_deg=(0, -13, 0))

    # splinters: thin pyramids lying near the planks
    for k in range(9):
        a = rng.uniform(0, 2 * math.pi)
        d = rng.uniform(0.05, 0.9)
        length = rng.uniform(0.1, 0.3)
        kit.cylinder(f"splinter_{k}", 0.009, length, (0.0 + d * math.cos(a) * 1.3, 0.1 + d * math.sin(a) * 0.7, 0.008),
                     (90, 0, rng.uniform(0, 180)), wo, segments=4, radius_top=0.001, parent=root)

    # loose stones
    spots = [(0.95, 0.45), (-0.3, 0.7), (0.45, -0.5), (1.1, -0.1), (-0.1, -0.35)]
    for k, (x, y) in enumerate(spots):
        _stone(kit, mats, rng, root, f"stone_{k}", x + j(0.1), y + j(0.1), rng.uniform(0.05, 0.12))

    # dropped bucket: lying on its side, ears horizontal so the bail falls to the ground
    tip = kit.group("bucket_tip", (0.85, -0.65, 0.14), parent=root)
    tip.rotation_euler = (0, math.radians(85.1), math.radians(rng.uniform(0, 360)))
    b = bucket_mod.build(kit, mats, rng, bail_deg=95)
    b.parent = tip
    b.rotation_euler = (0, 0, math.radians(90))
    return root

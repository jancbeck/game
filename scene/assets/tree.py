"""Bare, gnarled deciduous tree: twisted trunk, root flare, branches down to thin twigs.

Origin at the trunk base on Z = 0, 5 to 9 m tall (the rng sets the height, the
crown style, the lean and the trunk twist, so instances look different).
Trunk, limbs and roots are `bark`; branches thinner than 4 cm are a second mesh
in `wood_dark`, which reads as a darker twig tangle. Branches bend back toward
their start direction, so there are no long smooth arcs. 40k to 100k triangles.

Styles: `spread` (wide crown of long crooked limbs), `upright` (narrow, limbs
rise steeply), `lean` (spread crown on a leaning trunk) and `fork` (a short
trunk that splits into three heavy limbs).
"""

import math

from mathutils import Vector

from . import _tube

STYLES = {
    #            trunk length / H, limb angle from trunk, limb length / trunk, limb pull up
    "spread":  dict(trunk=(0.50, 0.62), angle=(48, 80), limb_len=(0.70, 1.00), up=0.05, limbs=(5, 7)),
    "upright": dict(trunk=(0.70, 0.85), angle=(16, 40), limb_len=(0.35, 0.55), up=0.10, limbs=(6, 9)),
    "lean":    dict(trunk=(0.55, 0.70), angle=(40, 70), limb_len=(0.55, 0.85), up=0.06, limbs=(5, 7)),
    "fork":    dict(trunk=(0.28, 0.36), angle=(45, 75), limb_len=(0.60, 0.85), up=0.06, limbs=(2, 3)),
}
WEIGHTS = {"spread": 3, "upright": 2, "lean": 2, "fork": 2}


def _roots(mesh, rng, r_base, count):
    """Buttress roots that leave the trunk 0.5 to 1 m up, curve over the ground and dive."""

    def root(start, az, length, r0, z0, sub):
        n = 10
        ph = rng.uniform(0, 6.28)
        curve = rng.uniform(-0.35, 0.35)
        pts, radii, frames = [], [], []
        for i in range(n + 1):
            t = i / n
            r = max(0.02, r0 * (1 - t) ** 0.6)
            a = az + curve * t + 0.25 * math.sin(2 * math.pi * 1.2 * t + ph)
            x = start[0] + math.cos(az) * length * t + math.cos(a + 1.57) * 0.12 * length * math.sin(3 * t + ph)
            y = start[1] + math.sin(az) * length * t + math.sin(a + 1.57) * 0.12 * length * math.sin(3 * t + ph)
            z = max(-0.18, z0 * (1 - t) ** 3.5 + r * 0.3 - 0.2 * t ** 3)
            pts.append(Vector((x, y, z)))
            radii.append(r)
            frames.append((t, a))
        mesh.tube(pts, radii, 8 if r0 > 0.08 else 6)
        if not sub:
            return
        for _ in range(rng.choice((1, 2, 2, 3))):
            k = rng.randint(3, 6)
            t, a = frames[k]
            side = rng.choice((-1, 1))
            root((pts[k].x, pts[k].y), a + side * rng.uniform(0.5, 1.0),
                 length * rng.uniform(0.3, 0.5), radii[k] * rng.uniform(0.5, 0.7),
                 max(0.0, pts[k].z - 0.02), False)

    for k in range(count):
        az = 2 * math.pi * (k + rng.uniform(-0.3, 0.3)) / count
        start = (math.cos(az) * r_base * 0.4, math.sin(az) * r_base * 0.4)
        root(start, az, r_base * rng.uniform(2.5, 6.0), r_base * rng.uniform(0.45, 0.7),
             rng.uniform(0.25, 0.6), True)


def build(kit, mats, rng):
    root = kit.group("tree")
    style_name = rng.choices(list(WEIGHTS), weights=list(WEIGHTS.values()))[0]
    st = STYLES[style_name]
    height = rng.uniform(5.2, 8.8)
    gn = rng.uniform(0.85, 1.25)
    dens = rng.uniform(0.85, 1.15)
    up = st["up"]

    P = _tube.Params(
        seg=[0.22, 0.24, 0.22, 0.20, 0.17, 0.15, 0.13, 0.12, 0.10],
        gnarl=[g * gn for g in (0.10, 0.32, 0.38, 0.42, 0.46, 0.48, 0.50, 0.50, 0.50)],
        kink=[0.0, 0.18, 0.20, 0.20, 0.22, 0.22, 0.22, 0.22, 0.22],
        up=[0.03, up * 0.6, up * 0.5, 0.02, 0.0, -0.01, -0.02, -0.02, -0.02],
        spring=[0.06, 0.12, 0.14, 0.12, 0.10, 0.08, 0.08, 0.08, 0.08],
        keep=0.45,
        density=[0, 2.0 * dens, 3.2 * dens, 4.4 * dens, 5.6 * dens, 6.0 * dens, 6.0 * dens, 5.0 * dens, 0],
        angle=[st["angle"], (40, 80), (38, 75), (38, 75), (35, 70), (35, 70), (35, 70), (35, 70), (35, 70)],
        up_bias=[0.0, up * 1.5, 0.08, 0.06, 0.04, 0.02, 0.0, 0.0, 0.0],
        shrink=[(0.45, 0.65), (0.45, 0.65), (0.5, 0.7), (0.55, 0.78), (0.58, 0.8), (0.58, 0.8),
                (0.58, 0.8), (0.58, 0.8), (0.58, 0.8)],
        len_ratio=[st["limb_len"], (0.4, 0.7), (0.4, 0.7), (0.4, 0.7), (0.35, 0.6),
                   (0.35, 0.6), (0.35, 0.6), (0.35, 0.6), (0.35, 0.6)],
        t_first=[0.3, 0.2, 0.12, 0.1, 0.1, 0.08, 0.08, 0.08, 0.08],
        r_min=0.0018,
        min_len=0.1,
        max_level=8,
        floor=0.3,
        break_p=0.06,
        max_branches=4500,
        lobe={0: (rng.uniform(0.10, 0.18), rng.choice((3, 4, 5)), rng.uniform(0.12, 0.35)),
              1: (rng.uniform(0.05, 0.10), rng.choice((3, 4)), rng.uniform(0.10, 0.25))},
    )

    mesh, twigs = _tube.Mesh(), _tube.Mesh()
    grower = _tube.Grower(mesh, rng, P, fine=twigs, fine_r=0.02)

    r_base = height * rng.uniform(0.028, 0.040)
    trunk_len = height * rng.uniform(*st["trunk"])
    tilt = math.radians(rng.uniform(14, 28) if style_name == "lean" else rng.uniform(0, 7))
    az = rng.uniform(0, 2 * math.pi)
    lean = Vector((math.sin(tilt) * math.cos(az), math.sin(tilt) * math.sin(az), math.cos(tilt)))
    spec = dict(
        sway=(rng.uniform(0.05, 0.12), rng.uniform(0.25, 0.5), rng.uniform(0, 6.28)),
        flare=(rng.uniform(0.12, 0.3), 0.4),
        sides=12,
    )
    if style_name == "fork":
        spec.update(n_lat=rng.randint(*st["limbs"]), t_range=(0.35, 0.8), end_ratio=0.8,
                    n_term=3, term_shrink=(0.75, 0.95), term_angle=(22, 40),
                    term_len=height * 0.36)
    else:
        spec.update(n_lat=rng.randint(*st["limbs"]), t_range=(0.3, 0.97), end_ratio=0.22)
    grower.add((0, 0, -0.1), lean, trunk_len, r_base, 0, **spec)
    grower.run()

    _roots(mesh, rng, r_base, rng.randint(5, 8))

    top = max(mesh.max_z(), twigs.max_z() if twigs.verts else 0.0)
    for m in (mesh, twigs):
        m.scale(height / top)
    mesh.to_object("tree_wood", mats["bark"], root)
    if twigs.faces:
        twigs.to_object("tree_twigs", mats["wood_dark"], root)
    return root

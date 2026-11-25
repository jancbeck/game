"""Macro history of the courtyard floor: where mud lies, where setts have sunk or are gone.

Pure numpy, no camera. Helpers: `cw` is the cobble_wet module (its numpy helpers and constants).
Everything is in world meters on the same grid as cobble_wet's maps (row 0 at MAP_Y0).

What it makes, in four fields of 0..1:

    mud    where the floor is under mud: a ragged band along every wall foot that widens in the
           corners, a worn apron around the well, the cookhouse, the forge, the stable and the
           gallows, the cart park, and the worn tracks between them. The shader cuts it with
           noise and with a threshold of each sett's own, so the edge follows the stones.
    sunk   where setts have sunk into the ground: wide mud joints, low and tilted tops. A ring
           around the mud, and patches along tracks and walls.
    trail  the worn track from the gate to the well and to the forge and stable: dark, smooth setts.
    moss   damp green on the stone at the wall feet.

`yard_mask` is the free floor that connects to the middle of the courtyard.
`CACHE` keeps the finished maps of a build, so the floor material and the prop that scatters
litter over it share one calculation.
"""

import math

import numpy as np

CACHE = {}

MUD_BAND = (0.40, 0.95, 1.5)  # wall foot band: least width m, extra width from the noise, extra width in a corner
SPOT_RAGGED = 0.30  # how much the outline of a worn apron strays, in units of its radius
SUNK_PATCHES = 22  # random patches of sunk setts
SUNK_RADIUS = (0.5, 1.3)  # meters


def yard_mask(cw, X, Y, plan, d_wall):
    """1 on the free floor that connects to the middle of the courtyard, 0 behind the walls, soft at the edge."""
    st = 6
    xs, ys, d = X[::st, ::st], Y[::st, ::st], d_wall[::st, ::st]
    free = cw._in_polygon(xs, ys, plan["platform"]["polygon"]) & (d > 0.02)
    region = np.zeros_like(free)
    i, j = int((-3.0 - cw.MAP_Y0) * cw.PPM / st), int((0.0 - cw.MAP_X0) * cw.PPM / st)
    region[i, j] = free[i, j]
    for _ in range(2000):
        grown = region.copy()
        grown[1:, :] |= region[:-1, :]
        grown[:-1, :] |= region[1:, :]
        grown[:, 1:] |= region[:, :-1]
        grown[:, :-1] |= region[:, 1:]
        grown &= free
        if (grown == region).all():
            break
        region = grown
    up = np.repeat(np.repeat(region, st, axis=0), st, axis=1)
    pad = np.zeros((cw.MAP_H, cw.MAP_W), bool)
    h, w = min(up.shape[0], cw.MAP_H), min(up.shape[1], cw.MAP_W)
    pad[:h, :w] = up[:h, :w]
    for _ in range(st):  # the coarse region grown by one of its cells, then cut by the free floor at full resolution
        grown = pad.copy()
        grown[1:, :] |= pad[:-1, :]
        grown[:-1, :] |= pad[1:, :]
        grown[:, 1:] |= pad[:, :-1]
        grown[:, :-1] |= pad[:, 1:]
        pad = grown
    fine = pad & cw._in_polygon(X, Y, plan["platform"]["polygon"]) & (d_wall > 0.02)
    return np.clip(cw._blur(fine.astype(np.float32), 0.04), 0.0, 1.0)


def _ellipse(cw, X, Y, c, rx, ry, rot, ragged):
    """1 inside an ellipse with a ragged outline, soft to 0 outside."""
    cs, sn = math.cos(rot), math.sin(rot)
    u = ((X - c[0]) * cs + (Y - c[1]) * sn) / rx
    v = (-(X - c[0]) * sn + (Y - c[1]) * cs) / ry
    return cw._smooth(1.08, 0.5, np.hypot(u, v) + SPOT_RAGGED * ragged)


def macro_fields(cw, X, Y, Xw, Yw, s, d_wall, corner, wander, traffic, shadow, yard, patchy):
    """The four fields of the module docstring, as a dict of (MAP_H, MAP_W) float32 arrays."""
    big = cw._fbm(cw._stream("mud_big"), 2.8, 3)
    mid = cw._fbm(cw._stream("mud_mid"), 1.0, 2)
    ragged = 0.6 * mid + 0.4 * cw._fbm(cw._stream("mud_fine"), 0.4, 2)
    smooth = cw._smooth

    # ---- wall feet: a band that wanders in width, wider in corners
    width = MUD_BAND[0] + MUD_BAND[1] * smooth(-0.9, 0.9, big) + MUD_BAND[2] * corner
    band = np.maximum(smooth(width, 0.0, d_wall + wander) * (0.78 + 0.22 * smooth(-1.0, 1.0, mid)),
                      smooth(0.7, 0.32, d_wall + 0.5 * wander) * 0.95)  # next to the wall it is mud everywhere

    # ---- worn aprons: each is an ellipse with a ragged outline
    stable, stable_rot = s["stable"]
    forge, forge_rot = s["forge"]
    gx, gy = s["gate"]
    spots = [
        (s["well"], 3.0, 2.6, 0.0, 0.95),
        ((s["shed"][0] + 0.3, s["shed"][1] - 2.3), 3.1, 1.5, 0.0, 0.9),
        (s["brazier2"], 2.0, 1.5, 0.0, 0.85),
        (stable(0.0, -2.8), 2.7, 2.2, stable_rot, 0.95),
        (stable(0.0, -5.2), 2.0, 1.2, stable_rot, 0.7),
        (forge(0.4, -1.7), 2.7, 2.1, forge_rot, 0.9),
        (s["gallows"], 2.5, 2.1, math.radians(-46.0), 0.9),
        ((s["cart"][0] - 0.2, s["cart"][1] + 0.2), 2.0, 1.7, 0.4, 0.85),
        ((gx - 3.4, gy - 3.6), 2.1, 1.3, 0.1, 0.75),
        ((gx + 2.8, gy - 3.4), 1.8, 1.2, -0.2, 0.7),
    ]
    apron = np.zeros_like(X)
    for c, rx, ry, rot, w in spots:
        apron = 1.0 - (1.0 - apron) * (1.0 - w * _ellipse(cw, Xw, Yw, c, rx, ry, rot, ragged))

    # ---- worn tracks: gate to well, gate to forge and cart, gate to stable and shed
    trail = np.zeros_like(X)
    for name, pts, half, weight, _ in cw._paths(s):
        if name not in ("well road", "cart road", "stable road", "shed road", "gate road"):
            continue
        d = cw._polyline(Xw, Yw, cw._spline(pts))[0]
        t = smooth(half * 1.25, half * 0.35, d) * np.clip(0.85 + 0.2 * patchy, 0.0, 1.0)
        trail = np.maximum(trail, t * (0.75 + 0.25 * weight))
    path = smooth(0.18, 0.7, traffic)

    mud = 1.0 - (1.0 - band * 0.95) * (1.0 - apron) * (1.0 - path * 0.85) * (1.0 - trail * 0.95)
    mud *= 1.0 - 0.45 * shadow * (1.0 - np.maximum(traffic, apron))  # a roof keeps the rain off the far corners
    mud = np.clip(mud * (0.86 + 0.14 * smooth(-1.0, 1.0, big)), 0.0, 1.0) * (0.3 + 0.7 * yard)

    # ---- sunk setts: a ring around the mud, and patches along tracks and walls
    ring = smooth(0.22, 0.42, mud) * smooth(0.92, 0.55, mud) * (0.45 + 0.55 * smooth(-0.8, 0.8, mid))
    sunk = ring.astype(np.float32)
    rng = cw._stream("sunk")
    weight = np.clip(yard, 0.0, 1.0) * (0.25 + 0.9 * traffic * (1.0 - traffic) * 4.0 + 0.8 * np.exp(-d_wall / 1.4))
    weight[d_wall < 0.35] = 0.0
    flat = weight.ravel().astype(np.float64)
    flat /= flat.sum()
    for k in rng.choice(flat.size, size=SUNK_PATCHES, replace=False, p=flat):
        i, j = divmod(int(k), cw.MAP_W)
        cx, cy = cw.MAP_X0 + (j + 0.5) / cw.PPM, cw.MAP_Y0 + (i + 0.5) / cw.PPM
        rx, ry = rng.uniform(*SUNK_RADIUS), rng.uniform(*SUNK_RADIUS) * 0.7
        sunk = np.maximum(sunk, 0.9 * _ellipse(cw, X, Y, (cx, cy), rx, ry, rng.uniform(0, math.pi), ragged))
    sunk *= 0.3 + 0.7 * yard

    # ---- moss on the damp stone at the wall feet, mostly where the rain does not wash it
    moss = smooth(1.5, 0.25, d_wall) * smooth(-0.3, 0.9, cw._fbm(cw._stream("moss"), 1.5, 2)) * (1.0 - 0.8 * traffic)
    moss *= 0.4 + 0.6 * yard

    return {"mud": mud.astype(np.float32), "sunk": np.clip(sunk, 0.0, 1.0).astype(np.float32),
            "trail": trail.astype(np.float32), "moss": moss.astype(np.float32)}


def get_maps(cw, plan):
    """The finished maps of cobble_wet.ground_maps(plan), computed once per build."""
    import json
    key = json.dumps([plan.get("blocks"), plan.get("props"), plan.get("platform")], sort_keys=True, default=str)
    if key not in CACHE:
        CACHE.clear()
        CACHE[key] = cw._ground_maps(plan)
    return CACHE[key]

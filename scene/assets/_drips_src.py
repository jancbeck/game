"""Where water leaves the buildings: the drip points of assets/drips.py, read from the location's plan.json.

Nothing is typed in twice. Every prop that sheds water is found in the plan by name, placed with its
own position and rotation, and its eave line is taken from the prop's own module (the shed's
`surface()`, the stable's eave constants, the gallows' beam). Each source returns `Drip` records:

    x, y, z    where the water leaves the edge (world meters)
    heading    unit (x, y) pointing away from the edge: the way the water arcs out
    hv         horizontal speed factor: the water is `hv * sqrt(h)` out after falling h meters
    flow       0..1: thin dribble to thick stream
    z_land     height of whatever the water lands on
    patch      True where the landing is a floor that stays mirror-wet

`Ctx.ground` finds what lies below a point: the top of a wall or tower it falls onto, the courtyard
floor, or the lower ward. It returns (None, False) where a strand would hit a prop's own detail (the
shaft of the well, the gallows stair, the lever); such strands are dropped, as are strands that would
land in a bucket that has drips of its own.
"""

import math
from collections import namedtuple

from . import _drips_geo as geo

Drip = namedtuple("Drip", "x y z heading hv flow z_land patch")


class Frame:
    """Placement of a prop: local (x, y) to world, as build_scene.place_asset does it."""

    def __init__(self, pos, rot_deg=0.0, scale=1.0, z=0.0):
        self.px, self.py = pos[0], pos[1]
        self.s = scale if not isinstance(scale, (list, tuple)) else scale[0]
        self.c, self.sn = math.cos(math.radians(rot_deg)), math.sin(math.radians(rot_deg))
        self.z = z

    def pt(self, lx, ly):
        return (self.px + self.s * (lx * self.c - ly * self.sn), self.py + self.s * (lx * self.sn + ly * self.c))

    def dir(self, dx, dy):
        return (dx * self.c - dy * self.sn, dx * self.sn + dy * self.c)

    def loc(self, wx, wy):
        dx, dy = wx - self.px, wy - self.py
        return ((dx * self.c + dy * self.sn) / self.s, (-dx * self.sn + dy * self.c) / self.s)


class Ctx:
    """The plan, seen as obstacles: block tops, the floor polygon and the buckets that have their own drips."""

    def __init__(self, plan):
        self.plan = plan
        self.heights = plan["heights"]
        self.lower = self.heights["lower_ward"]
        self.poly = [tuple(p) for p in plan["platform"]["polygon"]]
        self.blocks = []
        for key, b in plan["blocks"].items():
            if key.startswith("_"):
                continue
            h = b["h"]
            h = self.heights[h] if isinstance(h, str) else h
            if "from" in b:
                (ax, ay), (bx, by) = b["from"], b["to"]
                length = math.hypot(bx - ax, by - ay) + b["t"] * 0.5
                self.blocks.append((((ax + bx) / 2, (ay + by) / 2), (length / 2, b["t"] / 2),
                                    math.atan2(by - ay, bx - ax), h))
            else:
                self.blocks.append((tuple(b["center"]), (b["size"][0] / 2, b["size"][1] / 2),
                                    math.radians(b.get("rot_z", 0)), h))
        self.buckets = [tuple(p["pos"]) for k, p in plan["props"].items()
                        if not k.startswith("_") and k.split("#")[0].startswith("drip_bucket")]
        self.extra = []      # obstacle functions (x, y, z_from) -> (z, patch) or None

    def _in_poly(self, x, y):
        inside = False
        pts = self.poly
        for i in range(len(pts)):
            (ax, ay), (bx, by) = pts[i], pts[(i + 1) % len(pts)]
            if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
                inside = not inside
        return inside

    def ground(self, x, y, z_from):
        """(z, patch) of what water falling from z_from lands on at (x, y)."""
        for fn in self.extra:
            hit = fn(x, y, z_from)
            if hit is not None:
                return hit
        best = None
        for (cx, cy), (hw, hd), rot, top in self.blocks:
            dx, dy = x - cx, y - cy
            lx = dx * math.cos(rot) + dy * math.sin(rot)
            ly = -dx * math.sin(rot) + dy * math.cos(rot)
            if abs(lx) < hw and abs(ly) < hd and top <= z_from + 1e-3:
                best = top if best is None else max(best, top)
        if best is not None:
            return best, True
        return (0.0 if self._in_poly(x, y) else self.lower), True

    def near_bucket(self, x, y, r=0.32):
        return any(math.hypot(x - bx, y - by) < r for bx, by in self.buckets)


def _settle(ctx, x, y, z, heading, hv, flow):
    """Landing point and surface of water leaving (x, y, z); None when it lands where it should not."""
    lean = geo.WIND if flow >= 0.5 else (geo.WIND[0] * 0.5, geo.WIND[1] * 0.5)
    zl, patch = ctx.ground(x, y, z)
    for _ in range(3):
        if zl is None:
            return None
        dx, dy = geo.lateral(z - zl, heading, hv, lean)
        z_new, patch = ctx.ground(x + dx, y + dy, z)
        if z_new is None:
            return None
        if abs(z_new - zl) < 1e-3:
            break
        zl = z_new
    lx, ly = x + dx, y + dy
    if z - zl < 0.3 or ctx.near_bucket(lx, ly):
        return None
    return lx, ly, zl, patch


def _along(fr, ctx, rng, x0, x1, y, zfn, head, gap, heavy, hv, skip=None, fixed_x=False):
    """Drip points every `gap` meters along a local line, from local x0 to x1 (or y0 to y1 when
    `fixed_x`: then `y` is the fixed local x and the line runs along local y)."""
    out = []
    t = x0 + rng.uniform(0.0, gap[1]) * 0.6
    hx, hy = fr.dir(*head)
    while t < x1:
        lx, ly = (y, t) if fixed_x else (t, y)
        t += rng.uniform(*gap)
        if skip and skip(lx, ly):
            continue
        flow = rng.uniform(0.5, 1.0) if rng.random() < heavy else rng.uniform(0.05, 0.45)
        speed = rng.uniform(*hv)
        wx, wy = fr.pt(lx, ly)
        z = fr.z + fr.s * zfn(lx, ly)
        hit = _settle(ctx, wx, wy, z, (hx, hy), speed, flow)
        if hit is None:
            continue
        out.append(Drip(wx, wy, z, (hx, hy), speed, flow, hit[2], hit[3]))
    return out


# ---- sources --------------------------------------------------------------------------------

def shed(fr, ctx, rng):
    """Cookhouse lean-to: the whole eave under the fascia, and the right-hand barge edge."""
    from . import _shed_roof as roof

    def eave_z(x, _):
        return roof.surface(x, roof.Y_F) + 0.035 - 0.21 - 0.015 * math.sin(x * 5.0) - 0.01

    def barge_z(_, y):
        return roof.surface(roof.X_R, y) + 0.035 - 0.2 - 0.01

    out = _along(fr, ctx, rng, roof.X_L + 0.12, roof.X_R - 0.05, roof.Y_F - 0.045, eave_z, (0, -1),
                 gap=(0.06, 0.17), heavy=0.6, hv=(0.07, 0.14))
    out += _along(fr, ctx, rng, 0.6, roof.Y_W - 0.35, roof.X_R + 0.05, barge_z, (1, 0), gap=(0.25, 0.55),
                  heavy=0.3, hv=(0.05, 0.1), fixed_x=True)
    return out


def stable(fr, ctx, rng):
    from . import stable as st
    return _along(fr, ctx, rng, -st.ROOF_HALF + 0.05, st.ROOF_HALF - 0.05, st.EAVE_Y - 0.035,
                  lambda x, y: st.Z_EAVE - 0.10 - 0.085 - 0.01, (0, -1),
                  gap=(0.09, 0.26), heavy=0.5, hv=(0.07, 0.14))


def well(fr, ctx, rng):
    """Both eaves of the gable roof. Water that falls inside the drum would land on the rim or in the shaft."""
    from . import well as w

    def drum(x, y, z_from):
        lx, ly = fr.loc(x, y)
        r = math.hypot(lx, ly)
        if r < w.R_IN + 0.03:
            return None, False                      # shaft: caller drops it
        if r < 0.86:
            return w.HEIGHT, False                  # capstones
        return None

    ctx.extra.append(drum)
    out = []
    for s in (-1, 1):
        out += _along(fr, ctx, rng, -1.02, 1.02, s * 0.89, lambda x, y: 2.12, (0, s), gap=(0.09, 0.26),
                      heavy=0.4, hv=(0.06, 0.12))
    ctx.extra.remove(drum)
    return out


def gallows(fr, ctx, rng):
    """Crossbeam (two edges and both ends), and the deck rim: drip strings, a few streams."""
    from . import gallows as g

    def deck(x, y, z_from):
        lx, ly = fr.loc(x, y)
        if abs(lx) < g.HX - 0.08 and abs(ly) < g.HY - 0.08 and z_from > g.DECK_TOP + 0.2:
            if abs(lx - 0.92) < 0.2 and abs(ly - 0.2) < 0.2:          # lever
                return None, False
            return g.DECK_TOP, False
        if -g.HX - 1.85 < lx < -g.HX + 0.05 and -1.2 < ly < 0.2:    # the stair
            return None, False
        return None

    ctx.extra.append(deck)
    z_beam = fr.z + g.BEAM_Z - g.BEAM_HZ - 0.005
    out = []
    near_post = lambda lx: min(abs(lx - 1.4), abs(lx + 1.4)) < 0.2     # noqa: E731
    for ly in (g.BEAM_Y - g.BEAM_HY - 0.01, g.BEAM_Y + g.BEAM_HY + 0.01):
        sy = -1 if ly < g.BEAM_Y else 1
        out += _along(fr, ctx, rng, -1.8, 1.8, ly, lambda x, y: z_beam - fr.z, (0, sy), gap=(0.28, 0.75),
                      heavy=0.12, hv=(0.02, 0.06),
                      skip=lambda lx, ly_: near_post(lx) or abs(lx - 0.07) < 0.16 or (ly_ < g.BEAM_Y and abs(lx + 0.68) < 0.2))
    for sx in (-1, 1):                                              # end grain: water gathers and lets go
        wx, wy = fr.pt(sx * (g.BEAM_L / 2 + 0.01), g.BEAM_Y)
        hx, hy = fr.dir(sx, 0)
        hit = _settle(ctx, wx, wy, z_beam, (hx, hy), 0.05, 0.55)
        if hit:
            out.append(Drip(wx, wy, z_beam, (hx, hy), 0.05, 0.55, hit[2], hit[3]))
    rim_z = g.DECK_TOP - 0.24
    out += _along(fr, ctx, rng, -1.6, 1.6, -g.HY - 0.085, lambda x, y: rim_z, (0, -1), gap=(0.14, 0.42),
                  heavy=0.2, hv=(0.05, 0.1))
    out += _along(fr, ctx, rng, -1.0, 1.0, g.HX + 0.09, lambda x, y: rim_z, (1, 0), gap=(0.25, 0.6),
                  heavy=0.12, hv=(0.05, 0.1), fixed_x=True)
    out += _along(fr, ctx, rng, -1.5, 1.5, g.HY + 0.085, lambda x, y: rim_z, (0, 1), gap=(0.3, 0.7),
                  heavy=0.12, hv=(0.05, 0.1))
    ctx.extra.remove(deck)
    return out


def lit_door(fr, ctx, rng):
    """Stone door-case: water drips off the front edge of the drip course above the lintel."""
    from . import lit_door as ld

    def step(x, y, z_from):
        lx, ly = fr.loc(x, y)
        if abs(lx - 0.04) < 0.73 and -1.02 < ly < -ld.DEPTH + 0.02:
            return fr.z + 0.12, False
        return None

    ctx.extra.append(step)
    out = _along(fr, ctx, rng, -0.98, 0.98, -(ld.DEPTH + 0.12) - 0.015, lambda x, y: ld.HEIGHT + 0.335, (0, -1),
                 gap=(0.12, 0.34), heavy=0.28, hv=(0.05, 0.11))
    ctx.extra.remove(step)
    return out


def gatehouse_spouts(ctx, rng):
    """Stone spouts at the foot of the gatehouse parapet, under two crenels, throwing the roof water out.

    Returns (drips, spouts) where each spout is (x, y_face, z) for the stone block on the wall.
    """
    b = ctx.plan["blocks"].get("gatehouse")
    if not b:
        return [], []
    cx, cy = b["center"]
    face = cy - b["size"][1] / 2
    top = ctx.heights[b["h"]] if isinstance(b["h"], str) else b["h"]
    drips, spouts = [], []
    for dx in (-3.25, -0.65):
        x = cx + dx
        z = top + 0.02
        y = face - 0.46
        spouts.append((x, face, z))
        hv = rng.uniform(0.28, 0.34)
        hit = _settle(ctx, x, y, z, (0.0, -1.0), hv, 1.0)
        if hit:
            drips.append(Drip(x, y, z, (0.0, -1.0), hv, 1.0, hit[2], hit[3]))
    return drips, spouts


SOURCES = {"shed": shed, "stable": stable, "well": well, "gallows": gallows}


def _safely(name, fn, *args):
    """Run one source. A prop that was changed so that the constants this module reads are gone drops
    its own drips and says so; it never stops the scene from building."""
    ctx = next(a for a in args if isinstance(a, Ctx))
    kept = list(ctx.extra)
    try:
        return fn(*args)
    except (AttributeError, ImportError, KeyError, TypeError, ValueError) as err:
        print(f"drips: source {name!r} skipped: {err!r}")
        ctx.extra[:] = kept
        return []


def collect(plan, rng):
    """All drip points of the plan, plus the spout blocks to build. Returns (drips, spouts)."""
    ctx = Ctx(plan)
    drips = []
    for key, p in plan["props"].items():
        if key.startswith("_"):
            continue
        fn = SOURCES.get(key.split("#")[0])
        if fn is None:
            continue
        z = p.get("z", 0.0)
        fr = Frame(p["pos"], p.get("rot_z", 0.0), p.get("scale", 1.0), z if isinstance(z, (int, float)) else 0.0)
        drips += _safely(key, fn, fr, ctx, rng)
    for key, m in plan["mounted"].items():
        if key.startswith("_") or key.split("#")[0] != "lit_door":
            continue
        fr = Frame(m["pos"][:2], m.get("rot_z", 0.0), m.get("scale", 1.0), m["pos"][2])
        drips += _safely(key, lit_door, fr, ctx, rng)
    spouts = []
    got = _safely("gatehouse", gatehouse_spouts, ctx, rng)
    if got:
        spout_drips, spouts = got
        drips += spout_drips
    return drips, spouts

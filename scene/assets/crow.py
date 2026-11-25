"""Perched raven or crow, about 0.45-0.6 m from beak to tail tip, head toward -Y. Origin at the feet.

rng picks one of seven postures, a mirror side and a size. The set is chosen so that each
reads as a different silhouette at 25 px: alert (neck stretched), look (head turned, in
profile), hunch (rain-sunk head, fluffed ball), preen (beak in the shoulder), caw (head
thrown back, bill open), droop (wings held loose and open to shed rain) and hop (feet off
the ground, wings half raised). The silhouette carries the read against dark stone: full
chest, heavy curved bill, folded wings crossing over a wedge tail, thin legs with spread toes.
Also exports make_tf, head_and_beak, tail_fan and tag_vane for the flying raven.
"""

import math

from mathutils import Matrix, Vector

from ._sweep import blade, curve, ribbons, smooth, sweep

LIGHTS = []

# body-frame rings along +Y (tail): y, center z, half width, half height
BODY = [(-0.125, 0.030, 0.030, 0.034), (-0.105, 0.018, 0.047, 0.050), (-0.070, 0.004, 0.062, 0.064),
        (-0.020, 0.000, 0.068, 0.068), (0.040, -0.004, 0.064, 0.064), (0.095, -0.012, 0.048, 0.048),
        (0.140, -0.020, 0.030, 0.030), (0.175, -0.026, 0.010, 0.012)]

# posture table. tilt: body pitch in degrees (negative raises the chest); head: body-frame head
# center; yaw: head turn about Z; droop: bill angle below horizontal (negative points up);
# via: neck control point; gape: bill opening at the tip in meters; tail: tail lift in degrees;
# lift: height of the feet above the perch; wings: None (folded) or (arm, hand, curl, span scale)
POSTURES = {
    "alert": dict(weight=2, tilt=-34, head=(0.0, -0.150, 0.092), yaw=(-12, 12), droop=6,
                  via=(0.0, -0.118, 0.062), fluff=1.0, tail=16),
    "look": dict(weight=3, tilt=-30, head=(0.014, -0.135, 0.078), yaw=(55, 85), droop=10,
                 via=(0.010, -0.110, 0.055), fluff=1.0, tail=16, turn=True),
    "hunch": dict(weight=3, tilt=-12, head=(0.0, -0.098, 0.044), yaw=(-15, 15), droop=16,
                  via=(0.0, -0.086, 0.034), fluff=1.16, tail=8),
    "preen": dict(weight=2, tilt=-24, head=(0.062, -0.030, 0.056), yaw=(140, 165), droop=18,
                  via=(0.045, -0.085, 0.07), fluff=1.04, tail=16, turn=True, back=True),
    "caw": dict(weight=2, tilt=-42, head=(0.0, -0.108, 0.118), yaw=(-10, 10), droop=-26,
                via=(0.0, -0.094, 0.076), fluff=1.0, tail=22, gape=0.05),
    "droop": dict(weight=2, tilt=-20, head=(0.0, -0.128, 0.064), yaw=(-14, 14), droop=14,
                  via=(0.0, -0.105, 0.045), fluff=1.06, tail=10, wings=(4, -42, 0.0, 0.9)),
    "hop": dict(weight=2, tilt=-6, head=(0.0, -0.138, 0.050), yaw=(-12, 12), droop=10,
                via=(0.0, -0.110, 0.040), fluff=1.0, tail=26, lift=0.075,
                wings=(42, 14, -0.02, 0.8)),
}


def make_tf(pitch_deg, origin, k, roll_deg=0.0):
    """Map body-frame points (scaled by k) into root space after a pitch about X and a roll about Y."""
    m = Matrix.Rotation(math.radians(roll_deg), 3, "Y") @ Matrix.Rotation(math.radians(pitch_deg), 3, "X")
    o = Vector(origin)
    return lambda p: o + m @ (Vector(p) * k)


def tag_vane(ob):
    """Mark a flat feather ribbon: the plumage shader keeps vanes matte and dark."""
    attr = ob.data.attributes.new("vane", "FLOAT", "POINT")
    attr.data.foreach_set("value", [1.0] * len(ob.data.vertices))
    return ob


def head_and_beak(kit, mat, parent, tf, k, tilt, head, yaw_deg, droop_deg, via=None,
                  neck_from=(0.0, -0.10, 0.03), gape=0.0):
    """Neck, head, throat tuft and a curved two-part bill; yaw turns the face about Z.

    gape opens the bill: the lower half drops three quarters of it at the tip, the upper rises the rest.
    """
    H = Vector(head)
    yaw, dr = math.radians(yaw_deg), math.radians(droop_deg)
    d = Vector((math.sin(yaw) * math.cos(dr), -math.cos(yaw) * math.cos(dr), -math.sin(dr)))
    down = Vector((0, 0, -1))

    ctrl = [neck_from] + ([via] if via else []) + [tuple(H)]
    sweep(kit, "neck", [tf(p) for p in curve(ctrl, 0.02)], [0.040 * k, 0.034 * k, 0.030 * k],
          [0.038 * k, 0.032 * k, 0.029 * k], mat, parent, sides=10)
    smooth(kit.sphere("head", 1.0, tf(H), scale=(0.036 * k, 0.045 * k, 0.037 * k),
                      rot_deg=(tilt, 0, yaw_deg), mat=mat, segments=14, parent=parent))
    smooth(kit.sphere("throat", 1.0, tf(H + Vector((0, 0.012, -0.026)) + d * 0.01),
                      scale=(0.025 * k, 0.031 * k, 0.026 * k), rot_deg=(tilt, 0, yaw_deg), mat=mat,
                      segments=10, parent=parent))

    up_ctrl = [H + d * 0.018, H + d * 0.050 + down * (0.002 - gape * 0.08), H + d * 0.095 + down * (0.013 - gape * 0.25)]
    sweep(kit, "beak_upper", [tf(p) for p in curve(up_ctrl, 0.015)], [0.0185 * k, 0.0150 * k, 0.0028 * k],
          [0.0215 * k, 0.0175 * k, 0.0034 * k], mat, parent, sides=6)
    lo_ctrl = [H + d * 0.016 + down * 0.012, H + d * 0.048 + down * (0.015 + gape * 0.4),
               H + d * 0.083 + down * (0.017 + gape * 0.75)]
    sweep(kit, "beak_lower", [tf(p) for p in curve(lo_ctrl, 0.015)], [0.0135 * k, 0.0105 * k, 0.0024 * k],
          [0.0090 * k, 0.0070 * k, 0.0022 * k], mat, parent, sides=6)


def tail_fan(kit, mat, parent, tf, count=5, step_deg=7.0, length=0.32, base=(0.0, 0.12, -0.02),
             lift=8.0, width=0.034):
    """Wedge of overlapping tail feathers; the middle pair is longest."""
    mid = (count - 1) / 2
    up = math.radians(lift)
    blades = []
    for i in range(count):
        a = math.radians((i - mid) * step_deg)
        d = Vector((math.sin(a) * math.cos(up), math.cos(a) * math.cos(up), math.sin(up)))
        side = Vector((math.cos(a), -math.sin(a), 0.0))
        blades.append(blade(Vector(base) + side * (0.004 * (i - mid)), d, side,
                            length * (1.0 - 0.05 * abs(i - mid) / max(mid, 1)), width,
                            bend=(0, 0, -0.012)))
    return tag_vane(ribbons(kit, "tail", blades, mat, parent, tf))


def build(kit, mats, rng):
    from .crow_flying import Wing, _wing

    root = kit.group("crow")
    bird = mats["feather"]
    # carrion crows run 0.45-0.5 m and ravens 0.6 m, so a few big birds sit among the small ones
    k = 0.86 * rng.choice((0.96, 1.0, 1.05, 1.1, 1.18)) * rng.uniform(0.97, 1.03)
    side = rng.choice((-1, 1))
    mode = rng.choices(list(POSTURES), weights=[p["weight"] for p in POSTURES.values()])[0]
    P = POSTURES[mode]
    root["pose"] = mode
    tilt, fluff = P["tilt"], P["fluff"]
    head = (side * P["head"][0], P["head"][1], P["head"][2])
    yaw = rng.uniform(*P["yaw"]) * (side if P.get("turn") else 1)
    if P.get("back"):
        yaw = -side * rng.uniform(*P["yaw"])
    lift = P.get("lift", 0.0)
    tf = make_tf(tilt, (0.0, 0.0, 0.163 * k + lift), k)

    # torso: smooth loft from neck base to rump
    ctrl = [(0.0, y, cz) for y, cz, _, _ in BODY]
    sweep(kit, "body", [tf(p) for p in ctrl],
          [r * k * fluff for _, _, r, _ in BODY], [r * k * fluff for _, _, _, r in BODY],
          bird, root, sides=14)

    via = (side * P["via"][0], P["via"][1], P["via"][2])
    head_and_beak(kit, bird, root, tf, k, tilt, head, yaw, P["droop"], via=via, gape=P.get("gape", 0.0))

    if "wings" in P:
        arm, hand, curl, span = P["wings"]
        pose = dict(arm=arm, hand=hand, curl=curl, sweep=0.10)
        shoulder = Vector((0.048, -0.030, 0.020))
        spread = lambda p: tf(shoulder + (Vector(p) - shoulder) * span)  # noqa: E731
        for sx in (1, -1):
            wing = Wing(sx, pose, rng.uniform(-4, 4), rng.uniform(-6, 6))
            _wing(kit, bird, root, spread, wing, pose, rng, "r" if sx > 0 else "l")
    else:
        # folded wings lying along the flanks, tips crossing the tail base
        for sx in (1, -1):
            path = [(sx * 0.058, -0.075, 0.022), (sx * 0.070, -0.02, 0.018), (sx * 0.073, 0.05, 0.004),
                    (sx * 0.066, 0.12, -0.010), (sx * 0.050, 0.20, -0.020), (sx * 0.034, 0.275, -0.028)]
            sweep(kit, f"wing_{'r' if sx > 0 else 'l'}", [tf(p) for p in curve(path, 0.025)],
                  [0.008 * k, 0.016 * k, 0.018 * k, 0.015 * k, 0.009 * k, 0.002 * k],
                  [0.026 * k, 0.045 * k, 0.050 * k, 0.040 * k, 0.024 * k, 0.006 * k], bird, root, sides=8)

    tail_fan(kit, bird, root, tf, length=0.26, lift=P["tail"], width=0.040)

    # legs: feathered thigh, thin tarsus, three toes forward and one back, curled to grip.
    # In a hop one leg reaches forward and the other trails.
    for sx in (1, -1):
        name = "r" if sx > 0 else "l"
        hip = tf((sx * 0.036, 0.015, -0.05))
        reach = (-0.05 if sx == side else 0.045) * k if lift else -0.006 * k
        ankle = Vector((hip.x, hip.y + reach, 0.012 * k + lift * (1.0 if sx == side else 0.85)))
        smooth(kit.sphere(f"thigh_{name}", 1.0, tf((sx * 0.040, 0.012, -0.040)),
                          scale=(0.026 * k, 0.040 * k, 0.034 * k), rot_deg=(tilt, 0, 0), mat=bird,
                          segments=10, parent=root))
        sweep(kit, f"tarsus_{name}", [hip, hip.lerp(ankle, 0.5) + Vector((0, -0.004 * k, 0)), ankle],
              [0.0075 * k, 0.0065 * k, 0.0062 * k], mat=bird, parent=root, sides=6)
        for n, (a, ln) in enumerate(((-26, 0.040), (0, 0.044), (26, 0.040), (180, 0.026))):
            fwd = Vector((math.sin(math.radians(a)), -math.cos(math.radians(a)), 0.0))
            sag = 0.0035 + (0.012 if lift else 0.0)
            toe = [ankle, ankle + fwd * ln * 0.55 * k + Vector((0, 0, -sag * k)),
                   ankle + fwd * ln * k + Vector((0, 0, -(sag + 0.002) * k))]
            sweep(kit, f"toe_{name}{n}", toe, [0.0048 * k, 0.0042 * k, 0.0018 * k], mat=bird,
                  parent=root, sides=5)
    return root

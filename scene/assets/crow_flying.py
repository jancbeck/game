"""Raven or crow in flight, wingspan 0.8-1.2 m, head toward -Y. Origin at the body center.

rng picks the wingbeat phase (up-stroke, glide or down-stroke), a small body pitch and bank,
and a size. Each wing is built in a flat (span u, chord v) layout and bent
into 3D by a dihedral that changes along the span: the arm and the hand can sit at
different angles, so the tips trail low on the up-stroke and curl up on the down-stroke.
Primaries are separated like fingers; secondaries and coverts overlap into a trailing edge.
The feather ribbons carry the `vane` attribute, which keeps them dark and matte in the plumage
shader; only the body, head, bill and wing bones are glossy.
"""

import math

from mathutils import Vector

from ._sweep import blade, ribbons, sweep
from .crow import head_and_beak, make_tf, tag_vane, tail_fan

LIGHTS = []

SHOULDER = (0.048, -0.030, 0.020)

# arm and hand dihedral in degrees (positive raises the wing), tip curl in meters, sweep-back
POSES = {
    "up": dict(arm=58.0, hand=20.0, curl=-0.035, sweep=0.12),
    "glide": dict(arm=9.0, hand=14.0, curl=0.025, sweep=0.09),
    "down": dict(arm=-26.0, hand=-4.0, curl=0.055, sweep=0.06),
}
BODY = [(-0.125, 0.012, 0.028, 0.028), (-0.100, 0.008, 0.045, 0.045), (-0.060, 0.000, 0.056, 0.056),
        (-0.010, -0.002, 0.058, 0.056), (0.045, -0.006, 0.050, 0.050), (0.095, -0.010, 0.036, 0.036),
        (0.135, -0.014, 0.022, 0.022), (0.162, -0.016, 0.008, 0.010)]


def _smoothstep(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


class Wing:
    """Maps flat wing coordinates (u outward, v back, w off the surface) into the body frame."""

    def __init__(self, sx, pose, arm_off, hand_off):
        self.sx = sx
        self.sweep = pose["sweep"]
        a, h = pose["arm"] + arm_off, pose["hand"] + hand_off
        du, self.table = 0.01, [(0.0, 0.0, math.radians(a))]
        x = z = 0.0
        for i in range(1, 61):
            th = math.radians(a + (h - a) * _smoothstep((i * du - 0.13) / 0.22))
            x += math.cos(th) * du
            z += math.sin(th) * du
            self.table.append((x, z, th))
        self.du = du

    def edge(self, u):
        """Leading-edge chord position: slightly back along the arm, swept back over the hand."""
        return -0.03 + 0.025 * min(u, 0.17) / 0.17 + self.sweep * max(0.0, (u - 0.17) / 0.3) ** 1.4

    def __call__(self, p):
        u, v, w = p
        f = min(max(u / self.du, 0.0), len(self.table) - 1.001)
        i = int(f)
        t = f - i
        x0, z0, th0 = self.table[i]
        x1, z1, th1 = self.table[i + 1]
        x, z, th = x0 + (x1 - x0) * t, z0 + (z1 - z0) * t, th0 + (th1 - th0) * t
        return Vector((self.sx * (SHOULDER[0] + x - w * math.sin(th)), SHOULDER[1] + v,
                       SHOULDER[2] + z + w * math.cos(th)))


def _wing(kit, mat, root, tf, wing, pose, rng, name):
    j = lambda a: rng.uniform(-a, a)  # noqa: E731
    flat = lambda p: tf(wing(p))  # noqa: E731
    curl = pose["curl"]
    blades = []

    # coverts over the arm give the wing body; primaries and secondaries carry the outline
    for n in range(8):                                  # secondaries, trailing edge of the arm
        u = 0.025 + 0.0185 * n
        v = wing.edge(u) + 0.045
        a = math.radians(5 + 1.5 * n + j(3))
        d = Vector((math.sin(a), math.cos(a), 0.0))
        blades.append(blade((u, v, 0.0), d, Vector((math.cos(a), -math.sin(a), 0.0)),
                            0.165 - 0.004 * n + j(0.006), 0.031, bend=(0, 0, -0.012 + curl * 0.3)))
    for n in range(7):                                  # primaries, fanned fingers of the hand
        u = 0.205 - 0.0125 * n
        v = wing.edge(u) + 0.035
        a = math.radians((4, 11, 20, 30, 41, 52, 62)[n] + j(2))
        d = Vector((math.cos(a), math.sin(a), 0.0))
        length = (0.235, 0.250, 0.255, 0.250, 0.235, 0.215, 0.190)[n] + j(0.008)
        blades.append(blade((u, v, 0.0), d, Vector((-math.sin(a), math.cos(a), 0.0)), length,
                            0.020 + 0.0013 * n, bend=(0.0, 0.02 * (1 - n / 7), curl * (1.0 - n * 0.08)),
                            rach=0.004))
    for n in range(8):                                  # greater coverts, short, above the secondaries
        u = 0.03 + 0.0185 * n
        v = wing.edge(u) + 0.04
        a = math.radians(6 + 1.5 * n)
        blades.append(blade((u, v, 0.005), Vector((math.sin(a), math.cos(a), 0.0)),
                            Vector((math.cos(a), -math.sin(a), 0.0)), 0.075, 0.030,
                            bend=(0, 0, -0.006)))
    for n in range(6):                                  # primary coverts
        u = 0.20 - 0.013 * n
        v = wing.edge(u) + 0.03
        a = math.radians((6, 14, 24, 35, 47, 58)[n])
        blades.append(blade((u, v, 0.005), Vector((math.cos(a), math.sin(a), 0.0)),
                            Vector((-math.sin(a), math.cos(a), 0.0)), 0.10, 0.022,
                            bend=(0, 0, curl * 0.4)))
    tag_vane(ribbons(kit, f"feathers_{name}", blades, mat, root, flat))

    # leading-edge pads: the arm and the hand bones under their feathers
    arm = [flat((u, wing.edge(u) + 0.045, 0.0)) for u in (0.0, 0.05, 0.10, 0.15, 0.20)]
    sweep(kit, f"arm_{name}", arm, [0.052, 0.054, 0.050, 0.044, 0.034], [0.015, 0.014, 0.012, 0.010, 0.007],
          mat, root, sides=8, step=0.02)
    hand = [flat((u, wing.edge(u) + 0.020, 0.0)) for u in (0.17, 0.21, 0.25, 0.29)]
    sweep(kit, f"hand_{name}", hand, [0.030, 0.024, 0.014, 0.004], [0.010, 0.008, 0.005, 0.002],
          mat, root, sides=6, step=0.02)


def build(kit, mats, rng):
    root = kit.group("crow_flying")
    bird = mats["feather"]
    k = rng.uniform(1.05, 1.25)
    name = rng.choice(("up", "glide", "down"))
    pose = POSES[name]
    pitch, roll = rng.uniform(-2, 9), rng.uniform(-14, 14)
    tf = make_tf(pitch, (0.0, 0.0, 0.0), k, roll)

    sweep(kit, "body", [tf((0.0, y, cz)) for y, cz, _, _ in BODY], [r * k for _, _, r, _ in BODY],
          [r * k for _, _, _, r in BODY], bird, root, sides=14)
    head_and_beak(kit, bird, root, tf, k, pitch, (0.0, -0.168, 0.016), rng.uniform(-9, 9),
                  rng.uniform(4, 12), neck_from=(0.0, -0.10, 0.012), via=(0.0, -0.135, 0.014))
    tail_fan(kit, bird, root, tf, count=7, step_deg=7.5, length=0.21, base=(0.0, 0.12, -0.014),
             lift=-4.0, width=0.036)

    for sx in (1, -1):
        wing = Wing(sx, pose, rng.uniform(-5, 5), rng.uniform(-5, 5))
        _wing(kit, bird, root, tf, wing, pose, rng, "r" if sx > 0 else "l")

        # legs tucked back against the belly
        leg = [tf((sx * 0.032, 0.040, -0.045)), tf((sx * 0.030, 0.085, -0.040)),
               tf((sx * 0.028, 0.130, -0.030))]
        sweep(kit, f"leg_{'r' if sx > 0 else 'l'}", leg, [0.0075 * k, 0.0065 * k, 0.0050 * k],
              mat=bird, parent=root, sides=6, step=0.02)
    return root

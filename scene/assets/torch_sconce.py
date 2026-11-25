"""Empty wall sconce: iron back plate, arm and two rings, a charred torch stub, a soot plume above.

No torch burns here: the sconce holds only the burnt-down stub of the last torch, black and split
at the top, and years of torches have left a soot plume on the stone above it, densest just over
the rings and fading out about 1.4 m up. The sconce has no light.

The module also provides the parts for a sconce that does burn (gate_door.py uses them):
bracket() builds the plate, arms and rings, burning_torch() the stick with its pitch-soaked head,
flames, embers and smoke, and TORCH_LIGHT is the light that belongs at its flame.

Origin is the mount point on the wall (XZ plane at y = 0); the torch sticks out toward -Y.
"""

import math

from . import _fire, _soot

LIGHTS = []
# light for a burning torch: at the flame, a hand's width in front of the wall, so the stone glows
# around the torch and not at a mirror point away from it (see _lights.py)
TORCH_LIGHT = dict(pos=(0.0, -0.34, 0.62), color=(1.0, 0.34, 0.06), watts=175.0, radius=0.15, specular=0.15,
                   reach=7.0)
VOLUME_FACTOR = 0.22          # share of a torch light that scatters in the haze and smoke

TILT = 15.0          # degrees, top of the torch leans toward -Y
BASE = (0.0, -0.07, -0.20)   # bottom end of the torch
SPARK_WIND = (0.9, 0.2)      # ember drift downwind in meters per meter of rise
FLAME_LEAN = (0.18, 0.04)    # flame lean in meters per meter of height

_S, _C = math.sin(math.radians(TILT)), math.cos(math.radians(TILT))
_TILT = (TILT, 0, 0)


def along(t):
    """Point on the torch axis, t meters up from its bottom end."""
    return (BASE[0], BASE[1] - t * _S, BASE[2] + t * _C)


def bracket(kit, mats, root):
    """Back plate with rivets and two rings, each on a short arm from the plate."""
    iron = mats["iron"]
    kit.box("plate", (0.14, 0.03, 0.30), (0, -0.015, 0), mat=iron, bevel=0.006, parent=root)
    for i, (x, z) in enumerate(((-0.045, 0.11), (0.045, 0.11), (-0.045, -0.11), (0.045, -0.11))):
        kit.cylinder(f"rivet_{i}", 0.012, 0.014, (x, -0.036, z), rot_deg=(90, 0, 0), mat=iron,
                     segments=8, parent=root)
    up = along(-BASE[2] / _C)
    low = along(0.08)
    kit.beam("arm_up", (0, -0.03, 0), (0, up[1] + 0.04, 0), section=(0.03, 0.03), mat=iron,
             bevel=0.004, parent=root)
    kit.torus("ring_up", 0.040, 0.010, up, rot_deg=_TILT, mat=iron, major_segments=16,
              minor_segments=5, parent=root)
    kit.beam("arm_low", (0, -0.03, low[2]), (0, low[1] + 0.035, low[2]), section=(0.028, 0.028),
             mat=iron, bevel=0.004, parent=root)
    kit.torus("ring_low", 0.036, 0.009, low, rot_deg=_TILT, mat=iron, major_segments=16,
              minor_segments=5, parent=root)


def burning_torch(kit, mats, rng, root):
    """Stick, rag-wrapped pitch head and an eight-tongue flame about 0.5 m tall, embers and smoke."""
    wood, rope, burlap = mats["wood_dark"], mats["rope"], mats["burlap"]
    fire, embers = mats["fire"], mats["embers"]
    kit.cylinder("stick", 0.026, 0.46, along(0.23), rot_deg=_TILT, mat=wood, segments=10,
                 radius_top=0.032, bevel=0.003, parent=root)
    kit.sphere("head", 0.062, along(0.50), scale=(1.0, 1.0, 1.55), rot_deg=_TILT, mat=burlap,
               segments=14, parent=root)
    for i, (t, r) in enumerate(((0.43, 0.050), (0.48, 0.060), (0.53, 0.062), (0.58, 0.052))):
        kit.torus(f"wrap_{i}", r, 0.008, along(t), rot_deg=_TILT, mat=rope, major_segments=14,
                  minor_segments=5, parent=root)
    kit.cylinder("char", 0.052, 0.045, along(0.585), rot_deg=_TILT, mat=wood, segments=12,
                 radius_top=0.058, parent=root)
    for i in range(3):
        a = 2 * math.pi * i / 3 + kit.jitter(rng, 0.5)
        p = along(0.44)
        kit.cylinder(f"rag_{i}", 0.009, 0.07, (p[0] + 0.055 * math.cos(a), p[1] + 0.055 * math.sin(a),
                                               p[2] - 0.02), rot_deg=(8 * math.sin(a), -8 * math.cos(a), 0),
                     mat=burlap, segments=5, radius_top=0.004, parent=root)
    top = along(0.605)
    kit.sphere("fuel", 0.052, top, scale=(1, 1, 0.5), rot_deg=_TILT, mat=embers, segments=12,
               parent=root)

    # one tall tongue with a bright narrow one inside it, four shorter ones licking out of the
    # sides and two low flickers, all leaning downwind
    base = (top[0], top[1], top[2] + 0.01)
    lx, ly = FLAME_LEAN
    #        dx,     dy,    height, radius, lean dx, lean dy, twist, phase
    tongues = ((0.000, 0.000, 0.56, 0.130, 0.04, -0.10, 1.4, 0.4),
               (0.004, -0.004, 0.36, 0.065, 0.02, -0.12, 1.1, 1.1),
               (-0.034, 0.010, 0.42, 0.098, -0.12, -0.04, -1.2, 2.0),
               (0.034, -0.012, 0.36, 0.092, 0.10, -0.08, 1.0, 4.0),
               (0.005, -0.044, 0.29, 0.078, 0.00, -0.22, 0.8, 5.3),
               (-0.028, -0.022, 0.25, 0.068, -0.20, -0.14, -0.9, 3.1),
               (0.040, 0.012, 0.20, 0.056, 0.22, 0.02, 1.3, 0.2),
               (-0.010, 0.034, 0.17, 0.050, -0.05, 0.12, -1.0, 2.7))
    for i, (dx, dy, h, r, ldx, ldy, tw, ph) in enumerate(tongues):
        _fire.flame(kit, fire, root, f"flame_{i}", (base[0] + dx, base[1] + dy, base[2] - 0.01), h, r,
                    lean=(lx + ldx, ly + ldy), twist=tw, phase=ph + kit.jitter(rng, 0.3))
    _fire.sparks(kit, embers, root, "sparks", rng, 6, (base[0], base[1], base[2] + 0.1), 0.9, 0.04,
                 SPARK_WIND, 0.04)
    _fire.smoke(kit, mats["smoke"], root, "smoke", (base[0], base[1], base[2] + 0.30),
                rise=0.55, drift=0.6, r0=0.08, r1=0.35, density=1.6, seed=rng.uniform(0, 50))


def stub(kit, mats, rng, root):
    """Burnt-down torch stub in the rings: a short stick, charred and split at the top."""
    wood = mats["wood_dark"]
    kit.cylinder("stub", 0.027, 0.24, along(0.12), rot_deg=_TILT, mat=wood, segments=10,
                 radius_top=0.024, bevel=0.003, parent=root)
    # the charred end: a ragged, shrunken crown of split wood and a scrap of burnt rag
    for i in range(4):
        a = 2 * math.pi * i / 4 + kit.jitter(rng, 0.4)
        p = along(0.25)
        kit.cylinder(f"stub_split_{i}", 0.010, 0.05 + kit.jitter(rng, 0.015),
                     (p[0] + 0.012 * math.cos(a), p[1] + 0.012 * math.sin(a), p[2]),
                     rot_deg=(TILT + 12 * math.sin(a), -12 * math.cos(a), 0), mat=wood, segments=5,
                     radius_top=0.003, parent=root)
    p = along(0.21)
    kit.torus("stub_rag", 0.030, 0.007, p, rot_deg=_TILT, mat=mats["burlap"], major_segments=10,
              minor_segments=4, parent=root)


def build(kit, mats, rng):
    root = kit.group("torch_sconce")
    bracket(kit, mats, root)
    stub(kit, mats, rng, root)
    # where the flames stood: from just over the rings up the wall, widening and fading
    _soot.plume(kit, root, "soot", (0.0, -0.004, 0.16), 0.62, 1.45, strength=0.85)
    return root

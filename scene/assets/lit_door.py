"""Small tower door, ajar, with lamplight from the room behind spilling out.

Origin: bottom center of the opening at ground level. The wall face is the XZ plane at y = 0 and
is not part of this prop; the wall is solid, so the door sits in a stone door-case that stands
0.62 m proud of it toward -Y.

Opening: 1.0 m wide, 2.0 m high, flat lintel. Case: jamb stones, lintel with a drip course, a
worn sill and one outer step; 1.9 m wide and 2.45 m high overall.

The plank leaf is hinged on the +X jamb, set back 0.22 m from the wall face, and swung
outward 28 degrees, so a gap about 0.21 m wide opens along the -X jamb. Behind the leaf is a
shallow room: plank floor, plank back wall with a batten and a hanging cloak, a ceiling beam
and a small oil lamp on a chain. Nothing emits except the lamp flame; everything else is lit by
point lights, so the interior reads through the gap and the light falls off over the sill, the
step and the ground. Three point lights: the lamp, one on the step outside the gap, one low on
the ground in front of the door.
"""

import math

from . import _fire

HALF = 0.5               # half the opening width
HEIGHT = 2.0             # opening height
DEPTH = 0.62             # how far the case stands out from the wall
JAMB_W = (0.32, 0.46)    # alternating stone widths (long and short work)
AJAR_DEG = 28.0
LEAF_W = 0.86
HINGE = (HALF - 0.03, -0.22)   # hinge axis (x, y)
LEAF_Z0 = 0.13           # underside of the leaf, above the room's floor boards
FLOOR_TOP = 0.11
LAMP = (-0.20, -0.11, 1.40)    # flame position

COLOR = (1.0, 0.42, 0.10)
LIGHTS = [
    ((LAMP[0], LAMP[1], LAMP[2] + 0.04), COLOR, 210.0),   # the lamp: the leaf and the jambs cut its
                                                         # light into a wedge across the step
    ((-0.55, -0.66, 0.38), COLOR, 36.0),     # soft fill on the step just outside the gap
    ((-1.00, -1.60, 0.18), COLOR, 22.0),     # lengthens the pool toward the front left
]


def _case(kit, mats, rng, root):
    from assets.gate_door import _dressed  # the gate's chiseled-stone variant of the wall material
    stone = _dressed(mats["stone_wall"])
    courses = 5
    base = HEIGHT / courses
    for side in (-1, 1):
        z = 0.0
        for c in range(courses):
            h = base + (kit.jitter(rng, 0.04) if c < courses - 1 else 0.0)
            if c == courses - 1:
                h = HEIGHT - z
            w = JAMB_W[c % 2] + kit.jitter(rng, 0.02)
            d = DEPTH - abs(kit.jitter(rng, 0.03))
            kit.box(f"jamb_{'R' if side > 0 else 'L'}{c}", (w, d, h - 0.014),
                    (side * (HALF + w / 2), -d / 2, z + h / 2), mat=stone, bevel=0.02, parent=root)
            z += h

    # lintel with a drip course on top
    kit.box("lintel", (1.9, DEPTH + 0.02, 0.34), (0, -(DEPTH + 0.02) / 2, HEIGHT + 0.17),
            mat=stone, bevel=0.025, parent=root)
    kit.box("drip", (2.02, DEPTH + 0.12, 0.12), (0, -(DEPTH + 0.12) / 2, HEIGHT + 0.34 + 0.06),
            mat=stone, bevel=0.02, parent=root)
    # worn sill inside the case, one step outside it
    kit.box("sill", (2 * HALF, DEPTH, 0.07), (0, -DEPTH / 2, 0.035), mat=stone, bevel=0.012,
            parent=root)
    kit.box("step", (1.5, 0.42, 0.12), (0.04, -(DEPTH + 0.21 - 0.02), 0.06), rot_deg=(0, 0, 1.5),
            mat=stone, bevel=0.025, parent=root)


def _leaf(kit, mats, rng, root):
    wood, iron = mats["door_wood"], mats["iron"]
    pivot = kit.group("leaf", (HINGE[0], HINGE[1], 0.0), parent=root)
    pivot.rotation_euler = (0, 0, math.radians(AJAR_DEG))
    z0, z1 = LEAF_Z0, HEIGHT - 0.01
    n = 5
    pw = LEAF_W / n
    for k in range(n):
        top = z1 - abs(kit.jitter(rng, 0.012))
        kit.box(f"plank_{k}", (pw - 0.006, 0.07, top - z0), (-(k + 0.5) * pw, 0, (top + z0) / 2),
                mat=wood, bevel=0.01, parent=pivot)

    # three iron straps from the hinge, studded, each with a hinge eye on the jamb side
    for b, z in enumerate((0.38, 1.0, 1.62)):
        length = LEAF_W - 0.1
        kit.box(f"strap_{b}", (length, 0.022, 0.12), (-length / 2 - 0.01, -0.044, z), mat=iron,
                bevel=0.006, parent=pivot)
        kit.cylinder(f"eye_{b}", 0.035, 0.15, (0.01, -0.03, z), mat=iron, segments=8, bevel=0.006,
                     parent=pivot)
        for s in range(4):
            kit.cylinder(f"stud_{b}_{s}", 0.017, 0.022, (-0.14 - s * 0.19, -0.057, z),
                         rot_deg=(90, 0, 0), mat=iron, segments=6, parent=pivot)

    # ring handle with a boss and a lock plate on the free edge
    hx = -LEAF_W + 0.09
    kit.cylinder("boss", 0.04, 0.03, (hx, -0.052, 1.0), rot_deg=(90, 0, 0), mat=iron, segments=8,
                 parent=pivot)
    kit.torus("ring", 0.06, 0.011, (hx, -0.065, 0.94), rot_deg=(90, 0, 0), mat=iron,
              major_segments=14, minor_segments=5, parent=pivot)
    kit.box("lock", (0.09, 0.02, 0.16), (hx + 0.09, -0.048, 1.13), mat=iron, bevel=0.005,
            parent=pivot)


def _room(kit, mats, rng, root):
    """The room behind the leaf: floor, back wall, beam, cloak and a small hanging oil lamp."""
    wood, dark, iron, burlap = mats["wood_old"], mats["wood_dark"], mats["iron"], mats["burlap"]
    depth = -HINGE[1] - 0.01
    for k, x in enumerate((-0.33, 0.0, 0.33)):
        kit.box(f"floor_{k}", (0.32, depth, 0.04), (x + kit.jitter(rng, 0.004), -depth / 2 - 0.01, FLOOR_TOP - 0.02),
                mat=wood, bevel=0.004, parent=root)
    for k, x in enumerate((-0.335, 0.0, 0.335)):
        top = HEIGHT - 0.02 - abs(kit.jitter(rng, 0.03))
        kit.box(f"back_{k}", (0.33, 0.035, top - 0.07), (x, -0.025 - 0.01 * (k % 2), 0.07 + (top - 0.07) / 2),
                mat=wood, bevel=0.005, parent=root)
    kit.box("batten", (1.0, 0.03, 0.08), (0, -0.058, 0.95), mat=dark, bevel=0.004, parent=root)
    kit.box("beam", (1.0, 0.17, 0.15), (0, -0.14, HEIGHT - 0.075), mat=dark, bevel=0.01, parent=root)
    # a cloak hung on a peg near the gap, where the lamp lights it
    kit.cylinder("peg", 0.012, 0.09, (-0.3, -0.085, 1.45), rot_deg=(90, 0, 0), mat=iron, segments=6, parent=root)
    kit.box("cloak", (0.2, 0.035, 0.62), (-0.3, -0.11, 1.12), rot_deg=(2, 0, 5), mat=burlap, bevel=0.01, parent=root)
    # oil lamp on a chain from the beam
    lx, ly, lz = LAMP
    kit.cylinder("chain", 0.006, HEIGHT - 0.15 - lz, (lx, ly, (HEIGHT - 0.15 + lz) / 2), mat=iron, segments=5,
                 parent=root)
    kit.cylinder("lamp_bowl", 0.032, 0.035, (lx, ly, lz - 0.02), mat=iron, segments=10, radius_top=0.052,
                 bevel=0.003, parent=root)
    kit.torus("lamp_rim", 0.052, 0.006, (lx, ly, lz - 0.003), mat=iron, major_segments=12, minor_segments=4,
              parent=root)
    _fire.flame(kit, mats["fire"], root, "lamp_flame", (lx, ly, lz), 0.10, 0.026, lean=(0.01, 0.0), twist=0.8,
                phase=1.0, rings=10, sides=8)


def build(kit, mats, rng):
    root = kit.group("lit_door")
    _case(kit, mats, rng, root)
    _leaf(kit, mats, rng, root)
    _room(kit, mats, rng, root)
    return root

"""The commander's weapons in the front corner: a rack with two boar spears and a sword on pegs, a round shield on the floor, and a mail shirt on its stand.

A freestanding rack, face-on to the camera, about 1.95 m wide: the mail stand on the left, the rack in the middle, the shield at its right foot. Origin:
the middle of the rack on the floor, the front toward -Y.
- The rack: two uprights on a foot board, a trough at the foot and a rail at 1.5 m, two spears standing through them; a middle rail
  with two pegs holds a sheathed arming sword, its belt hanging from the left peg.
- The shield: round, oak, leaning against the foot board, the paint rubbed off the iron boss.
- The mail shirt: oiled, mended at the left shoulder, on a T-stand with a plain iron cap on top.
"""

import math

from . import _kitchen
from . import _tower as T

LIGHTS = []


def spear(kit, mats, root, name, x, y, lean=0.0):
    kit.cylinder(f"{name}_shaft", 0.015, 2.1, (x, y, 1.05), (lean, 0, 0), mats["wood_old"], segments=8, parent=root)
    kit.box(f"{name}_socket", (0.034, 0.034, 0.12), (x, y, 2.16), (lean, 0, 0), mats["iron"], parent=root)
    leaf = kit.mesh(f"{name}_head", [(-0.032, 0.0, 0.0), (0.032, 0.0, 0.0), (0.04, 0.0, 0.1), (0.0, 0.0, 0.3), (-0.04, 0.0, 0.1)],
                    [(0, 1, 2, 3, 4)], loc=(x, y, 2.22), mat=mats["iron"], parent=root)
    kit.solidify(leaf, 0.008)
    kit.box(f"{name}_lugs", (0.11, 0.012, 0.014), (x, y, 2.19), mat=mats["iron"], parent=root)


def build(kit, mats, rng):
    root = kit.group("tower_rack")
    wo, wd, iron = mats["wood_old"], mats["wood_dark"], mats["iron"]
    # rack: foot board, two uprights, a trough at the foot, rails at 1.15 and 1.5
    kit.box("rack_foot", (0.95, 0.46, 0.06), (0, 0, 0.03), mat=wd, bevel=0.005, parent=root)
    for n, x in enumerate((-0.4, 0.4)):
        kit.box(f"rack_upright_{n}", (0.06, 0.07, 1.62), (x, 0.0, 0.06 + 0.81), mat=wd, bevel=0.005, parent=root)
        kit.box(f"rack_brace_{n}", (0.04, 0.4, 0.04), (x, 0.0, 0.5), (0, 0, 0), mat=wd, parent=root)
    kit.box("rack_trough", (0.8, 0.16, 0.09), (0, 0.0, 0.105), mat=wd, bevel=0.006, parent=root)
    kit.box("rack_rail_top", (0.86, 0.06, 0.07), (0, 0.0, 1.5), mat=wd, bevel=0.005, parent=root)
    kit.box("rack_rail_mid", (0.86, 0.05, 0.07), (0, -0.01, 1.12), mat=wd, bevel=0.005, parent=root)
    spear(kit, mats, root, "boar_spear_a", -0.2, 0.0)
    spear(kit, mats, root, "boar_spear_b", 0.05, 0.0, lean=0.0)
    # sword on two pegs of the middle rail, belt on the left one
    for n, x in enumerate((-0.32, 0.3)):
        kit.beam(f"peg_{n}", (x, -0.03, 1.12), (x, -0.14, 1.12), (0.03, 0.03), wd, bevel=0.004, parent=root)
    sc = kit.group("sword", (-0.02, -0.16, 1.15), parent=root)
    kit.box("scabbard", (0.74, 0.04, 0.05), (0.03, 0, 0), mat=wd, bevel=0.008, parent=sc)
    kit.box("scabbard_tip", (0.06, 0.03, 0.035), (0.4, 0, 0), mat=iron, parent=sc)
    kit.box("scabbard_throat", (0.05, 0.05, 0.06), (-0.3, 0, 0), mat=iron, parent=sc)
    kit.cylinder("grip", 0.016, 0.16, (-0.4, 0, 0), (0, 90, 0), mats["burlap"], segments=8, parent=sc)
    kit.box("crossguard", (0.025, 0.04, 0.2), (-0.31, 0, 0), mat=iron, bevel=0.003, parent=sc)
    kit.sphere("pommel", 0.026, (-0.495, 0, 0), mat=iron, segments=10, parent=sc)
    kit.beam("belt", (-0.32, -0.16, 1.1), (-0.3, -0.14, 0.72), (0.03, 0.01), mats["sacking"], parent=root)
    kit.box("buckle", (0.035, 0.01, 0.03), (-0.3, -0.15, 0.74), mat=iron, parent=root)
    # shield on the floor, leaning on the foot board
    sh = kit.group("shield", (0.66, -0.14, 0.28), parent=root)
    sh.rotation_euler = (math.radians(-72), 0, math.radians(-8))
    kit.cylinder("shield_board", 0.28, 0.035, (0, 0, 0), mat=mats["door_wood"], segments=24, bevel=0.003, parent=sh)
    kit.torus("shield_rim", 0.28, 0.012, (0, 0, 0.0), mat=iron, major_segments=24, minor_segments=4, parent=sh)
    kit.torus("shield_paint", 0.2, 0.045, (0, 0, 0.02), mat=mats["cloth_red"], major_segments=20, minor_segments=4, parent=sh)
    kit.cylinder("shield_boss", 0.06, 0.04, (0, 0, 0.03), mat=iron, radius_top=0.035, segments=12, parent=sh)

    # the mail shirt on a T-stand with an iron cap, to the left of the rack
    mx, my = -0.85, 0.05
    kit.box("stand_foot_a", (0.5, 0.05, 0.04), (mx, my, 0.02), mat=wd, bevel=0.004, parent=root)
    kit.box("stand_foot_b", (0.05, 0.5, 0.04), (mx, my, 0.02), mat=wd, bevel=0.004, parent=root)
    kit.box("stand_post", (0.045, 0.045, 1.42), (mx, my, 0.71), mat=wd, bevel=0.004, parent=root)
    kit.box("stand_arms", (0.64, 0.04, 0.04), (mx, my, 1.3), mat=wd, bevel=0.004, parent=root)
    profile = [(0.0, 0.58), (0.275, 0.58), (0.27, 0.62), (0.245, 0.78), (0.235, 0.98), (0.26, 1.18), (0.27, 1.27), (0.2, 1.33),
               (0.09, 1.35), (0.0, 1.35)]
    body = _kitchen.lathe(kit, "mail_shirt", profile, 22, mats["mail"], (mx, my, 0.0), root)
    for v in body.data.vertices:
        v.co.y *= 0.62
    for n, s in enumerate((-1, 1)):
        kit.cylinder(f"mail_sleeve_{n}", 0.075, 0.3, (mx + s * 0.34, my, 1.22), (0, 90 * s, 0), mats["mail"], radius_top=0.062,
                     segments=12, parent=root)
    # the left shoulder is mended with a patch of bright new rings
    kit.cylinder("mail_patch", 0.05, 0.02, (mx - 0.28, my - 0.01, 1.27), (0, 90, 0), mats["iron"], segments=10, parent=root)
    _kitchen.lathe(kit, "iron_cap", [(0.0, 0.0), (0.105, 0.0), (0.115, 0.03), (0.1, 0.1), (0.06, 0.155), (0.0, 0.175)], 16, iron,
                   (mx, my, 1.4), root)
    kit.torus("cap_rim", 0.108, 0.008, (mx, my, 1.405), mat=iron, major_segments=16, minor_segments=4, parent=root)
    return root

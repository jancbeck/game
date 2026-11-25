"""The commander's chair: a heavy oak armchair with a high back, behind his desk.

Origin: the middle of the seat on the floor, the front toward -Y (toward the desk and the guest). The seat top is 0.50 m
over the floor, 0.58 m wide and 0.52 m deep: this is where a seated figure's pelvis rests, so the plan puts the prop at the
spot recorded in location.json `people.commander`. The back stands 1.2 m high. Stout square legs, side and cross stretchers,
three thick seat planks, two arm boards on short posts, a back of two rails and four slats under a carved crest rail.
The wood is old, dark and worn pale where hands and elbows rest.
"""

LIGHTS = []
W, D = 0.58, 0.52          # the seat
SEAT = 0.50                # top of the seat planks
BACK = 1.2                 # top of the back posts
ARM = 0.74                 # top of the arm boards


def build(kit, mats, rng):
    root = kit.group("tower_chair")
    wd, wo, dw = mats["wood_dark"], mats["wood_old"], mats["door_wood"]
    hx, hy = W / 2 - 0.04, D / 2 - 0.04
    # four legs; the back pair rise on into the back posts
    for n, (px, py) in enumerate(((-hx, -hy), (hx, -hy), (-hx, hy), (hx, hy))):
        top = BACK if py > 0 else SEAT - 0.05
        kit.box(f"chair_leg_{n}", (0.07, 0.07, top), (px, py, top / 2), (0, 0, 0), wd, bevel=0.008, parent=root)
    # stretchers low between the legs: both sides, front and back
    for n, s in enumerate((-1, 1)):
        kit.box(f"chair_side_stretcher_{n}", (0.04, D - 0.1, 0.05), (s * hx, 0, 0.17), mat=wd, bevel=0.005, parent=root)
    for n, s in enumerate((-1, 1)):
        kit.box(f"chair_cross_stretcher_{n}", (W - 0.1, 0.04, 0.05), (0, s * hy, 0.2), mat=wd, bevel=0.005, parent=root)
    # seat rails under the planks, the planks themselves
    for n, s in enumerate((-1, 1)):
        kit.box(f"chair_rail_x_{n}", (0.05, D - 0.06, 0.09), (s * hx, 0, SEAT - 0.095), mat=wd, bevel=0.005, parent=root)
        kit.box(f"chair_rail_y_{n}", (W - 0.06, 0.05, 0.09), (0, s * hy, SEAT - 0.095), mat=wd, bevel=0.005, parent=root)
    y = -D / 2
    for n, w_ in enumerate((0.17, 0.18, 0.17)):
        kit.box(f"chair_plank_{n}", (W + 0.02, w_ - 0.008, 0.045), (0, y + w_ / 2, SEAT - 0.0225),
                (rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0), dw if n != 1 else wo, bevel=0.008, parent=root)
        y += w_
    # arms: a board on a short post at the front corner and on the back post
    for n, s in enumerate((-1, 1)):
        kit.box(f"chair_arm_post_{n}", (0.05, 0.05, ARM - SEAT), (s * (W / 2 - 0.035), -hy + 0.02, (ARM + SEAT) / 2), mat=wd,
                bevel=0.006, parent=root)
        kit.box(f"chair_arm_{n}", (0.07, D - 0.02, 0.04), (s * (W / 2 - 0.035), 0.0, ARM + 0.02), mat=wo, bevel=0.01,
                parent=root)
    # the back: two rails, four slats between them, a crest rail with a carved top
    for n, z in enumerate((0.78, 1.0)):
        kit.box(f"chair_back_rail_{n}", (W - 0.07, 0.04, 0.08), (0, hy, z), mat=wd, bevel=0.006, parent=root)
    for n in range(4):
        x = -0.17 + n * 0.113
        kit.box(f"chair_slat_{n}", (0.04, 0.025, 0.42), (x, hy - 0.005, 0.89), mat=wo, bevel=0.004, parent=root)
    kit.box("chair_crest", (W + 0.06, 0.06, 0.13), (0, hy, BACK - 0.065), mat=wo, bevel=0.012, parent=root)
    kit.box("chair_crest_cap", (W - 0.14, 0.05, 0.05), (0, hy, BACK + 0.02), mat=wo, bevel=0.01, parent=root)
    # a folded grey blanket over the back, worn smooth where a man leans
    kit.box("chair_blanket", (0.34, 0.025, 0.2), (0.04, hy - 0.035, 0.98), (0, 0, 0), mats["wool"], bevel=0.008, parent=root)
    return root

"""Iron tether ring set in the wall at hitching height, with a rope end tied through it.

Origin: the ring's anchor on the wall face (XZ plane at y = 0); it sticks out toward -Y. A square
iron plate with four rivets holds an eye bolt, and the ring hangs from the eye in the plane of the
wall. A short length of hemp lead is knotted through the ring and hangs down in a loose curve with
a frayed end. Below the plate the stone is stained dark by rust and rain. Mount it under "mounted"
at about z = 0.9 m, where a horse's halter reaches.
"""

from ._sweep import rope


def build(kit, mats, rng):
    root = kit.group("tether_ring")
    iron, rope_mat, soot = mats["iron"], mats["rope"], mats["wood_dark"]
    j = lambda a: kit.jitter(rng, a)  # noqa: E731

    kit.box("plate", (0.17, 0.028, 0.17), (0, -0.014, 0), (0, 0, j(3)), iron, bevel=0.006, parent=root)
    for i, (x, z) in enumerate(((-0.058, 0.058), (0.058, 0.058), (-0.058, -0.058), (0.058, -0.058))):
        kit.cylinder(f"rivet_{i}", 0.011, 0.012, (x, -0.033, z), rot_deg=(90, 0, 0), mat=iron, segments=8, parent=root)
    # eye bolt: a short shank and an eye that the ring passes through
    kit.cylinder("shank", 0.016, 0.09, (0, -0.07, 0.0), rot_deg=(90, 0, 0), mat=iron, segments=8, parent=root)
    kit.torus("eye", 0.026, 0.009, (0, -0.125, 0.0), rot_deg=(0, 90, 0), mat=iron, major_segments=14,
              minor_segments=5, parent=root)
    # the ring hangs from the eye, turned a little, its lower part resting forward
    kit.torus("ring", 0.078, 0.0125, (0, -0.125, -0.07), rot_deg=(90 + j(12), 0, 0), mat=iron,
              major_segments=24, minor_segments=6, parent=root)

    # lead rope: knotted through the ring's bottom, hanging in a loose curve with a frayed end
    top = (0.0, -0.125 - 0.012, -0.142)
    kit.sphere("knot", 0.026, top, scale=(1.0, 1.0, 1.2), mat=rope_mat, segments=8, parent=root)
    side = rng.choice((-1, 1))
    ctrl = [top, (side * 0.02, -0.15, -0.23), (side * 0.07, -0.19, -0.36), (side * 0.06, -0.24, -0.50),
            (side * 0.13, -0.27, -0.62)]
    rope(kit, "lead", ctrl, 0.011, rope_mat, root, lay=0.07, step=0.01)
    for k in range(3):
        a = ctrl[-1]
        kit.cylinder(f"fray_{k}", 0.003, 0.05, (a[0] + j(0.01), a[1] + j(0.01), a[2] - 0.02), rot_deg=(j(25), j(25), 0),
                     mat=rope_mat, segments=4, radius_top=0.001, parent=root)

    # rust and rain streaks on the stone under the plate
    for n, (dx, w, drop) in enumerate(((-0.05, 0.035, 0.34), (0.02, 0.05, 0.5), (0.06, 0.03, 0.26))):
        kit.box(f"stain_{n}", (w, 0.004, drop), (dx, -0.002, -0.085 - drop / 2), mat=soot, parent=root)
    return root

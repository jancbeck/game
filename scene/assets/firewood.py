"""Stacked firewood: split logs with their ends facing the front (-Y).

A rick about 1.4 m wide, 0.45 m deep and 0.9 m high, on two bearers between
four leaning stakes, ragged at the top and ends. Beside it: a chopping block
with an axe stuck in it, a few loose logs and wood chips. Back of the stack
is at about Y = +0.2; the stack center is at the origin.
"""

import math

COLS, ROWS = 9, 7
DX, DZ = 0.152, 0.138
LOG_LEN = 0.42


def _section(rng, kind, r, roll):
    if kind == "round":
        return [(r * math.cos(2 * math.pi * i / 8 + roll), r * math.sin(2 * math.pi * i / 8 + roll))
                for i in range(8)]
    if kind == "half":
        pts = [(r * math.cos(roll + math.pi * i / 4), r * math.sin(roll + math.pi * i / 4))
               for i in range(5)]
        return pts
    pts = [(0.0, 0.0)] + [(r * math.cos(roll + math.pi / 2 * i / 3), r * math.sin(roll + math.pi / 2 * i / 3))
                          for i in range(4)]
    return [(x - 0.3 * r * math.cos(roll + math.pi / 4), z - 0.3 * r * math.sin(roll + math.pi / 4))
            for x, z in pts]


def _add_log(rng, store, x, z, y0, r, kind):
    sec = _section(rng, kind, r, rng.uniform(0, 2 * math.pi))
    length = LOG_LEN + rng.uniform(-0.04, 0.04)
    verts, faces = store
    n = len(sec)
    base = len(verts)
    for yy in (y0, y0 + length):
        for sx, sz in sec:
            verts.append((x + sx + rng.uniform(-0.004, 0.004), yy + rng.uniform(-0.006, 0.006),
                          z + sz + rng.uniform(-0.004, 0.004)))
    faces.append(tuple(range(base + n - 1, base - 1, -1)))
    faces.append(tuple(range(base + n, base + 2 * n)))
    for i in range(n):
        k = (i + 1) % n
        faces.append((base + i, base + k, base + n + k, base + n + i))


def build(kit, mats, rng):
    j = lambda a: kit.jitter(rng, a)  # noqa: E731
    root = kit.group("firewood")
    wo, wd = mats["wood_old"], mats["wood_dark"]
    width = (COLS - 1) * DX
    split, bark = ([], []), ([], [])

    heights = [ROWS - (3 if c in (0, COLS - 1) else rng.choice((0, 0, 1, 1, 2))) for c in range(COLS)]
    for row in range(ROWS):
        cols = COLS if row % 2 == 0 else COLS - 1
        for c in range(cols):
            col_idx = c if row % 2 == 0 else c + 0.5
            if row >= heights[min(COLS - 1, int(round(col_idx)))]:
                continue
            r = rng.uniform(0.062, 0.085)
            kind = rng.choice(("round", "half", "half", "quarter", "quarter"))
            x = (col_idx - (COLS - 1) / 2) * DX + j(0.012)
            z = 0.05 + 0.075 + row * DZ + j(0.01)
            _add_log(rng, bark if kind == "round" else split, x, z, -LOG_LEN / 2 + j(0.04), r, kind)
    kit.mesh("logs_split", *split, mat=wo, parent=root)
    kit.mesh("logs_round", *bark, mat=wd, parent=root)

    # bearers keep the stack off the wet floor; stakes hold the ends
    for n, y in enumerate((-0.14, 0.14)):
        kit.box(f"bearer_{n}", (width + 0.25, 0.07, 0.05), (0, y, 0.025), mat=wd, bevel=0.008,
                parent=root)
    for sx in (-1, 1):
        for sy in (-1, 1):
            lean = sx * (3 + j(1.5))
            top = (sx * (width / 2 + 0.1 + math.tan(math.radians(lean)) * 1.0), sy * 0.17 + j(0.02), 1.0 + j(0.05))
            kit.beam(f"stake_{sx}_{sy}", (sx * (width / 2 + 0.1), sy * 0.17, 0), top, (0.07, 0.07), wd,
                     bevel=0.01, parent=root)

    # chopping block and a stuck axe
    bx, by = width / 2 + 0.6, -0.4
    kit.cylinder("block", 0.2, 0.38, (bx, by, 0.19), mat=wo, segments=14, bevel=0.01, parent=root)
    kit.cylinder("block_top", 0.19, 0.01, (bx, by, 0.385), mat=wd, segments=14, parent=root)
    p0 = (bx - 0.02, by, 0.47)
    kit.beam("axe_handle", p0, (p0[0] + 0.3, by + j(0.02), p0[2] + 0.62), (0.035, 0.03), wo, bevel=0.006,
             parent=root)
    kit.box("axe_head", (0.11, 0.035, 0.13), (bx - 0.02, by, 0.44), (0, j(5), 0), mats["iron"], bevel=0.006,
            parent=root)

    # loose logs on the floor, each shifted so its lowest point touches Z = 0
    for k in range(3):
        a = rng.uniform(0, 2 * math.pi)
        store = ([], [])
        _add_log(rng, store, 0.0, 0.0, 0.0, rng.uniform(0.07, 0.09), "half")
        low = min(z for _, _, z in store[0])
        ox, oy = bx + 0.45 * math.cos(a) - 0.2, by - 0.35 + 0.3 * math.sin(a)
        kit.mesh(f"log_loose_{k}", [(x, y, z - low + 0.003) for x, y, z in store[0]], store[1],
                 loc=(ox, oy, 0), rot_deg=(0, 0, rng.uniform(-60, 60)), mat=wo, parent=root)
    for k in range(14):
        a = rng.uniform(0, 2 * math.pi)
        d = rng.uniform(0.1, 0.6)
        kit.box(f"chip_{k}", (rng.uniform(0.05, 0.11), rng.uniform(0.02, 0.04), 0.008),
                (bx + d * math.cos(a), by + d * math.sin(a), 0.005), (j(4), j(4), rng.uniform(0, 180)), wo,
                parent=root)
    return root

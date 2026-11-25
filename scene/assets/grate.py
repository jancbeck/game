"""Square iron drain set in the courtyard floor.

Origin at the center, z = 0 is the floor surface. A stone curb frame stands
0.035 m proud, the iron grid sits just below the curb top, and a dark pit
drops 0.6 m underneath. Footprint 1.5 m x 1.5 m.
"""

OUTER = 1.5
CURB_W = 0.20
INNER = OUTER - 2 * CURB_W  # 1.1 m opening
CURB_TOP = 0.035
GRID_TOP = 0.01
PIT_DEPTH = 0.6
BARS = 7


def _splits(rng, kit, length, n):
    """Cut a run of `length` into n blocks of uneven size; returns (start, size) pairs."""
    weights = [1.0 + kit.jitter(rng, 0.35) for _ in range(n)]
    total = sum(weights)
    out, pos = [], -length / 2
    for w in weights:
        size = length * w / total
        out.append((pos, size))
        pos += size
    return out


def _curb(kit, mats, rng, root):
    stone = mats["stone_wall"]
    mid = (OUTER - CURB_W) / 2
    runs = [
        ("n", OUTER, 3, lambda c: (c, mid), True),
        ("s", OUTER, 3, lambda c: (c, -mid), True),
        ("e", INNER, 2, lambda c: (mid, c), False),
        ("w", INNER, 2, lambda c: (-mid, c), False),
    ]
    for tag, length, n, place, along_x in runs:
        for i, (start, size) in enumerate(_splits(rng, kit, length, n)):
            top = CURB_TOP + kit.jitter(rng, 0.006)
            h = top + 0.12
            gap = 0.008
            x, y = place(start + size / 2)
            dims = (size - gap, CURB_W - gap) if along_x else (CURB_W - gap, size - gap)
            kit.box(f"curb_{tag}{i}", (dims[0], dims[1], h), (x, y, top - h / 2),
                    rot_deg=(0, 0, kit.jitter(rng, 0.8)), mat=stone, bevel=0.015, parent=root)


def _grid(kit, mats, rng, root):
    iron = mats["iron"]
    half = INNER / 2
    # Angle iron resting on the curb ledge, holding the bars.
    rim = 0.05
    for sx, sy, size in (
        (0, half - rim / 2, (INNER, rim, 0.04)), (0, -half + rim / 2, (INNER, rim, 0.04)),
        (half - rim / 2, 0, (rim, INNER - 2 * rim, 0.04)), (-half + rim / 2, 0, (rim, INNER - 2 * rim, 0.04)),
    ):
        kit.box(f"rim_{len(root.children)}", size, (sx, sy, GRID_TOP - 0.02), mat=iron, bevel=0.006, parent=root)

    pitch = (INNER - 2 * rim - 0.06) / (BARS - 1)
    for i in range(BARS):
        p = -(BARS - 1) / 2 * pitch + i * pitch
        kit.box(f"bar_x{i}", (INNER - 0.04, 0.035, 0.04), (0, p, GRID_TOP - 0.02 + kit.jitter(rng, 0.002)),
                mat=iron, bevel=0.005, parent=root)
        kit.box(f"bar_y{i}", (0.035, INNER - 0.04, 0.04), (p, 0, GRID_TOP - 0.024 + kit.jitter(rng, 0.002)),
                mat=iron, bevel=0.005, parent=root)


def _pit(kit, mats, root):
    iron = mats["iron"]
    half = INNER / 2
    wall = 0.04
    top = -0.01
    h = PIT_DEPTH + top
    kit.box("pit_floor", (INNER + 0.1, INNER + 0.1, wall), (0, 0, -PIT_DEPTH - wall / 2), mat=iron, parent=root)
    for tag, size, loc in (
        ("n", (INNER + 0.1, wall, h), (0, half + wall / 2, top - h / 2)),
        ("s", (INNER + 0.1, wall, h), (0, -half - wall / 2, top - h / 2)),
        ("e", (wall, INNER, h), (half + wall / 2, 0, top - h / 2)),
        ("w", (wall, INNER, h), (-half - wall / 2, 0, top - h / 2)),
    ):
        kit.box(f"pit_{tag}", size, loc, mat=iron, parent=root)


def build(kit, mats, rng):
    root = kit.group("grate")
    _curb(kit, mats, rng, root)
    _grid(kit, mats, rng, root)
    _pit(kit, mats, root)
    return root

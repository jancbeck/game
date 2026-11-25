"""A soldier's narrow bed in the commander's chamber: a plank frame with a straw mattress, a grey wool blanket pulled tight, a pillow, a curtain on a rail.

0.9 m wide, 2.0 m long along Y, the head toward +Y. Origin: the middle of the bed on the floor. Four posts, the one at the east corner of the foot tall, carry a
curtain rail along the east side to the wall; a dark red wool curtain hangs from the east rail, drawn back
in folds to the foot post and to the head post, the middle open. Boots stand side by side
under the east rail, toes out.
"""

import math

from . import _kitchen
from . import _shed_geo as geo

LIGHTS = []
W, L = 0.9, 2.0
POST = 0.06
RAIL_Z = 1.9


def build(kit, mats, rng):
    root = kit.group("tower_bed")
    wo, wd, iron = mats["wood_old"], mats["wood_dark"], mats["iron"]
    hx, hy = W / 2 + 0.02, L / 2 - 0.03
    # frame: side boards, slats, head and foot boards, four posts
    for n, s in enumerate((-1, 1)):
        kit.box(f"side_board_{n}", (0.05, L - 0.04, 0.14), (s * (W / 2 - 0.02), 0, 0.32), mat=wo, bevel=0.004, parent=root)
    for k in range(7):
        kit.box(f"slat_{k}", (W - 0.06, 0.12, 0.02), (0, -0.85 + 0.283 * k, 0.28), mat=wd, parent=root)
    kit.box("headboard", (W + 0.02, 0.05, 0.72), (0, hy, 0.38 + 0.08), mat=wo, bevel=0.005, parent=root)
    kit.box("footboard", (W + 0.02, 0.05, 0.32), (0, -hy, 0.34), mat=wo, bevel=0.005, parent=root)
    # low corner posts, one tall post at the foot's east corner that carries the curtain rail to the wall
    for n, (px, py, ph) in enumerate(((-hx, -hy, 0.62), (hx, -hy, RAIL_Z), (-hx, hy, 1.05), (hx, hy, 0.95))):
        kit.box(f"post_{n}", (POST, POST, ph), (px, py, ph / 2), mat=wd, bevel=0.006, parent=root)
    kit.beam("curtain_rail", (hx, -hy, RAIL_Z - 0.03), (hx, hy + 0.1, RAIL_Z - 0.03), (0.04, 0.04), wd, bevel=0.004, parent=root)
    kit.beam("rail_brace", (hx, hy + 0.05, RAIL_Z - 0.03), (hx, hy + 0.1, RAIL_Z - 0.2), (0.03, 0.03), wd, parent=root)
    # straw mattress, sheet at the head, pillow
    mat_ob = _kitchen.blob(kit, "mattress", (0, 0, 0.36), (W / 2 - 0.03, L / 2 - 0.1, 0.085), mats["burlap"], root, segments=14)
    kit.box("sheet", (W - 0.1, 0.34, 0.03), (0, 0.5, 0.49), (0, 0, 0), mats["flour"], bevel=0.008, parent=root)
    # the blanket: a pulled-tight sheet of wool over the mattress, drooping at the sides and the foot
    nx, ny = 16, 30
    verts, faces = [], []
    for j in range(ny + 1):
        y = -0.93 + (0.93 + 0.34) * j / ny
        for i in range(nx + 1):
            x = -0.5 + i / nx
            ax = abs(x)
            drop = 0.3 * min(1.0, max(0.0, (ax - 0.36) / 0.12)) ** 1.5 + 0.22 * min(1.0, max(0.0, (-y - 0.78) / 0.14)) ** 1.5
            z = 0.51 + 0.012 * math.sin(7 * y + 3 * x) - drop + (0.014 if j > ny - 3 else 0.0)
            verts.append((x * 0.97, y, z))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    blanket = kit.mesh("blanket", verts, faces, mat=mats["wool"], parent=root)
    for p in blanket.data.polygons:
        p.use_smooth = True
    kit.solidify(blanket, 0.02)
    _kitchen.blob(kit, "pillow", (0, 0.74, 0.56), (0.21, 0.15, 0.06), mats["sacking"], root, rot_z=3, segments=12)
    # the curtain from the east rail: one panel gathered at the foot post, one at the head post, the middle open
    zr = RAIL_Z - 0.05
    _curtain_panel(kit, mats, root, hx - 0.02, -hy + 0.05, -hy + 0.62, zr, 0.0, gather=True)
    _curtain_panel(kit, mats, root, hx - 0.02, hy - 0.62, hy - 0.05, zr, 1.7, gather=True)
    # boots under the east rail
    for n, (bx, by) in enumerate(((0.55, -0.4), (0.55, -0.64))):
        kit.box(f"boot_sole_{n}", (0.1, 0.3, 0.03), (bx, by, 0.015), (0, 0, 5 - 10 * n), mats["wood_dark"], bevel=0.005, parent=root)
        kit.box(f"boot_{n}", (0.09, 0.22, 0.13), (bx, by - 0.03, 0.095), (0, 0, 5 - 10 * n), mats["sacking"], bevel=0.015, parent=root)
        kit.box(f"boot_shaft_{n}", (0.09, 0.09, 0.14), (bx, by + 0.08, 0.17), (0, 0, 5 - 10 * n), mats["sacking"], bevel=0.012, parent=root)
    return root


def _curtain_panel(kit, mats, root, x, y0, y1, z_top, phase, gather=False):
    """A curtain panel hanging in the plane x from y0 to y1: vertical folds, a ragged hem; `gather` bunches it."""
    nz, ny = 14, 30
    verts, faces = [], []
    for i in range(ny + 1):
        t = i / ny
        y = y0 + (y1 - y0) * t
        hem = 0.2 + 0.03 * math.sin(9 * t + phase)
        for j in range(nz + 1):
            s = j / nz
            z = z_top + (hem - z_top) * s
            fold = (0.1 if gather else 0.035) * (0.4 + 0.6 * s) * math.sin(2 * math.pi * (4.0 if gather else 2.2) * t + phase + 0.5 * s)
            verts.append((x + fold, y, z))
    for i in range(ny):
        for j in range(nz):
            a = i * (nz + 1) + j
            faces.append((a, a + 1, a + nz + 2, a + nz + 1))
    ob = kit.mesh("curtain", verts, faces, mat=mats["wool_red"], parent=root)
    for p in ob.data.polygons:
        p.use_smooth = True
    kit.solidify(ob, 0.012)
    return ob

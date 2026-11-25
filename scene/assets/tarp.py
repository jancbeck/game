"""Waxed canvas tarp thrown over the big crate and the one stacked on it, lashed with rope.

Place it with the same position and rotation as `crates`: it reads their layout (crates.BIG and
crates.MID) and covers that stack only. The small crate beside it stays open, so the lantern on
its lid still shows. Origin and orientation are the crates' own.

The cloth is one grid mesh. Over the crate tops it lies flat, then falls along the sides and
spreads out into a skirt that rests on the ground, with a ragged hem and a few creases. Two
rope loops hold it down, one round the big crate and one round the upper crate, each knotted at
the front with the ends hanging. The canvas is dark and wet, with a sheen, damp streaks running
down it and mud along the hem.
"""

import math

import bpy

from . import crates
from ._sweep import rope

CELL = 0.03
HEM = 0.30               # skirt reach beyond the crate sides, meters
TAU_BIG = 0.065          # how quickly the cloth drops away from a crate edge, meters
TAU_MID = 0.045
CLOTH = 0.03             # cloth sits this far above the crate tops and out from the sides: clears cleats and plates
LID_RAISE = 0.22         # the upper crate's lid stands ajar and its straw heaps up; the cloth tents over it


def _box_sdf(px, py, c, yaw_deg, a, b):
    """Signed distance from (px, py) to a rectangle (half sizes a, b) centered at c, turned by yaw."""
    t = math.radians(yaw_deg)
    dx, dy = px - c[0], py - c[1]
    qx = math.cos(t) * dx + math.sin(t) * dy
    qy = -math.sin(t) * dx + math.cos(t) * dy
    ex, ey = abs(qx) - a, abs(qy) - b
    outside = math.hypot(max(ex, 0.0), max(ey, 0.0))
    return outside + min(max(ex, ey), 0.0)


def _drop(d, tau):
    return 1.0 if d <= 0.0 else math.exp(-d / tau)


def _extents(box):
    """Center, yaw and half sizes of the cloth's footprint round a crate. The ajar lid of the upper
    crate swings out of its outline, so that one gets 0.04 m more."""
    w, d, h, loc, yaw, z0 = box
    extra = 0.04 if box is crates.MID else 0.0
    return loc, yaw, w / 2 + crates.BATTEN_T + CLOTH + extra, d / 2 + crates.BATTEN_T + CLOTH + extra


def _height(x, y, big, mid):
    """Cloth height at (x, y): big crate top plus the upper crate's step, falling off at the sides."""
    bc, byaw, ba, bb = _extents(big)
    mc, myaw, ma, mb = _extents(mid)
    d_big = _box_sdf(x, y, bc, byaw, ba, bb)
    d_mid = _box_sdf(x, y, mc, myaw, ma, mb)
    # creases: a slow wave in the fall-off distance, so the skirt ripples instead of being a smooth bell
    ripple = 0.018 * math.sin(17.0 * x + 3.1 * math.sin(7.0 * y)) + 0.014 * math.sin(23.0 * y + 1.7)
    # pleats: cloth gathers into vertical folds that fan out from the stack
    ang = math.atan2(y - bc[1], x - bc[0])
    ripple += 0.02 * math.sin(11.0 * ang + 1.6 * math.sin(3.0 * ang)) * min(max(d_big, 0.0) / 0.06, 1.0)
    zb = (big[2] + CLOTH) * _drop(d_big + ripple, TAU_BIG)
    zm = (mid[2] + CLOTH + LID_RAISE) * _drop(d_mid + 0.6 * ripple, TAU_MID)
    return zb + zm, d_big


def _tarp_mesh(kit, mats, root):
    big, mid = crates.BIG, crates.MID
    bc = big[3]
    x_lo, x_hi = bc[0] - 0.46 - HEM - 0.1, bc[0] + 0.46 + HEM + 0.1
    y_lo, y_hi = bc[1] - 0.40 - HEM - 0.1, bc[1] + 0.40 + HEM + 0.1
    nx, ny = int((x_hi - x_lo) / CELL) + 1, int((y_hi - y_lo) / CELL) + 1
    idx = {}
    verts, faces = [], []
    cells = {}
    for i in range(nx):
        for j in range(ny):
            x, y = x_lo + i * CELL, y_lo + j * CELL
            z, d = _height(x, y, big, mid)
            hem = HEM + 0.05 * math.sin(11.0 * x + 5.0 * y) + 0.04 * math.sin(7.0 * y - 3.0 * x)
            # the skirt lies on the ground, then dips under the cobbles past the hem: the edge
            # shows where the stones cut it, not as steps of the grid
            z = max(z, 0.03) if d < hem else 0.03 - 0.5 * (d - hem)
            cells[(i, j)] = (x, y, z, d < hem + 0.14)
    for i in range(nx - 1):
        for j in range(ny - 1):
            quad = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            if not all(cells[q][3] for q in quad):
                continue
            ids = []
            for q in quad:
                if q not in idx:
                    idx[q] = len(verts)
                    verts.append(cells[q][:3])
                ids.append(idx[q])
            faces.append(tuple(ids))
    ob = kit.mesh("tarp", verts, faces, mat=_canvas(), parent=root)
    for p in ob.data.polygons:
        p.use_smooth = True
    kit.solidify(ob, 0.006)
    return ob


def _canvas():
    mat = bpy.data.materials.get("tarp_canvas")
    if mat is not None:
        return mat
    mat = bpy.data.materials.new("tarp_canvas")
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    new = nt.nodes.new
    tc = new("ShaderNodeTexCoord")

    # slow tone variation, damp streaks that run down the cloth, and mud toward the hem
    blotch = new("ShaderNodeTexNoise")
    blotch.inputs["Scale"].default_value = 4.0
    blotch.inputs["Detail"].default_value = 5.0
    nt.links.new(tc.outputs["Object"], blotch.inputs["Vector"])
    stretch = new("ShaderNodeMapping")
    stretch.inputs["Scale"].default_value = (11.0, 11.0, 2.0)
    nt.links.new(tc.outputs["Object"], stretch.inputs["Vector"])
    streak = new("ShaderNodeTexNoise")
    streak.inputs["Scale"].default_value = 1.0
    streak.inputs["Detail"].default_value = 1.5
    nt.links.new(stretch.outputs["Vector"], streak.inputs["Vector"])
    sep = new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])

    tone = new("ShaderNodeValToRGB")
    tone.color_ramp.elements[0].color = (0.048, 0.050, 0.032, 1.0)
    tone.color_ramp.elements[1].color = (0.092, 0.088, 0.054, 1.0)
    nt.links.new(blotch.outputs["Fac"], tone.inputs["Fac"])
    damp = new("ShaderNodeMapRange")
    damp.inputs["From Min"].default_value = 0.42
    damp.inputs["From Max"].default_value = 0.65
    damp.inputs["To Min"].default_value = 1.0
    damp.inputs["To Max"].default_value = 0.68
    nt.links.new(streak.outputs["Fac"], damp.inputs["Value"])
    mud = new("ShaderNodeMapRange")
    mud.inputs["From Min"].default_value = 0.02
    mud.inputs["From Max"].default_value = 0.22
    mud.inputs["To Min"].default_value = 0.0
    mud.inputs["To Max"].default_value = 1.0
    nt.links.new(sep.outputs["Z"], mud.inputs["Value"])

    shade = new("ShaderNodeMix")
    shade.data_type = "RGBA"
    shade.blend_type = "MULTIPLY"
    shade.inputs[0].default_value = 1.0
    nt.links.new(tone.outputs["Color"], shade.inputs[6])
    nt.links.new(damp.outputs["Result"], shade.inputs[7])
    dirt = new("ShaderNodeMix")
    dirt.data_type = "RGBA"
    nt.links.new(mud.outputs["Result"], dirt.inputs[0])
    dirt.inputs[6].default_value = (0.045, 0.034, 0.022, 1.0)
    nt.links.new(shade.outputs[2], dirt.inputs[7])
    nt.links.new(dirt.outputs[2], b.inputs["Base Color"])

    weave = new("ShaderNodeTexNoise")
    weave.inputs["Scale"].default_value = 260.0
    weave.inputs["Detail"].default_value = 1.0
    nt.links.new(tc.outputs["Object"], weave.inputs["Vector"])
    bump = new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(weave.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.5
    b.inputs["Specular IOR Level"].default_value = 0.45
    return mat


def _loop(box, amp, floor, tau):
    """Closed path hugging the cloth round `box`: a rounded rectangle at the height where the
    cloth's fall-off, floor + amp * exp(-d / tau), has dropped to the level of the rope."""
    level = amp * 0.0 + floor + amp * 0.49
    d = tau * math.log(amp / (level - floor)) + 0.02
    bc, yaw, a, b = _extents(box)
    t = math.radians(yaw)
    pts = []
    for cx, cy, start in ((a, b, 0), (-a, b, 90), (-a, -b, 180), (a, -b, 270)):
        for k in range(6):
            ang = math.radians(start + 90 * k / 5)
            pts.append((cx + d * math.cos(ang), cy + d * math.sin(ang)))
    # extra points along the straight sides keep the spline from cutting corners
    dense = []
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]
        dense.append(p)
        if math.hypot(q[0] - p[0], q[1] - p[1]) > 0.2:
            dense.append(((p[0] + q[0]) / 2, (p[1] + q[1]) / 2))
    out = []
    for i, (px, py) in enumerate(dense):
        x = bc[0] + math.cos(t) * px - math.sin(t) * py
        y = bc[1] + math.sin(t) * px + math.cos(t) * py
        out.append((x, y, level + 0.012 * math.sin(3 * i * 2 * math.pi / len(dense))))
    return out


def _lash(kit, mats, rng, root, box, amp, floor, tau, name):
    ring = _loop(box, amp, floor, tau)
    rope(kit, name, ring + ring[:3], 0.0105, mats["rope"], root, lay=0.075, step=0.012)
    # knot at the front-most point of the loop, ends hanging
    knot = min(ring, key=lambda p: p[1])
    kx, ky, kz = knot[0], knot[1] - 0.012, knot[2]
    kit.sphere(f"{name}_knot", 0.024, (kx, ky, kz), scale=(1.1, 0.9, 0.9), mat=mats["rope"], segments=8,
               parent=root)
    for side, drop in ((1, 0.22), (-1, 0.15)):
        rope(kit, f"{name}_end", [(kx, ky, kz), (kx + side * 0.03, ky - 0.02, kz - drop * 0.4),
                                  (kx + side * (0.05 + rng.uniform(0, 0.03)), ky - 0.035, kz - drop)],
             0.0085, mats["rope"], root, lay=0.06, step=0.012)


def build(kit, mats, rng):
    root = kit.group("tarp")
    _tarp_mesh(kit, mats, root)
    big, mid = crates.BIG, crates.MID
    _lash(kit, mats, rng, root, big, big[2] + CLOTH, 0.0, TAU_BIG, "lashing_low")
    _lash(kit, mats, rng, root, mid, mid[2] + CLOTH + LID_RAISE, big[2] + CLOTH, TAU_MID, "lashing_high")
    return root

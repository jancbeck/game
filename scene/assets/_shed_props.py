"""Things in the cookhouse: provisions on the beams, work table, shelves, firewood, barrels, pots.

All positions are shed space (X east, Y toward the tower wall, Z up). The tower face is at
y = 2.13, the wall stair's flank at x = -2.15 and the board wall on the right at x = 2.09. The
bread oven (see _shed_hearth) stands in the front bay. A strip about 0.5 m wide along the stair's
flank stays clear: it is the way from the front to the store door left of the hearth.
"""

import math

from . import _shed_geo as geo
from . import _shed_roof as roof

WALL_Y = 2.13
EAST_X = 2.07          # inner face of the board wall on the right


def header_bottom(x):
    return roof.surface(x, roof.Y_P) - roof.UNDER - roof.HEADER_H


# ---- small things --------------------------------------------------------------------------

def jar(kit, mats, root, name, loc, r=0.07, h=0.18, covered=True):
    """Dark crock, usually with a burlap cover tied down by a rope."""
    x, y, z = loc
    kit.cylinder(f"{name}_body", r, h, (x, y, z + h / 2), mat=mats["wood_dark"], radius_top=r * 0.82,
                 segments=12, bevel=0.004, parent=root)
    kit.torus(f"{name}_lip", r * 0.86, 0.012, (x, y, z + h), mat=mats["wood_dark"], major_segments=12,
              minor_segments=4, parent=root)
    if covered:
        kit.cylinder(f"{name}_cloth", r * 1.0, 0.03, (x, y, z + h + 0.012), mat=mats["burlap"], segments=12,
                     radius_top=r * 0.7, parent=root)
        kit.torus(f"{name}_tie", r * 0.9, 0.007, (x, y, z + h - 0.005), mat=mats["rope"], major_segments=12,
                  minor_segments=4, parent=root)


def pot(kit, mats, root, name, loc, r=0.12, h=0.16, handle=True):
    """Black iron cooking pot."""
    x, y, z = loc
    kit.cylinder(f"{name}_body", r, h, (x, y, z + h / 2), mat=mats["iron"], radius_top=r * 0.9, segments=14,
                 bevel=0.004, parent=root)
    kit.torus(f"{name}_rim", r * 0.9, 0.01, (x, y, z + h), mat=mats["iron"], major_segments=14,
              minor_segments=4, parent=root)
    if handle:
        kit.torus(f"{name}_bail", r * 0.9, 0.006, (x, y, z + h), (90, 0, 0), mats["iron"],
                  major_segments=14, minor_segments=4, parent=root)


def bowl(kit, mats, root, name, loc, r=0.1, h=0.07, mat=None):
    x, y, z = loc
    kit.cylinder(name, r * 0.6, h, (x, y, z + h / 2), mat=mat or mats["wood_old"], radius_top=r, segments=12,
                 parent=root)


def sack(kit, mats, root, name, loc, rot_z=0, s=1.0):
    """Slumped grain sack with a tied neck."""
    x, y, z = loc
    g = kit.group(name, (x, y, z), parent=root)
    g.rotation_euler = (0, 0, math.radians(rot_z))
    kit.sphere("belly", 0.26 * s, (0, 0, 0.22 * s), scale=(0.95, 0.7, 0.85), mat=mats["burlap"], segments=14,
               parent=g)
    kit.cylinder("neck", 0.07 * s, 0.1 * s, (0, 0, 0.45 * s), mat=mats["burlap"], radius_top=0.05 * s,
                 segments=8, parent=g)
    kit.torus("tie", 0.062 * s, 0.01, (0, 0, 0.42 * s), mat=mats["rope"], major_segments=10, minor_segments=4,
              parent=g)


def barrel(kit, mats, root, name, x, y, h=0.82, r=0.3, lid=True):
    wo, iron = mats["wood_old"], mats["iron"]
    kit.cylinder(f"{name}_lo", r * 0.9, h * 0.36, (x, y, h * 0.18), mat=wo, radius_top=r, segments=16, parent=root)
    kit.cylinder(f"{name}_mid", r, h * 0.28, (x, y, h * 0.5), mat=wo, segments=16, parent=root)
    kit.cylinder(f"{name}_hi", r, h * 0.36, (x, y, h * 0.82), mat=wo, radius_top=r * 0.9, segments=16, parent=root)
    for n, (z, rr) in enumerate(((0.1, 0.9), (0.3, 0.98), (0.7, 0.98), (0.9, 0.9))):
        kit.torus(f"{name}_hoop_{n}", r * rr + 0.006, 0.012, (x, y, z * h), mat=iron, major_segments=16,
                  minor_segments=4, parent=root)
    if lid:
        kit.cylinder(f"{name}_lid", r * 0.9, 0.03, (x, y, h + 0.012), mat=wo, segments=16, bevel=0.004, parent=root)


def bucket(kit, mats, root, name, x, y, z=0.0):
    wo, iron = mats["wood_old"], mats["iron"]
    kit.cylinder(f"{name}_body", 0.15, 0.3, (x, y, z + 0.15), mat=wo, radius_top=0.18, segments=14, parent=root)
    kit.torus(f"{name}_hoop", 0.17, 0.008, (x, y, z + 0.24), mat=iron, major_segments=14, minor_segments=4,
              parent=root)
    kit.torus(f"{name}_bail", 0.18, 0.006, (x, y, z + 0.3), (90, 0, 0), mats["rope"], major_segments=14,
              minor_segments=4, parent=root)


def stool(kit, mats, rng, root, name, x, y, h=0.4):
    wo, wd = mats["wood_old"], mats["wood_dark"]
    for n in range(3):
        a = math.radians(90 + 120 * n + rng.uniform(-8, 8))
        kit.beam(f"{name}_leg_{n}", (x + 0.1 * math.cos(a), y + 0.1 * math.sin(a), 0.0),
                 (x + 0.15 * math.cos(a), y + 0.15 * math.sin(a), h), (0.04, 0.04), wd, parent=root)
    kit.cylinder(f"{name}_seat", 0.17, 0.04, (x, y, h + 0.02), mat=wo, segments=12, bevel=0.004, parent=root)


# ---- provisions hung from beams --------------------------------------------------------------

class Provisions:
    """Hams, sausages, herbs and onions, collected into five objects so a row of them stays cheap."""

    def __init__(self, rng):
        self.rng = rng
        self.rope, self.meat, self.herb, self.onion, self.iron = (geo.Mesh() for _ in range(5))

    def hook(self, x, y, z):
        self.iron.cyl((x, y, z), (x, y, z - 0.07), 0.007, sides=5)

    def ham(self, x, y, ztop, s=1.0):
        self.hook(x, y, ztop)
        cord = 0.14 * s
        self.rope.cyl((x, y, ztop), (x, y, ztop - cord), 0.006, sides=5)
        zc = ztop - cord - 0.17 * s
        self.meat.ellipsoid((x, y, zc), (0.095 * s, 0.085 * s, 0.17 * s), (self.rng.uniform(-6, 6), 0, 0))
        self.meat.cyl((x, y, zc - 0.12 * s), (x, y, zc - 0.26 * s), 0.036 * s, 0.026 * s, sides=7)
        self.rope.cyl((x, y, zc + 0.1 * s), (x, y, zc + 0.125 * s), 0.052 * s, sides=8)

    def sausages(self, x, y, ztop, n=4):
        self.hook(x, y, ztop)
        self.rope.cyl((x, y, ztop), (x, y, ztop - 0.07), 0.005, sides=5)
        zs = ztop - 0.07
        self.rope.cyl((x - 0.13, y, zs), (x + 0.13, y, zs), 0.007, sides=5)
        for i in range(n):
            xi = x - 0.1 + 0.2 * i / max(1, n - 1)
            ln = self.rng.uniform(0.2, 0.28)
            self.meat.cyl((xi, y, zs), (xi + self.rng.uniform(-0.01, 0.01), y, zs - ln), 0.024, 0.022, sides=7)

    def herbs(self, x, y, ztop, n=3):
        self.hook(x, y, ztop)
        self.rope.cyl((x, y, ztop), (x, y, ztop - 0.05), 0.005, sides=5)
        zs = ztop - 0.05
        self.rope.cyl((x - 0.11, y, zs), (x + 0.11, y, zs), 0.007, sides=5)
        for i in range(n):
            xi = x - 0.09 + 0.18 * i / max(1, n - 1)
            ln = self.rng.uniform(0.26, 0.36)
            self.herb.cyl((xi, y, zs - 0.01), (xi + self.rng.uniform(-0.02, 0.02), y, zs - ln), 0.07, 0.014, sides=7,
                          twist=i)
            self.herb.cyl((xi, y, zs - ln), (xi, y, zs - ln + 0.015), 0.07, sides=7)

    def onions(self, x, y, ztop, n=6):
        self.hook(x, y, ztop)
        self.rope.cyl((x, y, ztop), (x, y, ztop - 0.1 - 0.075 * n), 0.007, sides=5)
        for i in range(n):
            self.onion.ellipsoid((x + (0.028 if i % 2 else -0.028), y, ztop - 0.1 - 0.075 * i),
                                 (0.05, 0.05, 0.043), segments=8)

    def finish(self, mats, root):
        self.rope.finish("prov_cord", mats["rope"], root)
        self.meat.finish("prov_meat", mats["cloth_red"], root, smooth=True)
        self.herb.finish("prov_herbs", mats["burlap"], root)
        self.onion.finish("prov_onions", mats["straw"], root, smooth=True)
        self.iron.finish("prov_hooks", mats["iron"], root)


def front_provisions(kit, mats, rng, root):
    """Hung from the front header, clear of the oven mouth, and a pole of provisions across the rafters inside."""
    p = Provisions(rng)
    y = roof.Y_P - 0.03
    for x, kind, s in ((-0.14, "herbs", 1), (0.1, "ham", 1), (0.3, "herbs", 1), (0.95, "onions", 1),
                       (1.14, "sausages", 1), (1.36, "ham", 1.0), (1.58, "herbs", 1), (1.78, "ham", 0.9)):
        zt = header_bottom(x)
        if kind == "ham":
            p.ham(x, y, zt, s)
        elif kind == "sausages":
            p.sausages(x, y, zt)
        elif kind == "herbs":
            p.herbs(x, y, zt)
        else:
            p.onions(x, y, zt)
    p.finish(mats, root)
    # a pole across the rafters inside carries the rest of the winter store
    q = Provisions(rng)
    yp, zp = 0.3, 2.95
    kit.beam("store_pole", (-1.95, yp, zp), (1.65, yp, zp + 0.02), (0.06, 0.06), mats["wood_dark"], bevel=0.008,
             parent=root)
    for n, x in enumerate((-1.75, 1.6)):
        top = roof.surface(x, yp) - roof.UNDER
        kit.cylinder(f"store_hanger_{n}", 0.009, top - zp, (x, yp, (top + zp) / 2), mat=mats["iron"], segments=5,
                     parent=root)
    for x, kind in ((-1.5, "ham"), (-1.15, "herbs"), (-0.8, "ham"), (-0.4, "sausages"), (-0.05, "ham"),
                    (0.35, "onions"), (0.7, "sausages"), (1.05, "herbs"), (1.35, "ham")):
        zt = zp - 0.03
        if kind == "ham":
            q.ham(x, yp, zt, rng.uniform(0.85, 1.1))
        elif kind == "sausages":
            q.sausages(x, yp, zt)
        elif kind == "herbs":
            q.herbs(x, yp, zt)
        else:
            q.onions(x, yp, zt)
    q.finish(mats, root)


# ---- wall racks, shelves ---------------------------------------------------------------------

def _peg(kit, mats, root, name, x, y, z, along="x"):
    if along == "x":
        kit.cylinder(name, 0.012, 0.1, (x, y, z), (0, 90, 0), mats["iron"], segments=8, parent=root)
    else:
        kit.cylinder(name, 0.012, 0.1, (x, y, z), (90, 0, 0), mats["iron"], segments=8, parent=root)


def east_rack(kit, mats, rng, root):
    """Peg board on the right wall with the cooking tools hung from it: ladle, skimmer, cleaver, whisk, tongs."""
    wd, wo, iron = mats["wood_dark"], mats["wood_old"], mats["iron"]
    z = 1.62
    kit.box("east_rack_board", (0.04, 2.1, 0.12), (EAST_X - 0.02, 0.45, z), (0, 0, 0), wd, bevel=0.006, parent=root)
    x = EAST_X - 0.1
    for n, y in enumerate((-0.5, -0.2, 0.1, 0.4, 0.7, 1.0, 1.3)):
        _peg(kit, mats, root, f"east_peg_{n}", x + 0.05, y, z - 0.01)
    # ladle
    kit.beam("ladle_handle", (x, -0.5, z - 0.03), (x, -0.5, z - 0.5), (0.014, 0.014), wo, parent=root)
    kit.cylinder("ladle_bowl", 0.05, 0.04, (x, -0.5, z - 0.53), mat=iron, radius_top=0.065, segments=10, parent=root)
    # skimmer: a flat dish on a long handle
    kit.beam("skimmer_handle", (x, -0.2, z - 0.03), (x, -0.2, z - 0.45), (0.014, 0.014), wo, parent=root)
    kit.cylinder("skimmer_dish", 0.075, 0.01, (x, -0.2, z - 0.5), (0, 90, 0), iron, segments=14, parent=root)
    # cleaver and a knife
    kit.box("cleaver_blade", (0.012, 0.16, 0.12), (x, 0.1, z - 0.13), (0, 0, 0), iron, bevel=0.002, parent=root)
    kit.box("cleaver_grip", (0.025, 0.03, 0.11), (x, 0.1, z - 0.02), (0, 0, 0), wo, parent=root)
    # whisk of birch twigs
    kit.cylinder("whisk", 0.04, 0.3, (x, 0.4, z - 0.2), mat=mats["straw"], radius_top=0.012, segments=8, parent=root)
    # pot and a pan hung by their handles
    pot(kit, mats, root, "rack_pot", (x - 0.12, 0.7, z - 0.4), 0.1, 0.12, handle=False)
    kit.beam("pan_handle", (x, 1.0, z - 0.03), (x, 1.0, z - 0.4), (0.02, 0.012), iron, parent=root)
    kit.cylinder("pan", 0.12, 0.03, (x - 0.03, 1.0, z - 0.52), mat=iron, radius_top=0.13, segments=14, parent=root)
    # shelf under it with crocks
    z2 = 1.0
    kit.box("east_shelf", (0.26, 1.2, 0.035), (EAST_X - 0.13, 0.95, z2), mat=wo, bevel=0.006, parent=root)
    for b, yb in enumerate((0.4, 1.5)):
        kit.beam(f"east_bracket_{b}", (EAST_X - 0.01, yb, z2 - 0.22), (EAST_X - 0.2, yb, z2 - 0.02), (0.035, 0.035),
                 wd, bevel=0.004, parent=root)
    jar(kit, mats, root, "east_jar_a", (EAST_X - 0.14, 0.55, z2 + 0.0175), 0.065, 0.2)
    jar(kit, mats, root, "east_jar_b", (EAST_X - 0.15, 0.85, z2 + 0.0175), 0.08, 0.17)
    jar(kit, mats, root, "east_jar_c", (EAST_X - 0.14, 1.15, z2 + 0.0175), 0.06, 0.15, covered=False)
    bowl(kit, mats, root, "east_bowl", (EAST_X - 0.14, 1.4, z2 + 0.0175), 0.09, 0.07)


def wall_shelves(kit, mats, rng, root):
    """Two shelves on the back wall right of the hearth, and two short ones on the stair's flank."""
    wd, wo = mats["wood_dark"], mats["wood_old"]
    dx = 2.1                               # the back-wall shelves stand this far east of their layout
    for n, (z, x0, x1) in enumerate(((1.35, -1.85 + dx, -0.45 + dx), (1.8, -1.7 + dx, -0.6 + dx))):
        w = x1 - x0
        xc = (x0 + x1) / 2
        kit.box(f"tower_shelf_{n}", (w, 0.24, 0.035), (xc, WALL_Y - 0.13, z), (0, 0, 0), wo, bevel=0.006,
                parent=root)
        for b, xb in enumerate((x0 + 0.12, x1 - 0.12)):
            kit.beam(f"tower_bracket_{n}_{b}", (xb, WALL_Y - 0.03, z - 0.2), (xb, WALL_Y - 0.22, z - 0.02),
                     (0.035, 0.035), wd, bevel=0.004, parent=root)
    z = 1.35 + 0.0175
    pot(kit, mats, root, "shelf_pot_a", (-1.7 + dx, WALL_Y - 0.14, z), 0.1, 0.13)
    pot(kit, mats, root, "shelf_pot_b", (-1.38 + dx, WALL_Y - 0.15, z), 0.12, 0.15)
    jar(kit, mats, root, "shelf_jar_a", (-1.05 + dx, WALL_Y - 0.14, z), 0.07, 0.17)
    bowl(kit, mats, root, "shelf_bowl_a", (-0.78 + dx, WALL_Y - 0.14, z), 0.1, 0.07)
    bowl(kit, mats, root, "shelf_bowl_b", (-0.78 + dx, WALL_Y - 0.14, z + 0.07), 0.095, 0.07)
    z = 1.8 + 0.0175
    jar(kit, mats, root, "up_jar_a", (-1.5 + dx, WALL_Y - 0.13, z), 0.06, 0.14)
    jar(kit, mats, root, "up_jar_b", (-1.32 + dx, WALL_Y - 0.14, z), 0.07, 0.19)
    jar(kit, mats, root, "up_jar_c", (-1.12 + dx, WALL_Y - 0.14, z), 0.065, 0.16, covered=False)
    for n, z in enumerate((1.05, 1.55)):
        kit.box(f"wall_shelf_{n}", (0.26, 1.1 - 0.3 * n, 0.035), (-2.15 + 0.14, 0.4 + 0.15 * n, z), (0, 0, 0), wo,
                bevel=0.006, parent=root)
        for b, yb in enumerate((-0.05 + 0.15 * n, 0.85)):
            kit.beam(f"wall_bracket_{n}_{b}", (-2.12, yb, z - 0.2), (-1.95, yb, z - 0.02), (0.035, 0.035), wd,
                     bevel=0.004, parent=root)
    jar(kit, mats, root, "wall_jar_a", (-1.98, 0.1, 1.0675), 0.07, 0.17)
    pot(kit, mats, root, "wall_pot_a", (-1.98, 0.5, 1.0675), 0.1, 0.13)
    jar(kit, mats, root, "wall_jar_b", (-1.98, 0.8, 1.0675), 0.065, 0.14, covered=False)
    bowl(kit, mats, root, "wall_bowl_a", (-1.98, 0.35, 1.5675), 0.09, 0.07)
    jar(kit, mats, root, "wall_jar_d", (-1.98, 0.68, 1.5675), 0.075, 0.2)


# ---- work table ------------------------------------------------------------------------------

def work_table(kit, mats, rng, root):
    """Work table right of the hearth: laid out at x -1.8..-0.5 and moved east as a group."""
    wo, wd, iron = mats["wood_old"], mats["wood_dark"], mats["iron"]
    root = kit.group("work_table", (1.95, 0.05, 0.0), parent=root)
    x0, x1, y0, y1, top = -1.8, -0.5, 0.3, 1.1, 0.9
    xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    for n, (px, py) in enumerate(((x0 + 0.08, y0 + 0.07), (x1 - 0.08, y0 + 0.07), (x0 + 0.08, y1 - 0.07),
                                  (x1 - 0.08, y1 - 0.07))):
        kit.beam(f"table_leg_{n}", (px, py, 0.0), (px + rng.uniform(-0.008, 0.008), py, top - 0.04), (0.09, 0.09),
                 wd, bevel=0.008, parent=root)
    for n, y in enumerate((y0 + 0.07, y1 - 0.07)):
        kit.box(f"table_rail_{n}", (x1 - x0, 0.05, 0.1), (xc, y, top - 0.1), mat=wd, bevel=0.006, parent=root)
    kit.box("table_shelf", (x1 - x0 - 0.1, y1 - y0 - 0.1, 0.03), (xc, yc, 0.3), mat=wo, bevel=0.005, parent=root)
    y = y0 - 0.01
    for n, w in enumerate((0.2, 0.19, 0.21, 0.2)):
        kit.box(f"table_top_{n}", (x1 - x0 + 0.05, w, 0.045), (xc, y + w / 2, top),
                (rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0), wo if n != 2 else wd, bevel=0.008, parent=root)
        y += w + 0.012
    zt = top + 0.0225
    # board with a loaf being cut, cleaver stuck in the board, a knife
    kit.box("cutting_board", (0.42, 0.28, 0.035), (-1.35, 0.62, zt + 0.0175), (0, 0, 6), wd, bevel=0.006, parent=root)
    loaves = geo.Mesh()
    for n, (lx, ly, ang) in enumerate(((-0.95, 0.55, 20), (-0.82, 0.72, -10), (-0.9, 0.9, 35))):
        loaves.ellipsoid((lx, ly, zt + 0.06), (0.14, 0.09, 0.065), (0, 0, ang), segments=10)
    loaves.ellipsoid((-1.32, 0.62, zt + 0.1), (0.12, 0.08, 0.06), (0, 0, 8), segments=10)
    loaves.finish("loaves", mats["straw"], root, smooth=True)
    kit.box("table_cleaver", (0.15, 0.012, 0.1), (-1.5, 0.7, zt + 0.1), (0, 0, 12), iron, parent=root)
    kit.box("table_knife", (0.2, 0.02, 0.008), (-1.18, 0.42, zt + 0.06), (0, 0, -25), iron, parent=root)
    kit.box("table_cloth", (0.34, 0.26, 0.012), (-0.65, 0.5, zt + 0.006), (0, 0, -8), mats["cloth_emblem"],
            parent=root)
    bowl(kit, mats, root, "table_bowl_a", (-1.7, 0.45, zt), 0.1, 0.07)
    bowl(kit, mats, root, "table_bowl_b", (-1.7, 0.45, zt + 0.07), 0.095, 0.07)
    pot(kit, mats, root, "table_pot", (-1.62, 0.92, zt), 0.1, 0.13)
    jar(kit, mats, root, "table_jug", (-0.62, 0.93, zt), 0.06, 0.22, covered=False)
    kit.cylinder("rolling_pin", 0.022, 0.32, (-1.25, 0.95, zt + 0.022), (0, 90, 4), wo, segments=8, parent=root)
    onions = geo.Mesh()
    for n in range(5):
        onions.ellipsoid((-1.05 + rng.uniform(-0.07, 0.07), 1.0 + rng.uniform(-0.04, 0.04), zt + 0.045 + 0.02 * (n % 2)),
                         (0.05, 0.05, 0.043), segments=8)
    onions.finish("table_onions", mats["burlap"], root, smooth=True)


def front_table(kit, mats, rng, root):
    """Low prep table in the front bay, in front of the oven: it shows under the header at the main camera."""
    wo, wd, iron = mats["wood_old"], mats["wood_dark"], mats["iron"]
    x0, x1, y0, y1, top = -0.1, 0.7, -1.62, -1.0, 0.88
    xc = (x0 + x1) / 2
    for n, (px, py) in enumerate(((x0 + 0.06, y0 + 0.06), (x1 - 0.06, y0 + 0.06), (x0 + 0.06, y1 - 0.06),
                                  (x1 - 0.06, y1 - 0.06))):
        kit.beam(f"ftable_leg_{n}", (px, py, 0.0), (px, py, top - 0.04), (0.08, 0.08), wd, bevel=0.008, parent=root)
    kit.box("ftable_rail", (x1 - x0, 0.04, 0.09), (xc, y0 + 0.06, top - 0.09), mat=wd, bevel=0.005, parent=root)
    y = y0 - 0.01
    for n, w in enumerate((0.21, 0.2, 0.21)):
        kit.box(f"ftable_top_{n}", (x1 - x0 + 0.05, w, 0.045), (xc, y + w / 2, top),
                (rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0), wo if n != 1 else wd, bevel=0.008, parent=root)
        y += w + 0.01
    zt = top + 0.0225
    loaves = geo.Mesh()
    for lx, ly, ang in ((0.0, -1.2, 15), (0.17, -1.14, -20), (0.08, -1.32, 40)):
        loaves.ellipsoid((lx, ly, zt + 0.065), (0.14, 0.09, 0.07), (0, 0, ang), segments=10)
    loaves.finish("ftable_loaves", mats["straw"], root, smooth=True)
    kit.box("ftable_cloth", (0.3, 0.24, 0.014), (0.46, -1.32, zt + 0.007), (0, 0, 10), mats["cloth_emblem"],
            parent=root)
    pot(kit, mats, root, "ftable_pot", (0.55, -1.12, zt), 0.12, 0.15)
    bowl(kit, mats, root, "ftable_bowl_a", (-0.0, -1.5, zt), 0.1, 0.07)
    bowl(kit, mats, root, "ftable_bowl_b", (-0.0, -1.5, zt + 0.07), 0.095, 0.07)
    kit.box("ftable_cleaver", (0.15, 0.012, 0.1), (0.33, -1.5, zt + 0.1), (0, 0, 8), iron, parent=root)


# ---- firewood --------------------------------------------------------------------------------

def log_rick(kit, mats, rng, root, name, x_c, y_front, depth, cols, rows, d=0.15):
    """Split logs with their ends facing the front (-Y), cols wide and rows high, ragged at the top."""
    ma, mb = geo.Mesh(), geo.Mesh()
    for row in range(rows):
        n = cols - (row % 2)
        for c in range(n):
            if row >= rows - 2 and rng.random() < 0.35:
                continue
            x = x_c + (c - (n - 1) / 2) * d + rng.uniform(-0.01, 0.01)
            z = d * 0.5 + row * d * 0.88
            r = rng.uniform(0.058, 0.074)
            y0 = y_front + rng.uniform(-0.03, 0.03)
            length = depth + rng.uniform(-0.06, 0.03)
            (ma if rng.random() < 0.6 else mb).cyl((x, y0, z), (x + rng.uniform(-0.01, 0.01), y0 + length, z), r,
                                                    r * 0.96, sides=7, twist=rng.uniform(0, 6))
    ma.finish(f"{name}_a", mats["wood_old"], root)
    mb.finish(f"{name}_b", mats["wood_dark"], root)


def chopping_block(kit, mats, rng, root, loc=(1.12, -0.2)):
    """Log round with the cleaver in it and split kindling around."""
    x, y = loc
    wo, iron = mats["wood_old"], mats["iron"]
    h = 0.5
    kit.cylinder("block", 0.2, h, (x, y, h / 2), mat=wo, radius_top=0.19, segments=14, bevel=0.01, parent=root)
    kit.box("block_cleaver", (0.2, 0.014, 0.12), (x + 0.02, y, h + 0.05), (0, 0, 12), iron, bevel=0.002, parent=root)
    kit.box("block_cleaver_grip", (0.1, 0.03, 0.03), (x + 0.16, y + 0.02, h + 0.09), (0, 0, 12), wo, parent=root)
    kind = geo.Mesh()
    for n in range(7):
        a = rng.uniform(0, 360)
        dist = rng.uniform(0.28, 0.5)
        px, py = x + dist * math.cos(math.radians(a)), y + dist * math.sin(math.radians(a))
        kind.box((rng.uniform(0.25, 0.4), 0.045, 0.04), (px, py, 0.022), (0, 0, rng.uniform(0, 180)))
    kind.finish("kindling", wo, root)


def litter(kit, mats, rng, root):
    """Straw, onion skins and bones on the floor, charcoal by the hearth."""
    coal = geo.Mesh()
    for _ in range(36):
        px, py = rng.gauss(-0.67, 0.35), rng.uniform(0.8, 1.0)
        s = rng.uniform(0.012, 0.03)
        coal.box((s, s * rng.uniform(0.6, 1.2), s * 0.7), (px, py, s * 0.3),
                 (rng.uniform(-30, 30), rng.uniform(-30, 30), rng.uniform(0, 180)))
    coal.finish("charcoal", mats["iron"], root)
    chips = geo.Mesh()
    for _ in range(40):
        px, py = rng.uniform(0.55, 1.9), rng.uniform(-0.8, 0.5)
        if (px - 1.12) ** 2 + (py + 0.2) ** 2 > 0.7:
            continue
        chips.box((rng.uniform(0.03, 0.08), rng.uniform(0.012, 0.03), 0.006), (px, py, 0.004),
                  (rng.uniform(-10, 10), 0, rng.uniform(0, 180)))
    chips.finish("wood_chips", mats["wood_old"], root)
    straw = geo.Mesh()
    for _ in range(70):
        px, py = rng.uniform(-1.9, 0.0), rng.uniform(-1.5, 0.8)
        straw.box((rng.uniform(0.15, 0.35), 0.008, 0.006), (px, py, 0.004 + 0.01 * rng.random()),
                  (0, rng.uniform(-8, 8), rng.uniform(0, 180)))
    straw.finish("floor_straw", mats["straw"], root)

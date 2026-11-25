"""Cookhouse fittings on its walls and eave: the store door into the NW tower, the water butt and its gutter.

Shed space: X east, Y toward the tower wall (+Y), Z up. The tower face is at y = 2.13, the wall
stair's flank at x = -2.15 and the front eave at y = -2.17.

- Store door: a low plank door in a dressed-stone surround on the tower face, left of the hearth,
  into the tower's ground-floor store. It is shut with a hasp and staple; the threshold is worn.
- Board infill: the stair ends about 0.5 m short of the tower, so a few upright boards close the
  cookhouse's left side between the stair end and the tower.
- Water butt: an open cask under the front-right corner of the eave. A gutter of two boards hung on
  iron hooks under the eave falls toward it and spills into it.
"""

import math

from . import _shed_hearth as hearth
from . import _shed_roof as roof
from .drip_bucket import _glossy

WALL_Y = 2.13
DOOR_X, DOOR_W, DOOR_H = -1.76, 0.68, 1.78
BUTT = (2.12, -2.45)
STAIR_END_Y = 1.63          # where the wall stair ends, short of the tower face


def store_door(kit, mats, rng, root):
    st, wd, wo, iron = mats["stone_wall"], mats["wood_dark"], mats["wood_old"], mats["iron"]
    cut = hearth._dressed(st)
    x0, x1 = DOOR_X - DOOR_W / 2, DOOR_X + DOOR_W / 2
    # surround: jamb stones in alternating heights, a lintel, a worn threshold
    z = 0.0
    for n, h in enumerate((0.42, 0.36, 0.44, 0.38, 0.18)):
        for s, xj in enumerate((x0 - 0.07, x1 + 0.07)):
            w = 0.14 + (0.04 if (n + s) % 2 else 0.0)
            xc = xj - (w - 0.14) / 2 if s == 0 else xj + (w - 0.14) / 2
            kit.box(f"store_jamb_{s}_{n}", (w, 0.07, h - 0.01), (xc, WALL_Y - 0.03, z + h / 2),
                    (0, rng.uniform(-0.6, 0.6), 0), cut, bevel=0.012, parent=root)
        z += h
    kit.box("store_lintel", (DOOR_W + 0.46, 0.09, 0.24), (DOOR_X, WALL_Y - 0.035, DOOR_H + 0.12), mat=cut,
            bevel=0.015, parent=root)
    kit.box("store_threshold", (DOOR_W + 0.1, 0.24, 0.06), (DOOR_X, WALL_Y - 0.1, 0.03), mat=cut, bevel=0.02,
            parent=root)
    kit.box("store_threshold_wear", (DOOR_W * 0.55, 0.16, 0.012), (DOOR_X + 0.03, WALL_Y - 0.12, 0.058),
            mat=mats["mud"], parent=root)
    # leaf: five planks set a little back in the opening, two ledges, strap hinges, hasp and staple
    y = WALL_Y - 0.005
    x = x0 + 0.01
    for n in range(5):
        w = (DOOR_W - 0.02) / 5 - 0.006
        kit.box(f"store_plank_{n}", (w, 0.04, DOOR_H - 0.03 - rng.uniform(0, 0.02)),
                (x + w / 2, y, 0.06 + (DOOR_H - 0.06) / 2), (0, rng.uniform(-0.3, 0.3), 0), wo if n % 3 else wd,
                bevel=0.005, parent=root)
        x += w + 0.006
    for n, zl in enumerate((0.35, 1.45)):
        kit.box(f"store_ledge_{n}", (DOOR_W - 0.08, 0.03, 0.13), (DOOR_X, y - 0.035, zl), mat=wd, bevel=0.005,
                parent=root)
        kit.box(f"store_hinge_{n}", (DOOR_W * 0.7, 0.012, 0.045), (x0 + DOOR_W * 0.35, y - 0.056, zl), mat=iron,
                bevel=0.003, parent=root)
        kit.cylinder(f"store_pintle_{n}", 0.018, 0.08, (x0 - 0.02, y - 0.04, zl), mat=iron, segments=8,
                     parent=root)
    kit.box("store_hasp", (0.05, 0.012, 0.2), (x1 - 0.06, y - 0.058, 1.0), mat=iron, bevel=0.003, parent=root)
    kit.torus("store_staple", 0.03, 0.007, (x1 + 0.03, y - 0.07, 0.92), (0, 90, 0), iron, major_segments=10,
              minor_segments=4, parent=root)
    kit.torus("store_ring", 0.045, 0.008, (DOOR_X + 0.12, y - 0.07, 0.95), (90, 0, 0), iron, major_segments=12,
              minor_segments=4, parent=root)
    # a flour sack and a crock waiting by the door
    from . import _shed_props as props
    props.sack(kit, mats, root, "store_sack", (-1.92, 1.55, 0.0), rot_z=15, s=0.8)


def water_butt(kit, mats, rng, root):
    wo, wd, iron = mats["wood_old"], mats["wood_dark"], mats["iron"]
    bx, by = BUTT
    h, r = 0.95, 0.34
    # staves as narrow boxes round a slightly bellied cask, open at the top
    staves = 18
    for i in range(staves):
        a = 2 * math.pi * i / staves
        for k, (z0, z1, rr) in enumerate(((0.0, 0.32, 0.92), (0.32, 0.63, 1.0), (0.63, h, 0.95))):
            rad = r * rr
            kit.box(f"butt_stave_{i}_{k}", (2 * math.pi * rad / staves * 1.02, 0.035, z1 - z0),
                    (bx + rad * math.cos(a), by + rad * math.sin(a), (z0 + z1) / 2),
                    (0, 0, math.degrees(a) + 90), wo if (i * 7) % 5 else wd, parent=root)
    for n, (z, rr) in enumerate(((0.1, 0.93), (0.36, 1.0), (0.62, 1.0), (0.88, 0.96))):
        kit.torus(f"butt_hoop_{n}", r * rr + 0.02, 0.012, (bx, by, z), mat=iron, major_segments=20,
                  minor_segments=4, parent=root)
    kit.cylinder("butt_water", r * 0.94, 0.02, (bx, by, h - 0.12), mat=_glossy("rainwater", (0.03, 0.04, 0.05, 1.0)),
                 segments=20, parent=root)
    kit.cylinder("butt_bottom", r * 0.9, 0.04, (bx, by, 0.02), mat=wd, segments=20, parent=root)
    # a dipper hung on the rim
    kit.beam("butt_dipper_handle", (bx - 0.2, by - 0.22, h + 0.02), (bx - 0.4, by - 0.38, h - 0.35), (0.02, 0.02), wo,
             parent=root)
    # gutter: two boards in a V, hung on iron hooks under the eave, falling toward the butt
    xa, xb = -0.3, bx + 0.08
    yg = roof.Y_F - 0.1
    za = roof.surface(xa, roof.Y_F) - 0.24
    zb = za - 0.12
    length = xb - xa
    ang = math.degrees(math.atan2(za - zb, length))
    zc = (za + zb) / 2
    for s in (-1, 1):
        kit.box(f"gutter_board_{s}", (length, 0.02, 0.12), ((xa + xb) / 2, yg + s * 0.04, zc), (-s * 35, ang, 0), wo,
                bevel=0.004, parent=root)
    for n, x in enumerate((0.3, 1.1, 1.85)):
        zt = za + (zb - za) * (x - xa) / length
        kit.beam(f"gutter_hook_{n}", (x, roof.Y_F - 0.03, zt + 0.16), (x, yg, zt - 0.06), (0.012, 0.012), iron,
                 parent=root)

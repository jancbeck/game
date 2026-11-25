"""The map of the march: a painted board in a plain oak frame, pinned to the back wall.

1.0 x 0.78 m, its middle 1.4 m over the floor. Origin: the middle of the board's foot on the wall's inner face. The
paint is the procedural `map_board` material on a UV quad: the north road in red, the river in blue-grey and the
garrison as a black tower where they nearly cross, pin holes along the road. Four iron nails hold the frame.
"""

from . import _tower as T

LIGHTS = []
W, H, Z0 = 1.0, 0.78, 1.02


def build(kit, mats, rng):
    root = kit.group("tower_map")
    wd, iron = mats["wood_dark"], mats["iron"]
    kit.box("map_backing", (W, 0.03, H), (0, -0.015, Z0 + H / 2), mat=mats["wood_old"], bevel=0.004, parent=root)
    y = -0.034
    T.quad_uv(kit, "map_paint", [(-W / 2 + 0.03, y, Z0 + 0.03), (W / 2 - 0.03, y, Z0 + 0.03), (W / 2 - 0.03, y, Z0 + H - 0.03),
                                 (-W / 2 + 0.03, y, Z0 + H - 0.03)], mats["map_board"], root)
    for n, (cx, cz, sx, sz) in enumerate(((0, Z0 + 0.015, W, 0.04), (0, Z0 + H - 0.015, W, 0.04), (-W / 2 + 0.015, Z0 + H / 2, 0.04, H),
                                          (W / 2 - 0.015, Z0 + H / 2, 0.04, H))):
        kit.box(f"frame_{n}", (sx, 0.045, sz), (cx, -0.026, cz), mat=wd, bevel=0.005, parent=root)
    for n, (nx, nz) in enumerate(((-W / 2 + 0.015, Z0 + 0.015), (W / 2 - 0.015, Z0 + 0.015), (-W / 2 + 0.015, Z0 + H - 0.015),
                                  (W / 2 - 0.015, Z0 + H - 0.015))):
        kit.cylinder(f"nail_{n}", 0.008, 0.02, (nx, -0.055, nz), (90, 0, 0), iron, segments=6, radius_top=0.012, parent=root)
    return root

"""Pot rack of a garrison kitchen: a rail on two posts with pots, ladles, sausages and onions hanging from it.

Free-standing. The rail runs along Y, 1.4 m long and 1.9 m high, on two posts 1.5 m apart with a
foot board under each. Origin: center of the footprint on the floor.
"""

from . import _kitchen
from . import _shed_props as props

LIGHTS = []
LEN, H = 1.5, 1.9


def build(kit, mats, rng):
    root = kit.group("kitchen_rack")
    wd, wo, iron = mats["wood_dark"], mats["wood_old"], mats["iron"]
    for n, s in enumerate((-1, 1)):
        y = s * LEN / 2
        kit.box(f"rack_foot_{n}", (0.55, 0.12, 0.08), (0, y, 0.04), mat=wd, bevel=0.008, parent=root)
        kit.beam(f"rack_post_{n}", (0, y, 0.05), (rng.uniform(-0.01, 0.01), y, H), (0.1, 0.1), wd, bevel=0.01,
                 parent=root)
        kit.beam(f"rack_brace_{n}", (0.0, y, 1.3), (0.0, y - s * 0.32, H - 0.05), (0.06, 0.06), wd, bevel=0.006,
                 parent=root)
    kit.beam("rack_rail", (0, -LEN / 2 - 0.34, H), (0, LEN / 2 + 0.34, H), (0.09, 0.09), wd, bevel=0.01, parent=root)
    # pots on hooks: iron pots, a pan with a long handle, two ladles
    for n, (y, drop, r) in enumerate(((-0.55, 0.30, 0.13), (-0.2, 0.42, 0.11), (0.2, 0.28, 0.14), (0.55, 0.4, 0.1))):
        kit.cylinder(f"rack_hook_{n}", 0.006, drop, (0.0, y, H - drop / 2), mat=iron, segments=5, parent=root)
        props.pot(kit, mats, root, f"rack_pot_{n}", (0.0, y, H - drop - 0.17), r, 0.17)
    kit.cylinder("rack_pan", 0.14, 0.03, (0.0, -0.85, H - 0.55), (0, 20, 0), mat=iron, segments=14, parent=root)
    kit.beam("rack_pan_handle", (0.0, -0.85, H - 0.55), (0.0, -0.85, H - 0.08), (0.02, 0.02), iron, parent=root)
    for n, y in enumerate((0.85, 1.0)):
        kit.beam(f"rack_ladle_{n}", (0.02, y, H - 0.04), (0.02, y + 0.03, H - 0.5), (0.016, 0.016), wo, parent=root)
        kit.cylinder(f"rack_ladle_bowl_{n}", 0.05, 0.05, (0.02, y + 0.03, H - 0.52), mat=iron, radius_top=0.07,
                     segments=10, parent=root)
    p = _kitchen.Provisions(rng)
    p.sausages(0.0, 0.88, H, 4)
    p.onions(0.0, -1.0, H, 6)
    p.herbs(0.0, 1.1, H, 3)
    p.finish(mats, root)
    return root

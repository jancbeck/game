"""A three-legged stool beside the bed in the commander's chamber, with a candle stub in a saucer, a small book and a cup of water.

0.45 m high. Origin: the middle of the stool on the floor. The candle is not lit: nobody lights a candle beside
a bed in a garrison that counts its tallow.
"""

from . import _kitchen
from . import _shed_props as props
from . import _tower as T

LIGHTS = []


def build(kit, mats, rng):
    root = kit.group("tower_stool")
    props.stool(kit, mats, rng, root, "bedside", 0.0, 0.0, h=0.45)
    z = 0.47
    _kitchen.lathe(kit, "saucer", [(0.0, 0.0), (0.06, 0.0), (0.075, 0.012), (0.0, 0.006)], 14, mats["clay"], (-0.05, 0.03, z), root)
    T.candle(kit, mats, root, "stub", (-0.05, 0.03, z + 0.006), h=0.05, r=0.014, lit=False)
    kit.box("prayer_book", (0.1, 0.14, 0.03), (0.06, -0.03, z + 0.015), (0, 0, 28), mats["clay"], bevel=0.004, parent=root)
    kit.box("prayer_pages", (0.092, 0.128, 0.022), (0.062, -0.03, z + 0.015), (0, 0, 28), mats["parchment"], parent=root)
    _kitchen.lathe(kit, "water_cup", [(0.0, 0.0), (0.03, 0.0), (0.038, 0.07), (0.04, 0.075), (0.036, 0.075), (0.0, 0.01)], 14,
                   mats["pewter"], (0.06, 0.1, z), root)
    return root

"""A niche in the back wall of the commander's chamber with a small carved saint and an oil lamp that is never let go out.

The niche is 0.36 m wide, 0.52 m high and 0.3 m deep, cut into the wall block with a dressed case around it and a sill
shelf; its floor is 1.45 m over the room's. Origin: the middle of the niche on the wall's inner face at floor level. The saint is
a robed oak figure 0.26 m high, rubbed pale and smooth by thumbs, with a halo ring. The lamp is a clay dish with a wick: a
tiny flame and a tiny warm light, the only one that never changes. Hung beside the case: a string of wooden beads.
"""

from . import _fire, _kitchen, _lights
from . import _tower as T

LIGHTS = []
BLOCK = "block_back_wall_w"
W, H, DEPTH, Z0 = 0.36, 0.52, 0.3, 1.45


def build(kit, mats, rng):
    root = kit.group("tower_shrine")
    dressed = T.dressed(mats)
    import bpy
    block = bpy.data.objects.get(BLOCK)
    cutter = kit.box("cut_niche", (W, DEPTH + 0.05, H), (0, (DEPTH - 0.05) / 2 + 0.0, Z0 + H / 2), parent=root)
    if block is not None:
        mod = block.modifiers.new("niche", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter
        cutter.hide_render = True
        cutter.display_type = "WIRE"
    # case and sill
    for n, s in enumerate((-1, 1)):
        kit.box(f"niche_jamb_{n}", (0.07, 0.1, H + 0.06), (s * (W / 2 + 0.035), -0.04, Z0 + H / 2), mat=dressed, bevel=0.008, parent=root)
    kit.box("niche_head", (W + 0.2, 0.1, 0.08), (0, -0.04, Z0 + H + 0.04), mat=dressed, bevel=0.008, parent=root)
    kit.box("niche_sill", (W + 0.16, 0.16, 0.05), (0, -0.07, Z0 - 0.025), mat=dressed, bevel=0.008, parent=root)
    kit.box("niche_back", (W, 0.02, H), (0, DEPTH - 0.03, Z0 + H / 2), mat=mats["wood_dark"], parent=root)
    # the saint
    sx, sy, sz = -0.04, 0.15, Z0
    _kitchen.lathe(kit, "saint_robe", [(0.0, 0.0), (0.06, 0.0), (0.066, 0.03), (0.05, 0.12), (0.045, 0.17), (0.03, 0.2), (0.0, 0.2)],
                   14, mats["scrubbed"], (sx, sy, sz), root)
    kit.sphere("saint_head", 0.032, (sx, sy, sz + 0.235), mat=mats["scrubbed"], segments=10, parent=root)
    kit.torus("saint_halo", 0.04, 0.003, (sx, sy - 0.012, sz + 0.24), (80, 0, 0), mats["pewter"], major_segments=16, minor_segments=4,
              parent=root)
    kit.box("saint_arms", (0.1, 0.03, 0.04), (sx, sy - 0.04, sz + 0.14), (0, 0, 0), mats["scrubbed"], bevel=0.01, parent=root)
    # the oil lamp: a clay dish with a wick and a small flame
    lx, ly = 0.1, 0.1
    _kitchen.lathe(kit, "lamp_dish", [(0.0, 0.0), (0.035, 0.0), (0.045, 0.02), (0.04, 0.025), (0.0, 0.012)], 12, mats["clay"],
                   (lx, ly, Z0), root)
    kit.cylinder("lamp_wick", 0.003, 0.014, (lx, ly, Z0 + 0.02), mat=mats["iron"], segments=4, parent=root)
    _fire.flame(kit, mats["fire"], root, "lamp_flame", (lx, ly, Z0 + 0.028), 0.035, 0.0065, lean=(0.0, 0.0), twist=0.6, phase=1.1,
                rings=10, sides=6)
    _lights.add(root, "tower_shrine", pos=(lx, ly - 0.02, Z0 + 0.07), color=T.WARM, watts=3.0, radius=0.02, specular=0.3, reach=1.6)
    # prayer beads on a nail
    kit.cylinder("bead_nail", 0.004, 0.03, (0.3, -0.02, Z0 + H - 0.05), (90, 0, 0), mats["iron"], segments=6, parent=root)
    for k in range(9):
        kit.sphere(f"bead_{k}", 0.0075, (0.3, -0.03, Z0 + H - 0.065 - 0.016 * k), mat=mats["wood_dark"], segments=6, parent=root)
    return root

"""The doorway between the kitchen and the larder: dressed stone jambs, a worn threshold, an iron hook for the door that is gone.

Origin: the middle of the opening on the kitchen's face of the partition at floor level; the partition is
the XZ plane at y = 0 of the prop frame and lies toward +Y (place it with rot_z = -90 on the wall at
x = 3.0). The opening is 1.1 m wide and 2.15 m high; the blocks `partition_s`, `partition_n` and
`partition_lintel` of plan.json leave it open, so the proxy geometry has the gap too.
"""

from . import _lights

LIGHTS = []
W, H = 1.1, 2.15
SPILL = dict(pos=(0.0, 0.9, 1.3), color=(1.0, 0.45, 0.14), watts=9.0, radius=0.3, specular=0.0, reach=3.2)


def build(kit, mats, rng):
    root = kit.group("kitchen_archway")
    # the glow of the kitchen floor that reaches into the larder through the doorway (an indirect bounce, not a flame)
    _lights.add(root, "kitchen_archway", **SPILL)
    from .gate_door import _dressed
    dressed = _dressed(mats["stone_wall"])
    for s in (-1, 1):
        kit.box(f"arch_jamb_{s}", (0.18, 0.14, H + 0.02), (s * (W / 2 + 0.07), -0.05, H / 2 + 0.01), mat=dressed, bevel=0.012,
                parent=root)
    kit.box("arch_lintel", (W + 0.44, 0.16, 0.2), (0, -0.06, H + 0.07), mat=dressed, bevel=0.014, parent=root)
    kit.box("arch_threshold", (W + 0.1, 0.9, 0.04), (0, 0.4, -0.019), mat=dressed, bevel=0.01, parent=root)
    kit.box("arch_hook", (0.03, 0.14, 0.03), (-W / 2 - 0.02, -0.06, 1.2), mat=mats["iron"], parent=root)
    return root

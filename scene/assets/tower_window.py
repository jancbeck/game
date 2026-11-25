"""The paired window of the commander's chamber, in the back (cliff side) wall: a deep embrasure, shutters half open.

Origin: the middle of the opening on the wall's inner face at floor level; the wall (0.75 m thick) lies
toward +Y and the room toward -Y. A narrow throat of 0.28 m on the outer face carries two lights of 0.34 m
and a stone mullion; the reveals splay out to 1.3 m on the inside, with a timber lintel over them. The
window is open: no glass, a pair of shutter leaves folded back flat into the reveals. Rain blows in on the sill
and the boards below it, so a dark film of water lies there. A cool point light stands in the splay, 0.3 m into the wall, far enough from the jambs not to burn a patch into them: dusk
coming in. Beyond the opening there is only the valley, 9 m down (apron of plan.json).
"""

from . import _tower as T

LIGHTS = []
BLOCK = "block_back_wall_w"
WALL = 0.75


def build(kit, mats, rng):
    root = kit.group("tower_window")
    T.window(kit, mats, root, BLOCK, WALL, z1=2.45, head_rise=0.25, throat=0.28, leaves=(-60.0, -60.0), light_watts=24.0,
             light_y=0.3, name="tower_window")
    # rain on the boards under the sill, a darker film on the inner sill
    kit.sphere("sill_wet", 1.0, (0.0, 0.42, 0.93), scale=(0.5, 0.26, 0.004), mat=mats["water_film"], segments=12, parent=root)
    kit.sphere("floor_wet", 1.0, (0.1, -0.35, 0.003), scale=(0.62, 0.33, 0.004), mat=mats["water"], segments=14, parent=root)
    kit.sphere("floor_wet_b", 1.0, (-0.3, -0.65, 0.003), scale=(0.22, 0.14, 0.004), mat=mats["water"], segments=10,
               parent=root)
    return root

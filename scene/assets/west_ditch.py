"""West ditch: the wet, overgrown approach outside the west curtain wall.

A shallow defensive ditch of still dark water runs parallel to the wall, 2.4 to 4.5 m out, ending in a
shallow pool at both ends. Between wall and ditch lies a muddy track with two wheel ruts, long puddles in
the ruts and a gully that carries the trickle of a stone drain spout across it. The ditch's spoil is banked
on the far side. Bracken, bramble thickets, nettle stalks, grass, rushes and bulrushes crowd the wall foot
and both banks. Stones have fallen from the wall (two merlons among them), a post-and-rail fence stands
broken on the inner bank, sharpened stakes lean out of the outer bank, and a windfall log, broken boards and
sticks lie about. A lantern on a post at the fence line lights the wet track and shows in the water.

The wall is dressed on both faces: the retaining wall below the cobble ledge (damp, algae, ivy, streaks,
the drain spout) and the 7 m curtain face above it (rain streaks from the crenels, stone spouts under the
parapet, ivy, damp at the ledge). Silt and weeds lie on the
ledge. Ground fog thickens westward and a low mist lies on the water.

Parts, each in its own helper:

- `_ditch_field`   layout lines and the ground height field `ground(x, y)`; the plan's trees and bushes
                   read their heights from it;
- `_ditch_ground`  the mud skin, the wet-mud film, the ditch pool, track puddles, the rill, water material;
- `_ditch_plants`  the undergrowth;
- `_ditch_works`   fallen stones, fence, stakes, lantern post, litter;
- `_ditch_wall`    the dressing of both wall faces, the ledge and the drain spout;
- `_ditch_fog`     ground fog and mist.

Placement: the heights are those of the terrain the lower ward gets in build_scene.py, so the prop root
must stand where `_ditch_field.ORIGIN` says, on the lower ward, unrotated and unscaled:

    "west_ditch": {"pos": [-13.0, 0.0], "z": "lower_ward", "rot_z": 0}

The mud skin lies 1.2 to 3.5 cm above the terrain, which it hides between x = -24 and the wall and
y = -17 and 15. To keep a plan entry on the skin, give it `"z": ground(x, y)` from `_ditch_field`.

`PATROL_LANTERN = False` leaves out the lantern and its light.
"""

from . import _ditch_fog
from . import _ditch_ground as G
from . import _ditch_plants
from . import _ditch_wall
from . import _ditch_works
from . import lantern, lantern_standing

PATROL_LANTERN = False   # a lantern on a post at the fence line: a warm light pool on the wet track and in the water
LANTERN_WATTS = 130.0
LIGHTS = []              # filled in by build() when the lantern is on; the root-relative point light of its flame


def build(kit, mats, rng):
    global LIGHTS
    root = kit.group("west_ditch")
    G.build_ground(kit, mats, root)
    G.build_wet_mud(kit, root)
    G.build_pool(kit, root)
    G.build_puddles(kit, root)
    G.build_rill(kit, root)
    _ditch_plants.build(mats, root)
    if PATROL_LANTERN:
        top = _ditch_works.lantern_post(kit, mats, rng, root)
        lamp = lantern_standing.build(kit, mats, rng)
        lamp.parent = root
        lamp.location = top
        LIGHTS = [((top.x, top.y, top.z + lantern.FLAME_Z), lantern.COLOR, LANTERN_WATTS)]
    _ditch_works.stones(kit, mats, rng, root)
    _ditch_works.fence(kit, mats, rng, root)
    _ditch_works.stakes(kit, mats, rng, root)
    _ditch_works.litter(kit, mats, rng, root)
    _ditch_wall.damp(kit, rng, root)
    _ditch_wall.streaks(kit, rng, root)
    _ditch_wall.algae(kit, mats, rng, root)
    _ditch_wall.ivy(kit, mats, rng, root)
    _ditch_wall.ledge_cover(kit, root)
    _ditch_wall.ledge_weeds(kit, mats, rng, root)
    _ditch_wall.upper_damp(kit, rng, root)
    _ditch_wall.upper_streaks(kit, rng, root)
    _ditch_wall.upper_ivy(kit, mats, rng, root)
    _ditch_wall.wall_spouts(kit, mats, rng, root)
    _ditch_wall.spout(kit, mats, rng, root)
    _ditch_fog.build(kit, root)
    return root

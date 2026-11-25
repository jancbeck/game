"""Garrison cookhouse: a timber lean-to against the north-west tower, with a hearth and a bread oven.

Footprint 4.45 m wide (X) and 4.3 m deep (Y), built at full size, so place it at scale 1.
The back (+Y) stands against the NW tower (and, east of x = 0.075, the gatehouse); the left (-X)
against the open flank of the wall stair, whose masonry rises from about 3.2 m at the front to the
6 m landing at the tower face. The roof's left edge is let in under a flashing board along that
flank. The front is open: two heavy
posts on stone pads carry a bowed header, with a patched-in third post and knee braces. The roof
is staggered split shingles on open battens, sagging between header and wall, darker and wetter
along the eave and the stair. The right side is closed by a board wall.

Fires: a beehive bread oven in the front bay with its mouth toward the courtyard, and at the back
an open hearth under a stone hood, against the tower. The hood feeds a stone stack that climbs
the tower face (all of it west of the tower's corner) through the roof to 7.25 m. Its crown is a
dark, sooty flue with smoke and a faint ember glow deep down.

Left of the hearth a low store door in a dressed-stone surround leads into the tower; a strip
along the stair's flank stays clear as the way to it. Provisions hang from the header and from a
pole across the room, a metre in front of the hearth: in its smoke, away from its flame. A work
table, shelves, barrels, sacks, a chopping block and firewood ricks fill the rest, with one rick
in the front-right bay. A gutter under the front eave spills into a water butt at the front-right
corner; two more ricks stand outside the right wall under its overhang.
"""

from . import _lights
from . import _shed_geo as geo
from . import _shed_hearth as hearth
from . import _shed_props as props
from . import _shed_roof as roof
from . import _shed_store as store

# The hearth's warm light, root-relative. It is the only light: the scene's shadow budget has no
# room for more, so the oven mouth glows by emission. It stands 0.7 m from the tower wall and is
# placed through _lights, with a low specular, so the wet stone does not mirror it (see _lights.py).
LIGHTS = []
HEARTH_LIGHT = dict(pos=(hearth.HEARTH_X, 1.45, 0.95), color=(1.0, 0.34, 0.06), watts=220.0, radius=0.2, specular=0.25,
                    reach=9.0)


def _pad(kit, mats, rng, root, name, x, y, s=0.5):
    sx, sy = s * rng.uniform(0.9, 1.15), s * rng.uniform(0.9, 1.15)
    kit.box(name, (sx, sy, 0.2), (x, y, 0.04), (rng.uniform(-1.5, 1.5), rng.uniform(-1.5, 1.5), rng.uniform(-12, 12)),
            mats["stone_wall"], bevel=0.035, parent=root)


def _post(kit, mats, rng, root, name, x, y, top_z, section=0.19, mat=None, lean=0.012):
    kit.beam(name, (x, y, 0.1), (x + rng.uniform(-lean, lean), y + rng.uniform(-lean, lean), top_z),
             (section, section), mat or mats["wood_dark"], bevel=0.015, parent=root)


def _frame(kit, mats, rng, root):
    wd, wo, iron = mats["wood_dark"], mats["wood_old"], mats["iron"]
    Y_P = roof.Y_P

    def header_bottom(x):
        return roof.surface(x, Y_P) - roof.UNDER - roof.HEADER_H

    # front posts on stone pads, a patched-in third post, and the right side's own posts
    for n, x in enumerate((-1.95, 2.0)):
        _pad(kit, mats, rng, root, f"pad_front_{n}", x, Y_P)
        _post(kit, mats, rng, root, f"front_post_{n}", x, Y_P, header_bottom(x) + 0.03, 0.2, wd)
    _pad(kit, mats, rng, root, "pad_prop", -0.5, Y_P, 0.36)
    _post(kit, mats, rng, root, "prop_post", -0.5, Y_P, header_bottom(-0.5) + 0.02, 0.13, wo, lean=0.02)
    kit.box("prop_post_wedge", (0.07, 0.07, 0.1), (-0.5, Y_P, header_bottom(-0.5) - 0.04), (0, 0, 20), wo, parent=root)

    # braces: left one across the front bay, right one in the side plane
    kit.beam("brace_left", (-1.95, Y_P, 1.72), (-1.1, Y_P, header_bottom(-1.1) + 0.05), (0.1, 0.1), wd, bevel=0.01,
             parent=root)
    kit.beam("brace_right", (2.0, Y_P, 1.72), (2.0, Y_P + 0.85, roof.surface(2.0, Y_P + 0.85) - roof.UNDER - 0.02),
             (0.1, 0.1), wd, bevel=0.01, parent=root)
    for n, (x, y) in enumerate(((-1.95, Y_P), (2.0, Y_P))):
        kit.box(f"post_strap_{n}", (0.2, 0.2, 0.05), (x, y, header_bottom(x) - 0.08), mat=iron, bevel=0.004, parent=root)

    # right side posts and rails
    for n, y in enumerate((0.1, 1.95)):
        _pad(kit, mats, rng, root, f"pad_side_{n}", 2.0, y, 0.45)
        top = roof.surface(2.0, y) - roof.UNDER - 0.02
        _post(kit, mats, rng, root, f"side_post_{n}", 2.0, y, top, 0.17, wd)
    for n, z in enumerate((0.5, 1.35)):
        kit.box(f"side_rail_{n}", (0.08, 2.9, 0.1), (1.99, 0.55, z), (0, 0, rng.uniform(-0.4, 0.4)), wd, bevel=0.008,
                parent=root)

    # tie beam from the header to the tower side
    kit.beam("tie_beam", (-1.95, Y_P, header_bottom(-1.95) + 0.1), (-1.95, Y_P + 2.0, header_bottom(-1.95) + 0.3),
             (0.1, 0.12), wd, bevel=0.008, parent=root)


def _side_wall(kit, mats, rng, root):
    """Upright boards on the right side and the back corner, a few gone or rotted short."""
    wo, wd = mats["wood_old"], mats["wood_dark"]

    def build_run(coords, name, along_y):
        y = coords[0]
        n = 0
        while y < coords[1] - 0.1:
            w = rng.uniform(0.17, 0.25)
            gap = rng.uniform(0.01, 0.03)
            lo, hi = y, min(y + w, coords[1])
            y += w + gap
            n += 1
            if n in (5, 14):
                continue    # missing
            yc = (lo + hi) / 2
            if along_y:
                top_full = roof.surface(2.1, yc) - roof.UNDER - 0.04
            else:
                top_full = roof.surface(yc, 2.0) - roof.UNDER - 0.04
            short = n in (3, 11)
            h = top_full * (rng.uniform(0.5, 0.8) if short else rng.uniform(0.95, 1.0))
            slant = rng.uniform(0.08, 0.25) if short else rng.uniform(-0.02, 0.02)
            lean = rng.uniform(-0.02, 0.03)
            t = 0.032
            if along_y:
                x0, x1 = 2.095, 2.095 + t
                m = geo.Mesh()
                bot = [(x0, lo, 0.0), (x1, lo, 0.0), (x1, hi, 0.0), (x0, hi, 0.0)]
                top = [(x0 + lean, lo, h), (x1 + lean, lo, h), (x1 + lean, hi, h - slant), (x0 + lean, hi, h - slant)]
            else:
                m = geo.Mesh()
                x_lo, x_hi = lo, hi
                y0, y1 = 2.05 - t, 2.05
                bot = [(x_lo, y0, 0.0), (x_hi, y0, 0.0), (x_hi, y1, 0.0), (x_lo, y1, 0.0)]
                top = [(x_lo, y0 + lean, h), (x_hi, y0 + lean, h - slant), (x_hi, y1 + lean, h - slant),
                       (x_lo, y1 + lean, h)]
            m.prism(bot, top)
            m.finish(f"{name}_{n}", wo if rng.random() < 0.7 else wd, root, bevel=0.005)

    build_run((-0.9, 2.04), "side_board", True)
    build_run((1.4, 2.08), "back_board", False)


def build(kit, mats, rng):
    root = kit.group("shed")
    _lights.add(root, "shed", **HEARTH_LIGHT)
    roof.frame(kit, mats, rng, root)
    roof.shingles(kit, mats, rng, root)
    roof.stack_flashing(kit, mats, rng, root)
    _frame(kit, mats, rng, root)
    _side_wall(kit, mats, rng, root)
    hearth.hearth(kit, mats, rng, root)
    hearth.stack(kit, mats, rng, root)
    hearth.smoke_and_sparks(kit, mats, rng, root)
    hearth.oven(kit, mats, rng, root)
    props.front_provisions(kit, mats, rng, root)
    props.work_table(kit, mats, rng, root)
    props.front_table(kit, mats, rng, root)
    props.wall_shelves(kit, mats, rng, root)
    props.east_rack(kit, mats, rng, root)
    props.log_rick(kit, mats, rng, root, "rick_inside", 1.78, -0.55, 0.5, 3, 7)
    props.log_rick(kit, mats, rng, root, "rick_inside_back", 1.78, -0.05, 0.5, 3, 7)
    props.log_rick(kit, mats, rng, root, "rick_bay", 1.55, -1.8, 0.55, 4, 8)
    props.log_rick(kit, mats, rng, root, "rick_outside", 2.4, -0.8, 0.5, 3, 7)
    props.log_rick(kit, mats, rng, root, "rick_outside_back", 2.4, -0.3, 0.5, 3, 7)
    props.chopping_block(kit, mats, rng, root)
    props.barrel(kit, mats, root, "water_barrel", 1.68, 1.75)
    props.barrel(kit, mats, root, "flour_barrel", 1.08, 1.8, h=0.7, r=0.26)
    props.bucket(kit, mats, root, "bucket_a", 0.45, 1.85)
    props.sack(kit, mats, root, "sack_a", (0.95, -1.25, 0.0), rot_z=-20, s=0.85)
    props.sack(kit, mats, root, "sack_b", (1.0, -1.65, 0.0), rot_z=30, s=0.75)
    props.stool(kit, mats, rng, root, "stool", -1.0, 0.0)
    store.store_door(kit, mats, rng, root)
    store.water_butt(kit, mats, rng, root)
    props.litter(kit, mats, rng, root)
    return root

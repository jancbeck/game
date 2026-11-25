"""Shared weathering recipe: node helpers plus the wood shader behind wood_old, wood_dark and door_wood.

Rain is falling, so every material built on this file shares one idea of "wet":

- Soak: wood out in the rain is darker, browner and more saturated than dry wood. Wood under a
  roof or the gate vault stays drier. "Under cover" is read from the same boxes that stop rain
  streaks (`rain.sheltered` in layout.json) plus the small roof of the well (plan.json), so
  there is one definition of shelter.
- Ground wetness: world height near the floor, with a ragged top edge (splash line).
- Rain runoff: vertical streaks in world space, so they run down on every part, rotated or not.
- Film on top: up-facing surfaces carry a glossy film of water (a clear coat), nearly closed in
  the open and broken up where the wood is covered.

Large tone changes carry the look: board-to-board colour, wet/dry bands, grime that gathers in
corners through ambient occlusion. Every board differs in tone, in how far it has silvered, and in
the offset and stretch of its scanned texture. The board's random
value is the object's own, or, on a merged mesh, the `piece` face attribute that
assets/_se_mesh.py and assets/_shed_geo.py write per connected piece. Near the floor the boards
are soaked darker and carry mud and a green film of algae. The surface itself is a
scanned texture set (see _scan.py): its luminance sets the position on each material's colour
ramp, so cracks and fibres are real while the palette stays art-directed; its normal map and
height give the relief, its height also decides where water stands (cracks) and where raised
fibres break through the film.

Wood grain axis. Boards, posts and beams point along different local axes, so one fixed
grain axis would be wrong on some parts. The box size per axis is read from the coordinates:

- Generated coordinates run 0..1 over the object's bounding box and Object
  coordinates are meters, so |object| / |generated - 0.5| is the box size on each
  axis (clamped so the centre lines stay finite).
- `_scan.wood` turns the scan's grain along the longer in-plane edge of every face.
- On a merged mesh the `piece_size` face attribute gives each piece's own size instead, so a
  shingle carries its grain down the slope although the whole course is long along the eave.

The same size estimate gives the distance to each face, which drives worn, lighter
edges (`edge_amount` above zero). Merged meshes share one bounding box, so there the
grain follows the longest edge of the whole mesh and the edge wear sits on the outer corners only.
"""

import bpy

import _scan
import location

# half extents (x, y, z) of the small roofs that are not in layout.json
_SMALL_ROOFS = {"well": (1.25, 1.0, 2.0)}
# the roofs themselves are in the rain: boxes under a lean-to are cut off below the eaves
# (the lowest is the stable's, at 2.2 m); a box taller than a lean-to is a vault and keeps its height
UNDER_EAVE = 2.1
VAULT_HEIGHT = 4.0


# ---- node helpers ---------------------------------------------------------------------------

def vm(nt, op, *args):
    n = nt.nodes.new("ShaderNodeVectorMath")
    n.operation = op
    for i, a in enumerate(args):
        if a is None:
            continue
        if isinstance(a, bpy.types.NodeSocket):
            nt.links.new(a, n.inputs[i])
        else:
            n.inputs[i].default_value = tuple(a) if isinstance(a, (tuple, list)) else (a, a, a)
    return n


def math(nt, op, a, b=None, c=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b, c)):
        if v is None:
            continue
        if isinstance(v, bpy.types.NodeSocket):
            nt.links.new(v, n.inputs[i])
        else:
            n.inputs[i].default_value = v
    return n.outputs[0]


def map_range(nt, value, lo, hi, to_lo=0.0, to_hi=1.0):
    m = nt.nodes.new("ShaderNodeMapRange")
    m.inputs["From Min"].default_value = lo
    m.inputs["From Max"].default_value = hi
    m.inputs["To Min"].default_value = to_lo
    m.inputs["To Max"].default_value = to_hi
    nt.links.new(value, m.inputs["Value"])
    return m.outputs["Result"]


def mix_color(nt, fac, a, b, blend="MIX"):
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    m.blend_type = blend
    for idx, v in ((0, fac), (6, a), (7, b)):
        if isinstance(v, bpy.types.NodeSocket):
            nt.links.new(v, m.inputs[idx])
        elif idx == 0:
            m.inputs[idx].default_value = v
        else:
            m.inputs[idx].default_value = (*v, 1.0)
    return m.outputs[2]


def lerp(nt, fac, a, b):
    """Float blend: a where fac = 0, b where fac = 1. a and b may be numbers or sockets."""
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "FLOAT"
    for idx, v in ((0, fac), (2, a), (3, b)):
        if isinstance(v, bpy.types.NodeSocket):
            nt.links.new(v, m.inputs[idx])
        else:
            m.inputs[idx].default_value = v
    return m.outputs[0]


def noise(nt, vec, scale, detail, roughness=0.55, w=None):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.noise_dimensions = "4D" if w is not None else "3D"
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = roughness
    nt.links.new(vec, n.inputs["Vector"])
    if w is not None:
        nt.links.new(w, n.inputs["W"])
    return n.outputs["Fac"]


def ramp(nt, fac, stops):
    """Colour ramp from (position, rgb) stops."""
    r = nt.nodes.new("ShaderNodeValToRGB")
    while len(r.color_ramp.elements) < len(stops):
        r.color_ramp.elements.new(1.0)
    for el, (pos, col) in zip(r.color_ramp.elements, stops):
        el.position = pos
        el.color = (*col, 1.0)
    nt.links.new(fac, r.inputs["Fac"])
    return r.outputs["Color"]


def sep(nt, vec):
    n = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(vec, n.inputs[0])
    return n.outputs[0], n.outputs[1], n.outputs[2]


def combine(nt, x, y, z):
    n = nt.nodes.new("ShaderNodeCombineXYZ")
    for i, v in enumerate((x, y, z)):
        if isinstance(v, bpy.types.NodeSocket):
            nt.links.new(v, n.inputs[i])
        else:
            n.inputs[i].default_value = v
    return n.outputs[0]


def piece_random(nt):
    """Per-board random 0..1: the object's random value, shifted by the `piece` face attribute on
    merged meshes. Returns (random, piece size vector or None-like zero vector socket)."""
    info = nt.nodes.new("ShaderNodeObjectInfo")
    pa = nt.nodes.new("ShaderNodeAttribute")
    pa.attribute_type = "GEOMETRY"
    pa.attribute_name = "piece"
    ps = nt.nodes.new("ShaderNodeAttribute")
    ps.attribute_type = "GEOMETRY"
    ps.attribute_name = "piece_size"
    rnd = math(nt, "FRACT", math(nt, "MULTIPLY_ADD", pa.outputs["Fac"], 0.7548, info.outputs["Random"]))
    return rnd, ps.outputs["Vector"]


def seed_of(nt, mult=40.0):
    """Per-object random number scaled for use as a 4D noise W offset."""
    info = nt.nodes.new("ShaderNodeObjectInfo")
    return math(nt, "MULTIPLY", info.outputs["Random"], mult), info.outputs["Random"]


def world(nt):
    """World-space position and normal."""
    g = nt.nodes.new("ShaderNodeNewGeometry")
    return g.outputs["Position"], g.outputs["Normal"]


def occlusion(nt, distance=0.15):
    """0 deep in corners, 1 in the open."""
    n = nt.nodes.new("ShaderNodeAmbientOcclusion")
    n.inputs["Distance"].default_value = distance
    return n.outputs["AO"]


def darken(nt, color, amount, tint=(0.0, 0.0, 0.0)):
    """Colour times `tint`, applied with strength `amount` (0..1)."""
    return mix_color(nt, amount, color, tint, "MULTIPLY")


def rain_wetness(nt, wpos, wnrm, seed, ground=0.7, streaks=0.5, film=0.6, patch_range=(0.40, 0.58)):
    """Wet mask 0..1 from splash height, runoff streaks and the film on up-facing surfaces.

    `patch_range` is where the noise that breaks the film into patches turns it on: lower numbers
    close the film.

    Returns (wet, film_mask, splash): `wet` darkens and glosses, `film_mask` is the up-facing part
    alone, `splash` is the soaked zone near the floor alone.
    """
    wx, wy, wz = sep(nt, wpos)
    # splash zone: soaked near the floor, ragged top edge
    ragged = noise(nt, wpos, 3.0, 4.0, 0.6)
    top = math(nt, "MULTIPLY_ADD", ragged, ground * 1.1, ground * 0.3)
    near_floor = map_range(nt, math(nt, "DIVIDE", wz, top), 0.0, 1.0, 1.0, 0.0)
    # runoff: noise squeezed along world Z reads as vertical streaks on any part
    squeezed = vm(nt, "MULTIPLY", wpos, (7.0, 7.0, 0.9))
    runoff = map_range(nt, noise(nt, squeezed.outputs[0], 1.0, 3.0, 0.55, seed), 0.45, 0.68, 0.0, streaks)
    # film: up-facing surfaces, patchy
    _, _, nz = sep(nt, wnrm)
    facing_up = map_range(nt, nz, 0.55, 0.95)
    patch = map_range(nt, noise(nt, wpos, 2.2, 3.0, 0.6, seed), *patch_range)
    film_mask = math(nt, "MULTIPLY", facing_up, math(nt, "MULTIPLY", patch, film))
    wet = math(nt, "MAXIMUM", math(nt, "MAXIMUM", near_floor, runoff), film_mask)
    return wet, film_mask, near_floor


# ---- shelter --------------------------------------------------------------------------------

def shelters():
    """Boxes ((x0, x1), (y0, y1), (z0, z1)) in world meters where rain does not fall."""
    boxes = []
    try:
        for b in location.load("layout.json")["rain"]["sheltered"]:
            (x0, x1), (y0, y1), (z0, z1) = b
            boxes.append(((x0, x1), (y0, y1), (z0, z1 if z1 > VAULT_HEIGHT else min(z1, UNDER_EAVE))))
    except (OSError, KeyError, ValueError):
        pass
    try:
        props = location.plan()["props"]
        for key, p in props.items():
            half = _SMALL_ROOFS.get(key.split("#")[0])
            if half and not key.startswith("_"):
                x, y = p["pos"]
                boxes.append(((x - half[0], x + half[0]), (y - half[1], y + half[1]), (-1.0, half[2])))
    except (OSError, KeyError, ValueError):
        pass
    return boxes


def cover(nt, wpos, edge=0.15):
    """0 in the open, 1 under a roof (soft edges of `edge` meters), from the world position."""
    wx, wy, wz = sep(nt, wpos)
    total = None
    for box in shelters():
        inside = None
        for v, (lo, hi) in zip((wx, wy, wz), box):
            term = math(nt, "MULTIPLY", map_range(nt, v, lo - edge, lo + edge), map_range(nt, v, hi + edge, hi - edge))
            inside = term if inside is None else math(nt, "MULTIPLY", inside, term)
        total = inside if total is None else math(nt, "MAXIMUM", total, inside)
    return total if total is not None else 0.0


def hue_sat(nt, color, fac, sat, val):
    """Colour with saturation and value scaled by (sat, val), applied with strength `fac`."""
    n = nt.nodes.new("ShaderNodeHueSaturation")
    n.inputs["Saturation"].default_value = sat
    n.inputs["Value"].default_value = val
    if isinstance(fac, bpy.types.NodeSocket):
        nt.links.new(fac, n.inputs["Fac"])
    else:
        n.inputs["Fac"].default_value = fac
    nt.links.new(color, n.inputs["Color"])
    return n.outputs["Color"]


# ---- wood -----------------------------------------------------------------------------------

def grain_axes(nt, along, across):
    """Long-axis detection (see module docstring).

    Returns (size, half, in_plane, stretched): per-axis box size, half-extent fraction, the axes in
    the face plane, and Object coordinates scaled by `along` on the long axis and `across` elsewhere.
    """
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj, gen, nrm = tc.outputs["Object"], tc.outputs["Generated"], tc.outputs["Normal"]
    half = vm(nt, "MAXIMUM", vm(nt, "ABSOLUTE", vm(nt, "SUBTRACT", gen, 0.5).outputs[0]).outputs[0], 0.004)
    size = vm(nt, "DIVIDE", vm(nt, "ABSOLUTE", obj).outputs[0], half.outputs[0])
    in_plane = vm(nt, "MAXIMUM",
                  vm(nt, "MULTIPLY_ADD", vm(nt, "ABSOLUTE", nrm).outputs[0], -1.6,
                     (1.0, 1.0, 0.85)).outputs[0], 0.0)
    score = vm(nt, "POWER", vm(nt, "MULTIPLY", size.outputs[0], in_plane.outputs[0]).outputs[0], 3.0)
    total = vm(nt, "DOT_PRODUCT", score.outputs[0], (1.0, 1.0, 1.0))
    weight = vm(nt, "DIVIDE", score.outputs[0], total.outputs["Value"])
    freq = vm(nt, "MULTIPLY_ADD", weight.outputs[0], -(across - along), across)
    stretched = vm(nt, "MULTIPLY", obj, freq.outputs[0])
    return size, half, in_plane, stretched.outputs[0]


def build(nt, bsdf, *, dark, light, rough, bump, edge=(0.0, 0.0, 0.0), edge_amount=0.0,
          blotch=2.2, edge_width=0.03, tone_var=0.45,
          wet_tint=(0.38, 0.32, 0.27), wet_rough=0.38, ground=0.7, streaks=0.5, film=0.6,
          grime=0.55, mud_amount=0.6, roof=0.0, roof_moss=0.0, bleed_z=(), lichen=None, lichen_color=(0.17, 0.19, 0.13),
          soak=0.8, soak_sat=1.4, soak_val=0.62, dry=0.6, coat=0.9, film_patch=(0.22, 0.42), film_rough=0.07,
          scan="rough_wood", tile=(0.5, 1.0), lum_range=(0.06, 0.21), grain_mix=0.8, normal=1.6,
          silver=0.35, foot_algae=0.5):
    """Soaked, weathered wood.

    dark/light: colour at the two ends of the grain ramp (dry, silvered). rough: (rough, smooth)
    roughness at the ends of the ramp. tone_var: plank-to-plank tone range. wet_tint multiplies the
    colour where wet. ground/streaks/film: splash height (m), runoff strength, top-film strength.
    grime: how strongly occlusion darkens corners. mud_amount: floor-mud splash on the lowest part. roof: how dark, wet and dirty near-horizontal
    up-facing surfaces get (roofs, decks, lids); roof_moss: how much green moss grows on them.
    bleed_z: world heights of the bottom edges of iron straps; rust runs down the wood below each one. lichen: (lo, hi) noise thresholds of pale spots.
    soak: how far wood in the open is pulled from its dry colour toward the soaked one (saturation
    times `soak_sat`, value times `soak_val`, at full strength); dry: how much of the soak the wood
    loses under cover. coat: strength of the clear water film on up-facing surfaces; film_patch: the
    noise range that opens the film (low numbers close it); film_rough: roughness of that film.
    scan: texture set in scene/textures (see _scan.py); tile: meters of one tile across and along
    the grain; lum_range: linear luminance of the scan that maps to the dark and light ends of the
    colour ramp; grain_mix: share of the scan in the ramp position (the rest is the stain noise);
    normal: strength of the scanned normal map. bump: relief depth in meters of the scanned height.
    silver: how far the palest boards are bleached grey by weather (0..1); foot_algae: strength of
    the green-black algae film on the lowest, wettest part of vertical boards.
    """
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    rnd, piece_size = piece_random(nt)
    seed = math(nt, "MULTIPLY", rnd, 40.0)
    rnd2 = math(nt, "FRACT", math(nt, "MULTIPLY_ADD", rnd, 7.13, 0.31))  # a second, independent draw
    size, half, in_plane, _ = grain_axes(nt, 1.0, 1.0)
    # a merged mesh carries each piece's own size: the grain follows the piece, not the whole mesh
    has_piece = math(nt, "GREATER_THAN", vm(nt, "LENGTH", piece_size).outputs["Value"], 1e-4)
    grain_size = nt.nodes.new("ShaderNodeMix")
    grain_size.data_type = "VECTOR"
    nt.links.new(has_piece, grain_size.inputs[0])
    nt.links.new(size.outputs[0], grain_size.inputs[4])
    nt.links.new(piece_size, grain_size.inputs[5])
    # scanned wood, grain turned along each board's long edge; its luminance drives the colour ramp,
    # so cracks and fibres come from the scan and the palette stays the material's own. Each board
    # also stretches the scan a little along its grain, so neighbours do not repeat the same knots.
    rnd3 = math(nt, "FRACT", math(nt, "MULTIPLY_ADD", rnd, 3.71, 0.57))
    sc = _scan.wood(nt, scan, grain_size.outputs[1], tile[0], math(nt, "MULTIPLY_ADD", rnd3, 0.5 * tile[1], 0.8 * tile[1]), rnd)
    grain = map_range(nt, _scan.luminance(nt, sc["diff"]), *lum_range)
    stain = map_range(nt, noise(nt, obj, blotch, 3.0, 0.6, seed), 0.32, 0.68)
    t = lerp(nt, 1.0 - grain_mix, grain, stain)
    # 1 in the cracks and the low grain, 0 on the raised fibres
    crack = map_range(nt, sc["disp"], 0.86, 0.55)
    # each plank gets its own tone
    t = math(nt, "ADD", t, math(nt, "MULTIPLY", math(nt, "SUBTRACT", rnd, 0.5), tone_var), clamp=True)

    base = ramp(nt, t, [(0.0, dark), (1.0, light)])
    # some boards have weathered to a paler, cooler grey, others kept more of their brown
    if silver:
        grey = hue_sat(nt, base, 1.0, 0.45, 1.25)
        base = mix_color(nt, map_range(nt, rnd2, 0.45, 1.0, 0.0, silver), base, grey)

    # worn edges: distance to the nearest in-plane face
    if edge_amount:
        dist = vm(nt, "MULTIPLY", size.outputs[0],
                  vm(nt, "SUBTRACT", (0.5, 0.5, 0.5), half.outputs[0]).outputs[0])
        near = vm(nt, "MAXIMUM",
                  vm(nt, "MULTIPLY_ADD", dist.outputs[0], -1.0 / edge_width, 1.0).outputs[0], 0.0)
        edge_raw = vm(nt, "DOT_PRODUCT", near.outputs[0], in_plane.outputs[0])
        edge_fac = map_range(nt, edge_raw.outputs["Value"], 0.0, 1.0, 0.0, edge_amount)
        base = mix_color(nt, edge_fac, base, edge)

    # lichen: pale ragged spots
    if lichen:
        spots = map_range(nt, noise(nt, obj, 7.0, 5.0, 0.62, seed), *lichen)
        patchy = map_range(nt, noise(nt, obj, 1.3, 2.0, 0.5, seed), 0.45, 0.6)
        base = mix_color(nt, math(nt, "MULTIPLY", spots, patchy), base, lichen_color)

    # rain
    wpos, wnrm = world(nt)
    wet, film_mask, splash = rain_wetness(nt, wpos, wnrm, seed, ground, streaks, film, film_patch)
    shelter = cover(nt, wpos)
    open_air = math(nt, "SUBTRACT", 1.0, math(nt, "MULTIPLY", shelter, dry))   # 1 in the rain, 1 - dry under a roof
    # soaked through: darker, browner and more saturated than the dry wood
    base = hue_sat(nt, base, math(nt, "MULTIPLY", open_air, soak), soak_sat, soak_val)
    if roof:
        # up-facing planes hold water: blotchy dark rot, dirt and moss, always wet
        _, _, nz = sep(nt, wnrm)
        up = map_range(nt, nz, 0.7, 0.93)
        blotch_up = map_range(nt, noise(nt, wpos, 1.6, 4.0, 0.6, seed), 0.35, 0.6, 0.45, 1.0)
        rot = math(nt, "MULTIPLY", up, math(nt, "MULTIPLY", blotch_up, roof))
        base = darken(nt, base, rot, (0.46, 0.43, 0.38))
        dirt = math(nt, "MULTIPLY", up, map_range(nt, noise(nt, wpos, 5.0, 5.0, 0.62, seed), 0.52, 0.66, 0.0, 0.7))
        base = mix_color(nt, math(nt, "MULTIPLY", dirt, roof), base, (0.030, 0.027, 0.022))
        if roof_moss:
            moss = math(nt, "MULTIPLY", map_range(nt, noise(nt, wpos, 4.5, 5.0, 0.62, seed), 0.56, 0.68),
                        map_range(nt, noise(nt, wpos, 0.9, 2.0, 0.5, seed), 0.4, 0.6))
            base = mix_color(nt, math(nt, "MULTIPLY", math(nt, "MULTIPLY", moss, up), roof_moss), base,
                             (0.048, 0.062, 0.028))
        wet = math(nt, "MAXIMUM", wet, math(nt, "MULTIPLY", up, 0.9 * roof))
    # mud thrown up from the floor, then the soaking darkens everything wet
    base = mix_color(nt, math(nt, "MULTIPLY", math(nt, "MULTIPLY", splash, splash), mud_amount), base, (0.042, 0.036, 0.028))
    if foot_algae:
        # a green-black film of algae where the boards stay wet longest, in patches along the foot
        _, _, nz_w = sep(nt, wnrm)
        vertical = map_range(nt, math(nt, "ABSOLUTE", nz_w), 0.6, 0.3)
        patches = map_range(nt, noise(nt, wpos, 2.4, 3.0, 0.6, seed), 0.38, 0.62)
        algae = math(nt, "MULTIPLY", math(nt, "MULTIPLY", splash, vertical), math(nt, "MULTIPLY", patches, foot_algae))
        base = mix_color(nt, algae, base, (0.026, 0.034, 0.018))
    base = darken(nt, base, wet, wet_tint)
    if bleed_z:
        # rust bleed: orange-brown runs that start under each strap and fade out downward
        _, _, wz = sep(nt, wpos)
        runs = map_range(nt, noise(nt, vm(nt, "MULTIPLY", wpos, (16.0, 16.0, 1.6)).outputs[0], 1.0, 3.0, 0.55, seed),
                         0.42, 0.66, 0.15, 1.0)
        bleed = None
        for zb in bleed_z:
            d = math(nt, "SUBTRACT", zb, wz)                      # metres below the strap edge
            below = math(nt, "MULTIPLY", map_range(nt, d, -0.01, 0.0), map_range(nt, d, 0.0, 0.45, 1.0, 0.0))
            bleed = below if bleed is None else math(nt, "MAXIMUM", bleed, below)
        base = mix_color(nt, math(nt, "MULTIPLY", bleed, math(nt, "MULTIPLY", runs, 0.8)), base, (0.140, 0.058, 0.026))

    # grime gathers in corners and joints
    ao = occlusion(nt, 0.12)
    base = darken(nt, base, math(nt, "MULTIPLY", map_range(nt, ao, 0.2, 0.9, 1.0, 0.0), grime),
                  (0.30, 0.28, 0.26))
    nt.links.new(base, bsdf.inputs["Base Color"])

    # dry roughness: the material's range along the ramp, varied by the scanned roughness map
    dry_rough = map_range(nt, t, 0.0, 1.0, rough[1], rough[0])
    dry_rough = math(nt, "MULTIPLY_ADD", math(nt, "SUBTRACT", sc["rough"], 0.5), 1.5, dry_rough)
    dry_rough = math(nt, "ADD", dry_rough, math(nt, "MULTIPLY", crack, 0.06))
    # soaked wood keeps its texture: the roughness drops in proportion, and water stands in the cracks
    soaked_rough = lerp(nt, wet, dry_rough, math(nt, "MULTIPLY", dry_rough, (wet_rough / max(rough)) ** 0.5))
    soaked_rough = lerp(nt, math(nt, "MULTIPLY", math(nt, "MULTIPLY", crack, wet), 0.6), soaked_rough, 0.12)
    # the film is open water over the wood: nearly a mirror in the open, half closed under cover;
    # raised fibres break through it
    film_open = math(nt, "MULTIPLY", film_mask, math(nt, "SUBTRACT", 1.0, math(nt, "MULTIPLY", shelter, 0.7)))
    film_open = math(nt, "MULTIPLY", film_open, map_range(nt, sc["disp"], 0.93, 0.80, 0.3, 1.0))
    # under the film the wood itself stays a soaked, fairly rough surface: the coat is the water,
    # so the scanned grain does not turn into bright specular scratches
    nt.links.new(lerp(nt, film_open, soaked_rough, math(nt, "MINIMUM", soaked_rough, 0.32)), bsdf.inputs["Roughness"])
    # cracks and deep grain see little sky: their reflection is occluded
    nt.links.new(lerp(nt, film_open, map_range(nt, crack, 0.0, 1.0, 0.3, 0.08), 0.25), bsdf.inputs["Specular IOR Level"])
    # clear coat: the water film (IOR 1.33), plus a faint broken sheen on soaked vertical wood
    sheen = math(nt, "MULTIPLY", math(nt, "MULTIPLY", wet, open_air), math(nt, "MULTIPLY_ADD", crack, 0.10 * coat, 0.04 * coat))
    nt.links.new(math(nt, "MAXIMUM", math(nt, "MULTIPLY", film_open, coat), sheen), bsdf.inputs["Coat Weight"])
    nt.links.new(lerp(nt, film_open, 0.22, film_rough), bsdf.inputs["Coat Roughness"])
    bsdf.inputs["Coat IOR"].default_value = 1.33
    # relief: scanned normal map, plus the scanned height as bump on top of it
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = 1.0
    b.inputs["Distance"].default_value = bump
    nt.links.new(sc["disp"], b.inputs["Height"])
    nt.links.new(_scan.to_world_normal(nt, sc["normal"], normal), b.inputs["Normal"])
    nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Metallic"].default_value = 0.0

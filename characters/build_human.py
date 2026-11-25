"""Build one character from characters/<id>/recipe.json: MPFB body, medieval garments, retargeted
CMU animations, and a GLB for the game.

    scripts/make_character.py <id>        # the normal entry point (sets up Blender and MPFB)

Inside Blender: blender --background --factory-startup --python characters/build_human.py -- <recipe.json>

Recipe keys (see characters/hedda, marl, tam, player, commander for whole recipes):

  height_m, macro     the body: MPFB sliders 0..1 (gender 0 woman, 1 man; age 0.5 = 25 years, 1 = 90;
                      weight, muscle, proportions, height, cupsize and firmness for women, race)
  skin                name of an MPFB skin (old_caucasian_female, young_caucasian_male, ...), tint
                      (multiplies the texture), size, floor (the darkest the texture may be, default
                      0.24), despeckle (window radius in pixels, default 3, 0 = off: pulls pores, moles
                      and nostril dots, single black specks at game size, back to the skin), and
                      features painted into the texture:
                      beard, hair (above a hairline and at the temples), brows, flush (cheeks, nose)
  eyes                brown, blue or grey
  garments            each is cut from the body's own surface, so it fits any body:
      skin            forearms: bare forearms below elbow-length sleeves
      tunic, skirt    bodice with sleeves (sleeves "elbow" ends them above the elbow with a rolled cuff),
                      and the skirt lofted from its hem (hem_above_knee or hem_above_ankle; stride_total,
                      thigh_share and side_bias set how it follows the legs; fold_amp and fold_count give it
                      pleats). A slim rest shape is right: the "fit" keys push it out of the legs in a stride
      apron           a bib and skirt panel following the dress, with a waist tie; wear.stain
      hose, boots     leggings; boots of any height (a shoe at 0.09, riding boots at 0.40)
      hood, kerchief  a deep hood; a linen kerchief tied under the chin
      hair            hair as a thin cap with a fringe
      cloak           a shell over the back and shoulders, open in front, with a lofted hem
      jerkin, belt, coif, satchel
      Every garment takes color (sRGB) and wear {dirt, wet, stain}; keys other than these are
      the garment's own, documented at its function in garments.py.
  wear, detail        defaults for wear; Decimate ratio per part
  fit                 free cloth that follows the pose (posefit.py): {"walk": {"mode": "clear", "keys": 30},
                      "sleep": {"mode": "drape"}, "sit": {"mode": "drape", "floor": "seat"}}. A "clear" clip
                      gets one shape key per frame (at most `keys`), which moves the skirt or cloak hem out of
                      the legs; a "drape" clip gets one key that lets the loft fall onto the body, the floor
                      (`floor`: a height in metres, or "seat" for the sitter's own thighs). The game switches
                      the keys on with the clips (game/scripts/player.gd) and <id>.json lists them under "fit".
                      The skirt of a garment (garments.skirt) and the cloak hem are the free cloth.
  animations          one entry per clip, by name (idle, talk and walk are required):
      stand           loops range_s of a CMU clip on the spot (rate < 1 slows it, amplitude < 1 damps
                      its swings about their mean: a drier gesture). A seated clip is a stand clip cut from
                      a sitting stretch (CMU 86_15, seat 0.50 m): the pelvis follows the clip, so the
                      figure sits on a seat of that height (fit.<clip>.seat_height_m in <id>.json)
      walk            cuts one gait cycle at the game's walking speed
      rest            holds one pose of a clip at time t as a lying pose with the chest breathing
                      (period_s, breaths, breath_deg; tweaks {bone: [x, y, z degrees]} turn bones about
                      their own axes); the figure lies on the floor at the origin, head toward head_dir
"""

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector, noise  # noqa: E402

import finish  # noqa: E402
import garments  # noqa: E402
import mpfb_body  # noqa: E402
import posefit  # noqa: E402
import retarget  # noqa: E402

SPEED = 1.75  # m/s, game/scripts/player.gd

BONES = ["Root", "pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "head", "clavicle_l", "upperarm_l",
         "lowerarm_l", "hand_l", "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r", "thigh_l", "calf_l", "foot_l",
         "ball_l", "thigh_r", "calf_r", "foot_r", "ball_r"]


def log(*a):
    print("[build_human]", *a, flush=True)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    recipe_path = Path(argv[0]).resolve()
    options = {a.lstrip("-"): True for a in argv[1:] if a.startswith("--")}
    return recipe_path, options


# ---------------------------------------------------------------- materials

def _shader(mat):
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    return bsdf


def _vertex_colour(mat, bsdf):
    """Base colour = the vertex colour 'Col'. The glTF exporter writes COLOR_0 for a material whose node
    tree does this. It keeps real values for the first material in the mesh that uses the colour and
    writes 1.0 for the others, so the cloth is material slot 0 and is the only user."""
    nt = mat.node_tree
    col = nt.nodes.new("ShaderNodeVertexColor")
    col.layer_name = "Col"
    nt.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])


def image_material(name, image, roughness):
    mat = bpy.data.materials.new(name)
    bsdf = _shader(mat)
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Specular IOR Level"].default_value = 0.35
    return mat


def cloth_material(name, roughness=0.88):
    mat = bpy.data.materials.new(name)
    bsdf = _shader(mat)
    _vertex_colour(mat, bsdf)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Specular IOR Level"].default_value = 0.2
    mat.use_backface_culling = False
    return mat


def box_blur(a, radius):
    """Mean over a (2 radius + 1) square window, edges repeated, of an H x W x C array."""
    k = 2 * radius + 1
    padded = np.pad(a, ((radius, radius), (radius, radius), (0, 0)), mode="edge")
    c = np.cumsum(padded, axis=0)
    c = np.concatenate([np.zeros_like(c[:1]), c], axis=0)
    rows = (c[k:] - c[:-k])
    c = np.cumsum(rows, axis=1)
    c = np.concatenate([np.zeros_like(c[:, :1]), c], axis=1)
    return (c[:, k:] - c[:, :-k]) / (k * k)


def remove_specks(px, radius=3, drop=0.10):
    """Pull pixels that are much darker than their surroundings back to the local mean: the skin
    textures carry pores, moles and nostril dots that are single black specks at game size."""
    blur = box_blur(px[:, :, :3], radius)
    dark = (blur.mean(axis=2) - px[:, :, :3].mean(axis=2) - drop) / drop
    k = np.clip(dark, 0.0, 1.0)[:, :, None]
    px[:, :, :3] = px[:, :, :3] * (1.0 - k) + blur * k


def scaled_image(path, size, tint=(1.0, 1.0, 1.0), out_dir=None, name=None, layers=(), floor=0.0, despeckle=0):
    """Load an image, scale it to size x size, multiply by tint, lift every pixel darker than `floor`
    (a mean of 0..1) up to it, pull dark specks back to their surroundings (despeckle: window radius in
    pixels), paint the layers [(splats, colour)] (splats are (u, v, amount): a soft
    dot of the colour), save as JPEG, return the Blender image."""
    img = bpy.data.images.load(str(path), check_existing=False)
    img.scale(size, size)
    px = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(-1, 4)
    px[:, 0] *= tint[0]
    px[:, 1] *= tint[1]
    px[:, 2] *= tint[2]
    px = px.reshape(size, size, 4)
    if despeckle:
        remove_specks(px, radius=despeckle)
    if floor:
        # the skin textures paint the nostrils, the mouth and the eye corners almost black: at game
        # size those are single dark specks on the face
        lum = px[:, :, :3].mean(axis=2, keepdims=True)
        px[:, :, :3] += np.maximum(0.0, floor - lum)
    r = max(2, size // 160)
    ys, xs = np.mgrid[-r:r + 1, -r:r + 1]
    kernel = np.exp(-(xs * xs + ys * ys) / (0.5 * r * r)).astype(np.float32)
    for splats, splat_colour in layers:
        mask = np.zeros((size, size), dtype=np.float32)
        for u, v, k in splats:
            x, y = int(u * (size - 1)), int(v * (size - 1))
            y0, y1, x0, x1 = max(0, y - r), min(size, y + r + 1), max(0, x - r), min(size, x + r + 1)
            patch = kernel[y0 - (y - r):y1 - (y - r), x0 - (x - r):x1 - (x - r)] * k
            mask[y0:y1, x0:x1] = np.maximum(mask[y0:y1, x0:x1], patch)
        for c in range(3):
            px[:, :, c] = px[:, :, c] * (1.0 - mask) + splat_colour[c] * mask
    px = px.reshape(-1, 4)
    img.pixels.foreach_set(px.ravel())
    out = Path(out_dir) / f"{name or Path(path).stem}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.filepath_raw = str(out)
    img.file_format = "JPEG"
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 88
    img.save()
    img.name = name or Path(path).stem
    return img


# ---------------------------------------------------------------- vertex colours

def paint(obj, fn):
    """Set the colour attribute 'Col' of obj: fn(vertex position) -> (r, g, b), linear. The attribute holds
    the colour encoded as sRGB: Godot keeps a vertex colour in 8 bits, and figure.gdshader decodes it."""
    mesh = obj.data
    attr = mesh.color_attributes.get("Col") or mesh.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    data = []
    for v in mesh.vertices:
        r, g, b = finish.srgb_encode(fn(v.co))
        data.extend((r, g, b, 1.0))
    attr.data.foreach_set("color", data)
    mesh.color_attributes.active_color = attr


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def linear(c):
    """Recipe colours are sRGB, like Godot's Color constants; the mixing below is in linear light."""
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in (max(0.0, v) for v in c))


def cloth_colour(base, wear, seed):
    """Wool colour with mud toward the hem and the knees, wet darkening, weave-scale mottling and,
    where wear has "stain", greasy blotches that gather low on the front (an apron)."""
    dirt = wear.get("dirt", 0.3)
    wet = wear.get("wet", 0.15)
    stain = wear.get("stain", 0.0)
    base = linear(base)
    mudc = linear((0.20, 0.16, 0.11))
    stainc = linear(wear.get("stain_colour", (0.22, 0.14, 0.08)))

    def fn(p):
        n = noise.fractal(Vector((p.x * 9 + seed, p.y * 9, p.z * 9)), 0.5, 2.0, 3)
        mottle = 1.0 + 0.16 * n
        mud = dirt * smoothstep(0.75, 0.15, p.z) * (0.6 + 0.8 * abs(noise.fractal(Vector((p.x * 5, p.y * 5, p.z * 3 + seed)), 0.5, 2.0, 2)))
        k = mottle * (1.0 - wet) * (1.0 - 0.55 * min(1.0, mud))
        r, g, b = (base[0] * k, base[1] * k, base[2] * k)
        mix = min(0.5, mud * 0.5)
        r, g, b = (r * (1 - mix) + mudc[0] * mix, g * (1 - mix) + mudc[1] * mix, b * (1 - mix) + mudc[2] * mix)
        if stain:
            blot = noise.fractal(Vector((p.x * 7 + seed * 3, p.y * 7, p.z * 7)), 0.5, 2.0, 3)
            low = 0.6 + 0.4 * smoothstep(1.1, 0.5, p.z)
            s_ = stain * low * smoothstep(0.02, 0.30, blot + 0.12)
            r, g, b = (r * (1 - s_ * 0.8) + stainc[0] * s_ * 0.8, g * (1 - s_ * 0.8) + stainc[1] * s_ * 0.8,
                       b * (1 - s_ * 0.8) + stainc[2] * s_ * 0.8)
        return (r, g, b)

    return fn


def beard_amount(p, m, cfg):
    """0..1: how much grey beard covers the skin at p (a point of the head in metres)."""
    top = m.lips_z + cfg.get("up", 0.02)
    chin = m.chin_z - 0.035
    front = p.y < m.head_centre.y - 0.02
    side = abs(p.x) > 0.075 and m.chin_z - 0.02 < p.z < m.eye_z - 0.01 and p.y < m.head_centre.y + 0.07
    if not front and not side:
        return 0.0
    if p.z > top and not side:
        return 0.0
    n = 0.5 + 0.5 * noise.fractal(Vector((p.x * 60, p.y * 60, p.z * 60)), 0.5, 2.0, 2)
    edge = smoothstep(top, top - 0.02, p.z) * smoothstep(chin - 0.02, chin + 0.02, p.z)
    if side:
        edge = max(edge, smoothstep(m.eye_z, m.eye_z - 0.04, p.z) * 0.8)
    return cfg.get("strength", 0.7) * edge * (0.6 + 0.4 * n)


def hair_amount(p, m, cfg):
    """0..1: how much hair covers the skin at p: above the hairline and beside the eyes at the temples."""
    line = m.brow_z + cfg.get("hairline", 0.030) + cfg.get("widow", 0.022) * min(1.0, (abs(p.x) / 0.08) ** 2)
    top = smoothstep(line - 0.006, line + 0.006, p.z)
    temple = smoothstep(0.062, 0.074, abs(p.x)) * smoothstep(m.eye_z - 0.045, m.eye_z - 0.005, p.z)
    n = 0.5 + 0.5 * noise.fractal(Vector((p.x * 80, p.y * 80, p.z * 80)), 0.5, 2.0, 2)
    return cfg.get("strength", 0.8) * max(top, temple) * (0.7 + 0.3 * n)


def face_splats(skin_obj, m, amount_fn, grid=3):
    """[(u, v, amount)] over the skin where amount_fn(point) > 0: each polygon is sampled on a
    grid x grid lattice, so a feature thinner than the polygons still gets painted."""
    mesh = skin_obj.data
    uv = mesh.uv_layers.active.data
    out = []
    steps = [(i + 0.5) / grid for i in range(grid)]
    for poly in mesh.polygons:
        if poly.loop_total != 4:
            continue
        pts = [mesh.vertices[mesh.loops[i].vertex_index].co for i in poly.loop_indices]
        uvs = [uv[i].uv for i in poly.loop_indices]
        for a in steps:
            for b in steps:
                w = ((1 - a) * (1 - b), a * (1 - b), a * b, (1 - a) * b)
                p = sum((pt * wk for pt, wk in zip(pts, w)), Vector())
                k = amount_fn(p)
                if k > 0.02:
                    out.append((sum(u[0] * wk for u, wk in zip(uvs, w)), sum(u[1] * wk for u, wk in zip(uvs, w)), k))
    return out


def brow_amount(m, cfg):
    """Eyebrows: an arch above each eye, rising outward."""
    thickness = cfg.get("thickness", 0.0055)

    def fn(p):
        if p.y > m.head_centre.y - 0.03 or not 0.014 < abs(p.x) < cfg.get("half_width", 0.064):
            return 0.0
        z0 = m.brow_z + cfg.get("raise", -0.004) + cfg.get("arch", 0.12) * (abs(p.x) - 0.014)
        d = (p.z - z0) / thickness
        return cfg.get("strength", 0.7) * math.exp(-d * d)
    return fn


def flush_amount(m, cfg):
    """Ruddy cheeks and nose tip."""
    spots = [((0.052, m.eye_z - 0.040), 0.030), ((-0.052, m.eye_z - 0.040), 0.030), ((0.0, m.eye_z - 0.050), 0.014)]

    def fn(p):
        if p.y > m.head_centre.y - 0.03:
            return 0.0
        k = 0.0
        for (cx, cz), r in spots:
            d2 = ((p.x - cx) ** 2 + (p.z - cz) ** 2) / (r * r)
            k = max(k, math.exp(-d2))
        return cfg.get("strength", 0.35) * k
    return fn


# ---------------------------------------------------------------- mesh helpers

def decimate(obj, ratio):
    if ratio >= 1.0:
        log("  part", obj.name, len(obj.data.polygons), "faces")
        return
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    mod = obj.modifiers.new("decimate", "DECIMATE")
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    log("  part", obj.name, "->", tri_count(obj), "triangles")


def triangulate(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()


def join(objs):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    return objs[0]


def tri_count(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    return len(mesh.loop_triangles)


# ---------------------------------------------------------------- build

def load_recipe(path):
    return json.loads(Path(path).read_text())


def add_eyes(body, recipe):
    from bl_ext.user_default.mpfb.services import HumanService, LocationService
    root = Path(LocationService.get_user_data("eyes"))
    mhclo = root / "low-poly" / "low-poly.mhclo"
    eyes = HumanService.add_mhclo_asset(str(mhclo), body, asset_type="Eyes", subdiv_levels=0, material_type="MAKESKIN",
                                        set_up_rigging=True, interpolate_weights=True, import_subrig=False,
                                        import_weights=True)
    eyes.name = "eyes"
    return eyes, root / "materials" / f"{recipe.get('eyes', 'brown')}_eye.png"


def skin_texture_path(name):
    from bl_ext.user_default.mpfb.services import LocationService
    folder = Path(LocationService.get_user_data("skins")) / name
    found = sorted(folder.glob("*diffuse*.png"))
    if not found:
        raise FileNotFoundError(f"skin {name}: no diffuse texture in {folder} (run scripts/fetch_character_assets.py)")
    return found[0]


def build(recipe, options):
    out_dir = Path(recipe.get("export", {}).get("dir", ROOT / "game" / "assets" / "characters"))
    work = ROOT / "renders" / "characters" / recipe["id"]
    work.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    log("recipe", recipe["id"])
    body, rig = mpfb_body.make_body(recipe)
    eyes, eye_png = add_eyes(body, recipe)
    mpfb_body.remove_helper_geometry(body)
    m = garments.Measures(body, rig)
    mpfb_body.drop_unused_groups(body, rig, set(BONES))
    spec = recipe.get("garments", {})
    wear = recipe.get("wear", {})
    parts = []

    def add(obj, ratio, kind):
        decimate(obj, ratio)
        parts.append((obj, kind))

    skin_obj = garments.skin(body, rig, m, spec.get("skin", {}))
    skin_ratio = recipe.get("detail", {}).get("skin", 0.14)
    detail = recipe.get("detail", {})
    cloth_parts = []
    dress = []
    if "tunic" in spec:
        tunic = garments.tunic(body, rig, m, spec["tunic"])
        skirt_spec = dict(spec["tunic"])
        skirt_spec.update(spec.get("skirt", {}))
        skirt = garments.skirt(body, rig, m, tunic, skirt_spec)
        cloth_parts += [(tunic, detail.get("tunic", 0.4)), (skirt, 1.0)]
        dress = [tunic, skirt]
    if "apron" in spec:
        for o in garments.apron(body, rig, m, dress, spec["apron"]):
            cloth_parts.append((o, detail.get("apron", 0.4)))
    if "hose" in spec:
        hose = garments.hose(body, rig, m, spec["hose"])
        garments.hose_trim(hose, m, m.knee_z + spec.get("tunic", {}).get("hem_above_knee", 0.07),
                           m.ankle_z + spec.get("boots", {}).get("height", 0.26))
        cloth_parts.append((hose, detail.get("hose", 0.35)))
    if "boots" in spec:
        cloth_parts.append((garments.boots(body, rig, m, spec["boots"]), detail.get("boots", 0.22)))
    if "coif" in spec:
        cloth_parts.append((garments.coif(body, rig, m, spec["coif"]), detail.get("coif", 0.4)))
    if "kerchief" in spec:
        for o in garments.kerchief(body, rig, m, spec["kerchief"]):
            cloth_parts.append((o, 1.0 if o.name.startswith("kerchief_ties") else detail.get("kerchief", 0.4)))
    if "hood" in spec:
        cloth_parts.append((garments.hood(body, rig, m, spec["hood"]), detail.get("hood", 0.3)))
    if "hair" in spec:
        cloth_parts.append((garments.hair_cap(body, rig, m, spec["hair"]), detail.get("hair", 0.4)))
    if "jerkin" in spec:
        cloth_parts.append((garments.jerkin(body, rig, m, spec["jerkin"]), detail.get("jerkin", 0.35)))
    if "belt" in spec:
        cloth_parts.append((garments.belt(body, rig, m, spec["belt"]), detail.get("belt", 0.6)))
    if "cloak" in spec:
        shell, hem = garments.cloak(body, rig, m, spec["cloak"])
        cloth_parts += [(shell, detail.get("cloak", 0.4)), (hem, 1.0)]
    if "satchel" in spec:
        for o in garments.satchel(body, rig, m, spec["satchel"]):
            cloth_parts.append((o, 1.0))
    # the bare body, hidden and not exported: the floor under a lying figure is measured on it
    ground = body.copy()
    ground.data = body.data.copy()
    ground.name = "ground_ref"
    bpy.context.collection.objects.link(ground)
    bpy.data.objects.remove(body)

    # materials
    skin_cfg = recipe.get("skin", {})
    layers = []
    if skin_cfg.get("flush"):
        layers.append((face_splats(skin_obj, m, flush_amount(m, skin_cfg["flush"])),
                       tuple(skin_cfg["flush"].get("color", (0.78, 0.40, 0.34)))))
    if skin_cfg.get("hair"):
        hair = skin_cfg["hair"]
        layers.append((face_splats(skin_obj, m, lambda p: hair_amount(p, m, hair)), tuple(hair.get("color", (0.60, 0.59, 0.58)))))
    if skin_cfg.get("brows"):
        brows = skin_cfg["brows"]
        layers.append((face_splats(skin_obj, m, brow_amount(m, brows)), tuple(brows.get("color", (0.45, 0.44, 0.43)))))
    if skin_cfg.get("beard"):
        beard = skin_cfg["beard"]
        layers.append((face_splats(skin_obj, m, lambda p: beard_amount(p, m, beard)), tuple(beard.get("color", (0.62, 0.60, 0.58)))))
    skin_img = scaled_image(skin_texture_path(skin_cfg.get("name", "young_caucasian_male")),
                            skin_cfg.get("size", 1024), tuple(skin_cfg.get("tint", (1, 1, 1))), work, "skin",
                            layers=layers, floor=skin_cfg.get("floor", 0.24),
                            despeckle=skin_cfg.get("despeckle", 3))
    eye_img = scaled_image(eye_png, 128, (1, 1, 1), work, "eyes")
    skin_mat = image_material("skin", skin_img, 0.62)
    eyes_mat = image_material("eyes", eye_img, 0.18)
    cloth_mat = cloth_material("cloth", recipe.get("cloth_roughness", 0.88))

    decimate(skin_obj, skin_ratio)
    paint(skin_obj, lambda p: (1.0, 1.0, 1.0))
    skin_obj.data.materials.append(skin_mat)
    eyes.data.materials.clear()
    eyes.data.materials.append(eyes_mat)
    paint(eyes, lambda p: (1.0, 1.0, 1.0))
    for mod in list(eyes.modifiers):
        if mod.type != "ARMATURE":
            eyes.modifiers.remove(mod)
    all_objs = []
    seed = 3.0
    for obj, ratio in cloth_parts:
        decimate(obj, ratio)
        kind = obj.get("garment", "tunic")
        colour = obj.get("color", [0.3, 0.3, 0.3])
        own = dict(wear, **json.loads(obj["wear"])) if "wear" in obj else dict(wear)
        if kind == "leather":
            own["dirt"] = own.get("dirt", 0.3) * 0.5
        if obj.name != "skirt":              # the skirt's shape is fitted to the legs (posefit.py)
            garments.wrinkle(obj, kind, seed)
        paint(obj, cloth_colour(colour, own, seed))
        finish.set_attribute(obj, "kind", finish.KIND_CODE.get(kind, 0.0))
        if kind == "hair":
            finish.hair_edge(obj)
        seed += 1.7
        obj.data.materials.append(cloth_mat)
        all_objs.append(obj)
    for o in (skin_obj, eyes):
        finish.set_attribute(o, "kind", 0.0)
    all_objs += [skin_obj, eyes]       # cloth first: material slot 0 (see _vertex_colour)
    for o in all_objs:
        for key in ("garment", "color", "wear"):
            if key in o:
                del o[key]
    mesh = join(all_objs)
    mesh.name = "mesh"
    mesh.data.name = "mesh"
    for mod in list(mesh.modifiers):
        mesh.modifiers.remove(mod)
    triangulate(mesh)
    mesh.parent = rig
    arm_mod = mesh.modifiers.new("Armature", "ARMATURE")
    arm_mod.object = rig
    mpfb_body.remove_finger_bones(rig)
    # weights: four influences, normalised
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.mode_set(mode="OBJECT")
    for g in list(mesh.vertex_groups):
        if g.name not in BONES:
            mesh.vertex_groups.remove(g)
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    for poly in mesh.data.polygons:
        poly.use_smooth = True
    log("triangles", tri_count(mesh), "vertices", len(mesh.data.vertices), "bones", len(rig.data.bones))
    for attr in mesh.data.color_attributes:
        vals = [tuple(d.color) for d in attr.data]
        n = len(vals)
        per_mat = {}
        for poly in mesh.data.polygons:
            for vi in poly.vertices:
                per_mat.setdefault(poly.material_index, []).append(tuple(attr.data[vi].color))
        for mi_, vs in sorted(per_mat.items()):
            log("  material slot", mi_, mesh.data.materials[mi_].name, "mean", [round(sum(v[i] for v in vs) / len(vs), 3) for i in range(3)])
        log("colour attribute", attr.name, attr.domain, attr.data_type, "active" if attr == mesh.data.color_attributes.active_color else "", "mean", [round(sum(v[i] for v in vals) / n, 3) for i in range(3)])
    return mesh, rig, m, out_dir, work


def build_animations(recipe, rig, m):
    info = {}
    cfg = recipe.get("animations", {})
    bvh_dir = ROOT / "characters" / "vendor" / "bvh"
    cache = {}

    def source(name):
        if name not in cache:
            cache[name] = retarget.Source(str(bvh_dir / f"{name}.bvh"))
        return cache[name]

    rt = retarget.Retargeter(rig)
    rt_ref = {}
    for clip, c in cfg.items():
        src = source(c["bvh"])
        if c["bvh"] not in rt_ref:
            rt.reference(src)
            rt_ref[c["bvh"]] = True
        else:
            rt.reference(src)
        if c["type"] == "walk":
            frames, meta = retarget.walk_clip(src, rt, SPEED, fps_out=c.get("fps", 30))
            frames = retarget.ground_clip(rt, frames, rig)
        elif c["type"] == "rest":
            # a lying or sitting pose: one source pose held, the chest breathing; lying clips are
            # put on the floor by the bare body
            from mathutils import Vector
            frames, meta = retarget.rest_clip(
                src, rt, c["t"], period_s=c.get("period_s", 9.0), breaths=c.get("breaths", 2),
                breath_deg=c.get("breath_deg", 2.5), fps_out=c.get("fps", 30),
                head_dir=Vector(c.get("head_dir", (0, -1, 0))), tweaks=c.get("tweaks"))
            frames, extent = retarget.lying_ground(rt, rig, bpy.data.objects["ground_ref"], frames)
            meta.update(extent)
        else:
            a, b = c["range_s"]
            frames, meta = retarget.clip_from_range(src, rt, int(a * src.fps), int(b * src.fps), fps_out=c.get("fps", 30),
                                                    loop_overlap_s=c.get("overlap_s", 0.5), rate=c.get("rate", 1.0),
                                                    amplitude=c.get("amplitude", 1.0))
            frames = retarget.ground_clip(rt, frames, rig)
        meta["source"] = c["bvh"]
        retarget.make_action(rig, rt, clip, frames, fps=meta["fps"])
        if c["type"] == "walk":
            meta.update(retarget.walk_metadata(rt, frames, meta))
        info[clip] = meta
        log("clip", clip, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in meta.items() if k != "contacts"})
    rig.animation_data.action = None
    return info


def fit_cloth(recipe, mesh, rig, info):
    """Shape keys of the free cloth (posefit.py) for the clips the recipe's "fit" names:
    {"walk": {"mode": "clear", "keys": 8}, "sleep": {"mode": "drape"}, "sit": {"mode": "drape", "floor": "seat"}}"""
    ground = bpy.data.objects["ground_ref"]
    result = {}
    for clip, cfg in recipe.get("fit", {}).items():
        action = bpy.data.actions.get(clip)
        if action is None or "fit" not in mesh.data.attributes:
            continue
        got = posefit.fit_clip(mesh, rig, ground, action, cfg.get("mode", "clear"), keys=cfg.get("keys"),
                               floor_z=cfg.get("floor", 0.0))
        if got:
            if cfg.get("mode", "clear") == "clear":
                worst, share = posefit.penetration_report(mesh, rig, ground, action)
                got["unfitted_penetration_m"] = round(worst, 4)
                log("  unfitted cloth: deepest %.3f m, %d %% of the frames over 5 mm" % (worst, share * 100))
                worst, share = posefit.penetration_report(mesh, rig, ground, action, fits={clip: got})
                got["fitted_penetration_m"] = round(worst, 4)
                log("  fitted cloth:   deepest %.3f m, %d %% of the frames over 5 mm" % (worst, share * 100))
            result[clip] = got
    rig.animation_data.action = None
    return result


def export(recipe, mesh, rig, out_dir, info, m):
    out_dir.mkdir(parents=True, exist_ok=True)
    fit = info.pop("_fit", {})
    glb = out_dir / f"{recipe['id']}.glb"
    for o in bpy.context.selected_objects:
        o.select_set(False)
    mesh.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(
        filepath=str(glb), export_format="GLB", use_selection=True, export_apply=False,
        export_image_format="JPEG", export_jpeg_quality=85, export_yup=True, export_skins=True,
        export_animations=True, export_animation_mode="ACTIONS", export_force_sampling=True,
        export_optimize_animation_size=True, export_vertex_color="MATERIAL", export_all_vertex_colors=False,
        export_cameras=False, export_lights=False, export_morph=bool(fit), export_morph_normal=True,
        export_texcoords=True, export_normals=True, export_tangents=False, export_def_bones=False)
    meta = {
        "id": recipe["id"],
        "height_m": m.height,
        "radius_m": round(m.hip_radius, 3),
        "speed_m_s": SPEED,
        "animations": info,
        "fit": fit,
        "triangles": tri_count(mesh),
    }
    (out_dir / f"{recipe['id']}.json").write_text(json.dumps(meta, indent=1, default=lambda o: list(o)))
    log("wrote", glb, glb.stat().st_size // 1024, "KiB")


def main():
    recipe_path, options = parse_args()
    recipe = load_recipe(recipe_path)
    mesh, rig, m, out_dir, work = build(recipe, options)
    info = {} if options.get("no-anim") else build_animations(recipe, rig, m)
    fits = {} if options.get("no-anim") or options.get("no-fit") else fit_cloth(recipe, mesh, rig, info)
    if info:
        idle = bpy.data.actions.get("idle")
        if idle and not options.get("no-ao"):
            occ = finish.bake_occlusion(mesh, rig, idle)
            finish.write_uv2(mesh, occ)
            if options.get("show-ao"):         # debugging: the occlusion as the vertex colour, for --sketch
                attr = mesh.data.color_attributes["Col"]
                attr.data.foreach_set("color", [c for v in occ for c in (1 - min(1, v * 1.35),) * 3 + (1.0,)])
        rig.animation_data.action = None
    bpy.data.objects.remove(bpy.data.objects["ground_ref"])
    if fits:
        info["_fit"] = fits
    if not options.get("no-export"):
        export(recipe, mesh, rig, out_dir, info, m)
    if options.get("preview"):
        import preview
        preview.preview(rig, str(work / "preview"))
    if options.get("sketch"):
        import preview
        preview.sketch(rig, str(work / "sketch"), clips=options.get("clips"), fits=fits)


if __name__ == "__main__":
    main()

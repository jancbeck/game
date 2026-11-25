# Data contract: files the game reads

All paths in the data are relative to `game/`. Units are metres, seconds and pixels of the 2560 × 1440 game frame (row 0 at the top).

## Coordinates

Blender and `plan.json` are Z-up: X east, Y north, Z up. Godot is Y-up with -Z forward. Every
point and direction in the data goes through the rotation the glTF exporter uses:

    godot (x, y, z) = blender (x, z, -y)

so north is Godot -Z. `scene.json` stores this matrix as `conversion.godot_from_blender`.

## `data/scene.json`

| Key | Content |
|-----|---------|
| `camera` | Orthographic camera: `origin`, `basis_x/y/z` (Godot axes; it looks along -Z), `ortho_width_m` 35.0, `ortho_height_m`, `px_per_m` 73.14, `resolution`, `near`, `far`, and the Blender values under `blender` |
| `depth` | `file` (`assets/depth.f32`), `width`, `height`, `min_m`, `max_m`, `sky_m`, `sky_fraction` |
| `background` | `assets/layers/reference.png` |
| `layers` | See below |
| `masks` | `puddle`, `wet`, `normal`, `ids` (PNG paths) |
| `views` | `wide` and `tiles`, see below |
| `flipbooks` | List, see below |
| `crows` | `model` (`assets/crow.glb`), `head_height_m`, `perches`, `start` |
| `walk` | `mesh` (`assets/walk.glb`), `surfaces`, `surface_area_m2`, `wall_walks`, `links`, `exits`, `portals` |
| `proxy`, `proxy_counts` | `assets/proxy.glb`: wall and tower boxes with the gate passage open, prop footprint hulls, the floor |
| `ambient` | Sky fill colour, moon settings, `moon_direction` |
| `lights` | Point lights: `name`, `position`, `color`, `watts`, `reach_m`, `radius_m`, `inside_wall`, `group` |
| `checks` | Render checks and timings; not read by the game |

### Layers

```json
"layers": {
  "color_space": "linear Rec.709, scene-referred, exposure already applied",
  "view_transform": "AgX", "look": "AgX - Punchy", "exposure_applied_ev": 1.3,
  "post": {"saturation": 0.9, "bloom": 0.6, "...": "..."},
  "base": "assets/layers/base.exr",
  "groups": [{"id": "fire_basket", "image": "assets/layers/lg_fire_basket.exr", "curve": "fire",
              "seed": 3, "prop": "brazier", "anchor": [x, y, z]}],
  "reference": "assets/layers/reference.png",
  "reference_post": "assets/layers/reference_post.png"
}
```

- Final linear image = `base + Σ group × intensity(t)`. Intensity is 1.0 at rest.
- `curve` is one of `fire`, `interior`, `lamp`, `banked`, the curve families of anim.py. `seed`
  is the source's seed, so the game flickers each source like the videos do.
- `post` is the compositor post of `layout.json`. The game runs it in linear light: it divides by
  2^`exposure_applied_ev` first and multiplies back after.

### Depth and masks

- `depth.f32`: float32 little-endian, width × height, row 0 at the top. Metres along the camera
  axis from the camera origin. Sky pixels hold `sky_m`.
- `puddle.png`: 8-bit grey, 1 where standing water is.
- `wet.png`: 8-bit grey, how wet the surface is.
- `normal.png`: camera-space unit normal as rgb = n × 0.5 + 0.5 (x right, y up, z toward the camera).
- `ids.png`: 8-bit, 0 = nothing, k = hotspot k (1-based, in `hotspots.json` order).

### Zoom views

```json
"views": {
  "wide": {"camera": {"...": "same keys as the main camera"}, "base": "assets/wide/base.exr",
           "groups": [{"id": "...", "image": "assets/wide/lg_<id>.exr"}],
           "depth": "assets/wide/depth.f32", "depth_meta": {"...": "..."}, "ids": "assets/wide/ids.png",
           "masks": {"puddle": "...", "wet": "..."}, "reference": "assets/wide/reference.png"},
  "tiles": [{"id": "trough", "hotspot": "trough", "rect": [x0, y0, 1280, 720], "scale": 2,
             "base": "assets/tiles/trough/base.exr", "groups": [{"id": "...", "image": "..."}],
             "depth": "assets/tiles/trough/depth.f32", "ids": "assets/tiles/trough/ids.png",
             "masks": {"puddle": "...", "wet": "..."}, "reference": "assets/tiles/trough/reference.png"}]
}
```

- All views share the main camera's direction and image centre.
- `wide`: zoom 0.5, its own camera block, the same light groups as the main frame.
- `tiles`: one per hotspot. `rect` is in main-frame pixels; the tile images are `rect × scale`
  pixels. A tile lists only the light groups that reach it. The faint rest of the others is
  added to its base, so base + listed groups is the whole picture at rest.

### Flipbooks

```json
{"id": "fire_basket_flame", "atlas": "assets/flipbooks/fire_basket_flame.png",
 "cols": 9, "rows": 8, "frames": 72, "fps": 24.0, "loop": true,
 "rect": [x0, y0, w, h], "cell": [w, h], "blend": "premul", "encoding": "srgb", "scale": 6.75,
 "depth": null, "depth_m": 44.69, "group": "fire_basket", "kind": "flame",
 "density": 1, "source": "mantaflow"}
```

- Atlas: `cols × rows` cells, frames row-major from the top left, premultiplied RGBA.
  rgb = srgb_encode(linear / `scale`). The runtime multiplies back by `scale`.
- `rect`: the element's rectangle in the main frame. Frames are cropped to it.
- `depth`: per-pixel depth file, or null; then `depth_m` is one depth for the whole element.
- `group`: the flipbook's brightness follows that light group's intensity. Smoke has none.
- `kind`: `mist`, `flame`, `smoke` or `embers`. The list is sorted by kind, then id.
- `@2`: an entry whose id ends in `@2` (`density: 2`) is the same element at twice the density.
  It replaces its 1x entry while a zoom tile that contains it is shown.

### Crows

- `crow.glb`: one perched crow at the scene's scale, facing Godot +Z at yaw 0, feet at the
  origin. Nodes `body`, `head`, `tail`, `wing_l`, `wing_r`, pivoting at the neck, the tail base
  and the shoulders.
- `perches`: `id`, `pos`, `yaw` (degrees about Godot +Y), `kind` (`prop`, `ground` or `merlon`).
  The plan's crow points are named by `perch_names` in `location.json`; merlon tops follow as
  `merlon_<k>`.
- `start`: the perches where crows sit when the scene loads.

### Walkable space

- `walk.glb`: walkable surfaces only, with obstacle footprints cut out and no agent radius. Each
  face's material names the surface underfoot: `cobble`, `mud`, `straw`, `stone_stair`,
  `stone_walk`, `wood`. Puddles are not a face type: the game reads the puddle mask under the
  figure. Stairs are treads (risers up to 0.25 m), so bake the navmesh with
  `agent_max_climb` ≥ 0.26.
- `links`: `from`, `to`, `kind` (`stair`): foot and top of each stair.
- `exits`: `id`, `pos`, `label`, `target` (the location behind the door).
- `portals`: doors the figure goes through. Walking into `a` hides the figure for `seconds`, then
  it steps out at `b`, and the reverse. `label` names `a`, `label_b` names `b`, `sound` is a key of
  `sounds.json` `portals`, `via` lists the rooms in between.

```json
"portals": [{"id": "nw_tower", "a": [x, y, z], "b": [x, y, z], "label": "North-west tower",
             "label_b": "North-east tower", "seconds": 3.0, "sound": "door_heavy",
             "via": ["nw_tower", "gatehouse", "ne_tower"]}]
```

## `data/hotspots.json`

A list, in id order of the ids masks. Each entry: `id`, `name`, `text` (the look text),
`position` (the anchor object), `volume` (`center`, `size`, `yaw_rad`: the click box),
`stand` (where the figure stands), `plan.stand_xy` and `screen_px` (the stand point in the main
frame). The source is `hotspots` in `location.json`.

## `data/sounds.json`

```json
{
  "footsteps": {"cobble": ["assets/audio/steps/cobble_01.wav", "..."], "mud": [], "puddle": [],
                "stone_stair": [], "stone_walk": [], "wood": [], "straw": []},
  "step_interval_s": 0.5,
  "click": {"walk": "assets/audio/ui/walk_click.wav", "interact": "assets/audio/ui/interact.wav"},
  "hotspots": {"gate": ["assets/audio/objects/gate_01.wav", "..."]},
  "portals": {"door_heavy": {"open": "...", "close": "..."}},
  "levels_db": {"rain_bed": -20, "footsteps": -14}
}
```

Every file is 44.1 kHz WAV. Each walk surface and `puddle` has several variants (at least 6),
so steps do not repeat audibly.

## `config.json`

`data` names the scene.json to load (`data/scene.json`), `sounds` the sounds.json. `audio` holds
the rain bed, the fire loop and the crow calls. `camera`, `rain` and `crows` tune the runtime.

## What `check` validates

`scripts/game.py check` fails when a referenced file is missing, an id repeats (light groups,
tiles, flipbooks, perches, exits, portals, lights, hotspots), a rect leaves the frame, a mask or
atlas has the wrong size, a group, perch, hotspot or portal sound is unknown, a walk surface has
no footstep clips, or the game logs a script error in a headless run.

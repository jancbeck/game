---
name: scene-build
description: Build and change the procedural Blender scene of the garrison game - locations (plan.json, trace.json, layout.json, location.json), wall blocks, props in scene/assets, materials in scene/mats, terrain, light groups, the Cycles look, preview/check views and the orbit videos. Use it for any geometry, prop, material, lighting or new-location work in Blender, even when the user just says "the wall corner looks wrong" or "add a tower".
---

# The Blender scene

Headless Blender 5.2 builds every location from data. Shared code is in `scene/`, place data
in `locations/<name>/`.

```bash
B=/Applications/Blender.app/Contents/MacOS/Blender
$B --background --python scene/build_scene.py -- --out renders/x.png [--location courtyard] \
   [--view ref|plan|eye] [--check-scale] [--layout locations/courtyard/layout_preview.json] [--percent 50] [--passes]
$B --background --python scene/prop_preview.py -- gallows      # one prop alone
$B --background --python scene/prop_preview.py -- --swatches   # every material
python3 scripts/game.py preview [--view eye] [--percent 25]   # the usual way, through the GPU queue
```

Run Blender outside the sandbox and through `scripts/gpu.py run` (see `agent-workflow`).
Blender's Python is `/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3*` and has
numpy. Never use `--save-blend` from an agent.

## A location

| File | Content |
|------|---------|
| `plan.json` | The place in metres (X east, Y north, Z up): heights, merlon style, `blocks`, `platform`, `props`, `mounted`, `crows`, `humans` |
| `trace.json` | The main orthographic camera: elevation 38°, yaw 11°, px/m, image centre |
| `layout.json` | Cycles look: resolution, samples, exposure, sky and moon, haze, post, rain, `prop_light_scale` |
| `layout_preview.json` | EEVEE look for previews, check views, videos |
| `location.json` | Tables: check-view cameras, `light_groups`, `perch_names`, `fires`, `hotspots` with look texts |

`scene/location.py` is the only code that knows these paths. Scripts take `--location <name>`
(default `courtyard`, or `GAME_LOCATION`); code reads through `location.plan()`,
`location.load(name)`, `location.table(key)`. Still courtyard-specific in shared code:
`terrain.py`, `game_walk.py`, `orbit_audio.py` sources, and props that place themselves from
plan keys (`age_dressing`, `ground_dressing`, `drips`, `west_ditch`).

## The plan (courtyard)

- Courtyard floor z = 0; the rock spur stands over ground at about z = -3. A mound follows the
  north, east and south-east walls; on the south a 10 m cliff with a breast-high parapet. The
  commander's residential tower stands on the cliff edge at the south-west. Terrain:
  `scene/terrain.py`.
- Heights: curtain walls 6 m, corner towers 11 m, gatehouse 9.5 m.
- `blocks`: masonry boxes (centre+size or `from`/`to`+thickness) with battlements on chosen
  edges; `cut_gate` cuts an arch. `platform`: the floor polygon. `props`: position, rotation,
  scale, `"z": "ground"` for the terrain. `mounted`: torches, doors, windows, banners on a wall
  face. `crows`: perches. `humans`: 1.8 m scale figures (`--check-scale`).
- The towers stand only at the back so they do not hide the yard from the camera.

## Rooms and new locations

An interior is a location with `"kind": "room"` in plan.json (cutaway walls, `ground`
{terrain, floor, apron}, `platform.walk`/`surface`), built by `scene/game_room.py`, with
`exits.list` and `people` (where a person stands) in location.json and `camera.width_m` in
trace.json (the cookhouse frames 12.8 m at 200 px/m). Its export goes to
`game/locations/<name>/` (`location.game_dir()`, paths prefixed by `location.rel_prefix()`);
rooms export `"rain": false`. Check views: `game.py preview --view a,b,c` renders several keys of
location.json `views` from one build (perspective needs `lens`, orthographic `ortho_scale`).

Room recipe (from the cookhouse):
- The camera per location lives in trace.json (`elevation_deg`, `yaw_deg`, `width_m`,
  `center_px`); a room wants a steeper, squarer camera (cookhouse 46°/5°, 13.4 m wide) and should
  fill ~80–90 % of the frame, with solid surroundings (yard paving, the wall behind), never void.
- An invisible ceiling slab (`visible_camera` off) keeps moon and sky out; light with POINT lights
  only (only point lights reach the game's live figures): warm at hearth and oven, cool at
  window and door, soft fills far in front. A light must sit below a pot, never above its rim.
- `layout.json` `rain: {count: 0, sheltered: [box]}` dries wood and iron indoors; `stone_wall` ignores it.
- `cobble_wet` breaks in a room (NaN ground maps): use `yard_paving` or `flagstone`. Coals must
  keep the material name base `embers` for anim.py.
- Proxy geometry comes from plan blocks, not boolean cuts: a doorway is separate blocks
  (partition plus lintel with `base`). A hotspot without `volume` uses the prop's whole footprint.

The commander's chamber (`locations/tower/`) is the room recipe on an upper floor: the third floor of the
tower (floor z = 0 here, 5.8 m over the yard), 5.6 x 4.2 m inside, thick walls, a timber floor, hanging over
`ground.apron` at z = -9 with the `valley` material (mist, tree crowns, a pale river). What the 46 degree / 5 degree
camera (10.6 m frame) shows decides the layout:
- Only faces turned to the camera read. Put what must be seen (door, windows, hearth, map, niche) in the back wall; the side
  wall's inner face shows as a 0.4 m strip, so a door or window in it is invisible except for a leaf standing out square.
- A back-wall window shows little of the outside: a ray descends 1.04 m per metre of wall, so only the lower part of the throat
  looks out. `assets/_tower.window` builds the splayed embrasure with a throat of 0.28 m (0.75 m wall, 1.4 m high, 0.9 m shows),
  a timber lintel, a mullion and leaves folded into the reveals (negative angle). `tower_view` puts a ledge and a pine in that
  slice, and the river runs through the strip of valley the throat looks at.
- The invisible ceiling slab covers only the room, so the wall tops stay in the moon's light; the moon comes from the north
  (`direction_euler` 44, 0, -150) and does not enter the room.
- The stair door is three blocks of the back wall plus a lintel block; its prop cuts the passage through `stair_turret` and sets
  steps down into the dark. `export_game.NOT_OBSTACLES` lists it (its leaf must not block the doorway).
- Candles and the shrine lamp are `lamp` sources (`anim.KINDS`: `tower_desk`, `tower_shrine`): their flames stay in the static frame.

Walkability: Godot erodes the floor by 0.3 m (0.1 m cells), so a lane needs 0.7 m; keep stand
points 0.35 m from obstacle hulls (convex hulls of touching parts between z 0.25 and 1.8 —
anything hanging below 1.8 m merges into one hull). Check a room without rendering:
`.venv/bin/python scripts/walkcheck.py --location <name>` (~15 s) reports clearance and
reachability of every stand, exit and person. Keep window lights 0.4 m from jambs; use the dull
`cliff_rock`, not glossy `rock`, for rock the camera sees.

Walk slabs on wall-walks are built at `WALK_TOP` (game_walk.py): the few-mm `h_offset` between
blocks otherwise splits one walk into disconnected pieces.

## Props

One module per prop: `scene/assets/<name>.py` with `build(kit, mats, rng) -> root` (contract in
`scene/assets/__init__.py`). Use `scene/kit.py` helpers and only materials from
`scene/materials.py`. `barrel#2` places another instance. Fire props declare point lights in
`LIGHTS`; flame meshes cast no shadow.

## Materials

Keys are `SPECS` in `scene/materials.py`. A file `scene/mats/<key>.py` with
`build(mat, nt, bsdf)` replaces the built-in recipe. Helpers `_obj_coords`, `_noise`, `_ramp`,
`_map`, `_bump` import from `materials`; object coordinates are metres (kit keeps scale 1).
Wood, `stone_wall` and `iron` layer Poly Haven CC0 scans (`scene/textures/`, fetched with
`python3 scripts/fetch_textures.py`, helpers in `scene/mats/_scan.py`) under procedural weathering.

## Look

Cool moon from high north-west; the blue-hour sky gradient lights the scene; fires light their
pools. Cycles on Metal, denoised, for the stills and the game; EEVEE for previews and videos.
Compositor post: saturation, bloom, lift/gamma/gain, vignette (Kuwahara available, off). Each
flickering source is a light group named in `location.json` `light_groups`.

## Videos and stills

`scripts/iterate.sh` renders the main Cycles still plus scale, plan and eye views and scores
them against `ref/courtyard.webp` (`scripts/compare.py`). `scripts/orbit.sh [--move descent]`
renders the orbit or descent video with a spatial soundtrack (`scene/orbit_audio.py`). Videos
are optional tooling, not a deliverable.

## Known issues

- **Coplanar solids** render black in Cycles: blocks of equal height that meet get an
  `h_offset` of a few mm.
- **EEVEE shadow budget**: watch for "Shadow buffer full"; raise `shadow_pool_size` or drop a light.
- The Cycles still is static; fire and smoke shader noise follows scene frames, not `anim.apply(t)`.
- TRELLIS.2 (`scripts/gen_prop.sh`) makes dark, noisy meshes; keep it for a hero prop procedural
  modelling cannot reach.

Before committing scene work: check the change in `preview` (default and `--view eye`) against a
1.8 m figure and the consistency rules in `AGENTS.md`, then `scripts/game.py status` to see
which final steps it made stale.

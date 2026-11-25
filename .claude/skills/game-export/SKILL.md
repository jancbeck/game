---
name: game-export
description: The Blender-to-Godot export of a garrison-game location - scripts/game.py tiers (check, preview, draft, final, status, adopt), the export steps (layers, ids, wide, tiles, flipbooks, fire, lut, export), stale-step hashing, render times, what is in the static frame, and the data contract of scene.json, hotspots.json and sounds.json. Use it whenever you render or export game data, change what the game reads, add a hotspot, light group, flipbook or location, or wonder why a step re-runs.
---

# Game export

`scripts/game.py` is the one entry point. All Blender runs that render go through the GPU queue
(see `agent-workflow`).

```bash
python3 scripts/game.py check   [--location courtyard] [--no-build]   # ~1 min, no GPU
python3 scripts/game.py preview [--view ref|eye|plan] [--percent 50] [--check-scale]
python3 scripts/game.py draft   [step ...]     # low quality into renders/draft/<location>/
python3 scripts/game.py final   [step ...]     # full quality into the game folder; only stale steps
python3 scripts/game.py status  [--tier final] # which steps are stale, and the changed inputs
python3 scripts/game.py adopt                  # mark the current export as up to date
python3 scripts/game.py --location cookhouse draft --full-frame --all-tiles --to-game   # playable draft of a non-first location (draft stamps never satisfy final)
```

`final` runs only on the user's go, overnight. Each step hashes its inputs (code without
comments, location files without `_doc` keys, its arguments, the Blender version) into
`<out>/build/steps/<step>.json`; unchanged steps are skipped. Hidden files are ignored.

## Steps

| Step | Script | Renders | Final time (M1 Pro) | Writes (under the game folder) |
|------|--------|---------|---------------------|------------------------|
| layers | `scene/game_layers.py` | Cycles 128 spp | 35 min | `assets/layers/`, `assets/depth.f32`, `assets/masks/{puddle,wet,normal}.png`, `build/layers.json` |
| ids | `scene/game_views.py --view ids` | Cycles data | 3 min | `assets/masks/ids.png`, `build/view_ids.json` |
| wide | `game_views.py --view wide` | Cycles 64 spp | 16 min | `assets/wide/`, `build/view_wide.json` |
| tiles | `game_views.py --view tiles` | Cycles 80 spp | 56 min | `assets/tiles/<hotspot>/`, `build/view_tiles.json` |
| flipbooks | `scene/game_flipbooks.py` | EEVEE | 3 min | `assets/flipbooks/`, `build/flipbooks.json` |
| fire | `scene/game_fire.py` | Mantaflow (CPU) + EEVEE | 7 min, bakes reused | `assets/flipbooks/*_flame{,@2}.png`, `build/fire_flipbooks.json` |
| lut | `scene/bake_view_lut.py` | no | seconds | `luts/agx__punchy.{f32,json}` |
| export | `scene/export_game.py` | no | 2 min | `assets/{proxy,walk,crow}.glb`, `data/scene.json`, `data/hotspots.json` |

Every step builds the scene itself (~1 min) through `game_frame.build()`. `build/*.json` hand
over from the render steps to the export, which merges them (fire flipbooks replace flipbooks
with the same id). What re-runs: a hotspot text → export only; a hotspot click box → ids, wide,
tiles, export; a prop or material → everything but the LUT.

`data/sounds.json` is not written by Blender; see `sound-effects`.

## Exits

A location's doors to other places are `walk.exits` of scene.json: id, pos, label, target. A room lists them in `location.json`
`exits.list` (`game_room.exits()`). The yard has the doors of `game_walk.exits()` and also reads its own `exits.list`, for doors
that belong to no prop: `tower` at (-9.5, -12.55), the gap in the south parapet near the south-west corner, which is on the walk mesh.
The export step is stale when `exits` or `people` change.

## Where a location's game data goes

The courtyard exports into `game/` (`assets/`, `data/`, `build/`). Every other location
exports to `game/locations/<name>/` with the same layout; `location.game_dir()` decides. Paths
inside any scene.json are relative to `game/`. Shared files stay at the top: `luts/`, shared
audio, `config.json`.

## What is in the static frame

Everything that does not move. Rain, splashes, drip strands, smoke, embers, ground mist and
crows are left out (`game_frame.HIDDEN_PROPS`, `hide_moving`) and drawn by the game. Open-fire
flames are hidden from camera rays only: they still light the scene and show in reflections,
in their light group. Coals, interior lamps and room glow stay in the frame in their group.

- **Layers:** one Cycles render with one light group per flickering source (ids from
  `location.json` `light_groups`), each denoised, half-float EXR, scene-linear Rec.709 with the
  exposure multiplied in. `base + Σ group × intensity(t)` through AgX "Punchy" is the picture.
  The script checks the sum against Cycles' combined pass.
- **Zoom views:** `wide` is 2560 × 1440 over twice the frame (zoom 0.5); `tiles` are a
  1280 × 720 main-frame rect per hotspot at twice the density, rendered as a union of
  overlapping border renders and cut out. A second fast pass without haze gives depth, masks, ids.
- **Flipbooks:** EEVEE at the game camera with every static object as holdout; embers loop,
  flames and smoke cross-fade the end into the start. The fire step replaces open-fire flames
  with Mantaflow sims (`fires` in `location.json`) plus `@2` versions; bakes are cached under
  `build/fire/cache_<fire>/`.

## Data contract

Read `references/data-contract.md` before changing anything the game reads: coordinates
(`godot = (x, z, -y)` of Blender), `scene.json` keys (camera, depth, layers, masks, views,
flipbooks, crows, walk, proxy, lights), `hotspots.json`, `sounds.json`, `config.json`, and what
`check` validates.

## Release build

The dev game reads raw EXRs. A release converts them to GPU-compressed textures and exports a
Mac app (no GPU needed for the build):

```bash
python3 scripts/release.py build [--format astc|bc6h] [--force]   # ~100 s for ASTC, incremental, into game/release/
python3 scripts/release.py export     # build if needed, export, add the data pack, thin to arm64, ad-hoc sign -> dist/Courtyard.app
python3 scripts/release.py check      # launch the app through the queue: title, new game, every location; renders/release/app/
python3 scripts/release.py measure    # queue jobs: raw against release (load, video memory, frame times)
.venv/bin/python scripts/release.py compare                       # frame difference raw vs release
```

- ASTC 4x4 HDR is the default (Apple GPUs; ~5 s per layer). BC6H is ~30 % more accurate but
  takes ~50 s per layer (about 2 h for all); use it for Windows/Linux builds.
- Each EXR becomes `release/<path>.gtx` (20-byte header + mip chain, zstd when it pays), each
  depth `.f32` a lossless RGBA8 PNG. `SceneData` uses release data only when
  `release/manifest.json` matches every source file's size and mtime; otherwise it falls back to
  raw with a warning. `--raw` forces raw files.
- `.gdignore` folders are invisible to Godot's export filters, so the app's data is a second pack
  (`game_data.pck`, every location's assets plus characters, npc clips and skill audio, built by `game/scripts/release_build.gd` with PCKPacker) mounted at start.
- Measured (M1 Pro): video memory 1983 → 880 MB, process peak 2.8 → 1.1 GB, tile upload 26–36 →
  7–10 ms, no hitches in the perf check, layer disk 1.5 GB → 0.47 GB; mean error 0.3–0.4 display
  codes, no banding in the darks.
- Export templates for the installed Godot (4.7.2) live in
  `~/Library/Application Support/Godot/export_templates/4.7.2.stable/` (`release.py templates`
  downloads and verifies them from the official GitHub release).
- The release covers every exported location; staleness is per location folder (a changed
  location reads raw EXRs, the others keep release data). `export_presets.cfg` include_filter
  needs `locations/*/data/*`. After a final render: `release.py build` (incremental), `export`,
  `check`. App: about 1.1 GB, each location loads in about 0.5 s plus fades.

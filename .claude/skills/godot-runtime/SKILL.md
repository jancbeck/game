---
name: godot-runtime
description: The Godot 4.7 game of the garrison project (game/) - module map of game/scripts, how the pre-rendered frame is composited live, camera zoom, rain, crows, navigation, interaction, NPC dialogue, audio, debug keys and command-line flags, headless checks, screenshots and the performance log. Use it for any change to game code or shaders, for running or screenshotting the game, measuring frame times, or debugging what the player sees, even if the user only says "the rain looks off" or "it stutters".
---

# Godot runtime

```bash
G=/Applications/Godot.app/Contents/MacOS/Godot
$G --path game                                         # play
$G --path game --audio-driver Dummy -- --no-intro      # silent
$G --path game --headless --audio-driver Dummy -- ...  # no window, no GPU queue needed
```

Windowed runs need the sandbox disabled; run those that measure or screenshot through
`scripts/gpu.py run`. When you start the game for the user, stop it afterwards: a running game
keeps the Mac busy and plays audio in the background.

## How the frame is drawn

`game/config.json` names the data (`data/scene.json`, `data/sounds.json`); `main.gd` wires the
modules.

- The 3D world renders into a linear HDR SubViewport at the window's pixel size; the 16:9 frame
  is letterboxed when the aspect differs (fullscreen too).
- `compositor.gd` draws `base + Σ group × intensity` and writes the frame's depth, so the figure
  and crows hide behind walls. Per pixel it picks the main frame, the wide view (zoom < 1, freed
  after the intro) or the focused hotspot's tile. Tiles refill one fixed texture slot, one layer
  per frame, so a tile never stalls a frame. Intensity is level^1.3 of a curve in `curves.gd`, a
  port of Blender's `anim.py` (same hashes and seeds).
- `view.gd` applies AgX "Punchy" through a baked 3D LUT and the still's post (saturation 0.9,
  bloom, lift/gamma/gain, vignette) in linear light, dividing by 2^exposure first.
  `"post": false` in config.json turns the post off.
- `camera_rig.gd`: one orthographic camera; intro eases 0.5 → 1; an interaction eases to 2 on
  the hotspot's tile and back. It moves only across its own axis so depth stays valid.
- `lights.gd` real-time lights follow their group; `flipbooks.gd` plays flipbooks at their depth.
- `rain.gd` GPU particles with terminal velocity, wind, gusts and depth-tested splashes.
- `crows.gd` / `crow.gd` idle on perches, take off when the figure comes within 3 m.

## Play

- `navigation.gd` bakes a navmesh from `walk.glb` plus stair links and reads each face's
  surface; `portals.gd` takes the figure through tower doors; exits show a title card when the
  target has no export.
- `interaction.gd`: click a walkable surface to walk, the object to interact; Shift-click or
  right-click always interacts; hover glows, Tab outlines every hotspot.
- `player.gd`: the figure (`walk_to`, `stop`, `face`, `palette`); SPEED 1.75 m/s.
- `npc.gd`: people from `data/npcs/<id>.json`: a figure, the conversation, a talking portrait
  (InfiniteTalk frames per line) and a listening loop between lines in `ui.gd`'s dialogue column
  (keys 1–9 pick options). See `npc-pipeline`.
- `audio.gd`: rain bed and fire loop on an "Ambience" bus with a low-pass that follows the zoom,
  footsteps by surface (puddle mask under the figure), clicks, hotspot sounds, doors. No reverb.
  An interior (`"rain": false` in its scene.json) has no rain bed: the fire loop sits at the room's
  own hearth (`config.json` -> `audio.fire_group` lists one light group id per location) and a
  quiet low room tone plays (`audio.room`, level `levels_db.room`, default -26 dB). While that file
  is missing a brown-noise rumble under 200 Hz is made in code.

## Controls, story and state

- Mouse, keyboard and Xbox pad share InputMap actions (`actions.gd`). Pad: left stick walks,
  D-pad or right stick selects the nearest interactable in that direction, A interacts or
  confirms (and skips a line being spoken), B closes, hold LB or X highlights all, Y or Menu
  opens the satchel; in dialogue D-pad up/down picks a response. The mouse cursor (a quill drawn
  in `cursor.gd`) hides while the pad is in use. Nothing is drawn where the player clicks.
- Dialogue is Ink through inkgd (`game/addons/inkgd`, `story.gd`); see `npc-pipeline` for the
  story files, tags and externals. inkgd registers global classes: a fresh checkout needs one
  `Godot --headless --path game --import` (`game.py check` does it).
- Skills: `skills.gd` holds the six skills of `data/skills.json` (id, name, description, colour,
  starting value 1-5; also the named difficulties), the values and every roll made. `journal.gd`
  holds the tasks the story writes (titles in `data/journal.json`). `sheet_ui.gd` is the panel for
  both: the character sheet (`C`, pad View) and the journal (`J`, pad RB), D-pad up/down or arrow
  keys step through skills or scroll; while it is open the dialogue column takes no input
  (`ui.suspended`). The tags, externals and rules the story uses are in `npc-pipeline` (Dialogue).
  Passive lines, check options (tag, chance, lock) and roll lines in the log are `dialogue.gd` and
  `ui.gd`; a roll's dice come from the game seed, the check's key and the attempt number, so a
  loaded save never rerolls.
- `inventory.gd` (satchel, `I`), items in `data/items.json`; `quest.gd` keeps flags and Ink
  variables; F5 quick-saves and F9 quick-loads `user://save.json` (refused during a
  conversation; a location change autosaves). Saves hold Ink state, the skills with their rolls and the journal, so a story edit
  can break an old save.
- Locations: `config.json` `start`; any other location loads
  `locations/<name>/data/scene.json`. An exit or portal with `target`/`to` fades, rebuilds the
  world and places the figure at the door leading back. `"rain": false` in a scene.json turns off
  rain for interiors. NPC JSON `location` and `fallback` decide where a person stands.
- Figures: `player.gd` loads `assets/characters/<model>.glb` (MPFB, AnimationTree blending idle,
  walk, talk; walk playback follows ground speed) and falls back to the procedural figure.

## Figure look

`figure.gdshader` + `figure_look.gd` make the MPFB figures sit in the photograph: matte wool with a
grazing sheen, skin wrap and translucency, a sky rim, hair strands, cloth chroma kept at 70 % with a
white balance (fire light plus the post's lift otherwise turns brown wool red-magenta), lamp
irradiance compressed above a knee of 5, floor bounce and room-indirect terms, baked occlusion in
UV2, and a depth-tested floor shadow (`figure_shadow.gdshader`) from the three strongest lamps.
`lights.gd` feeds each figure its lamps every frame. GLB contract: COLOR_0 is sRGB; TEXCOORD_1 =
(occlusion or hair edge, 1 − kind); shape keys `<clip>_<NN>` (hem fit per walk frame) and
`<clip>` (drape). NPC JSON: `idle_clip`, `talk_clip`. Flags `--npc-walk`, `--swatches`.

## Title, saves and settings

- `menu_ui.gd`: the title (Continue, New game, Load, Settings, Quit) over the live wide view; Esc/B
  at idle opens the pause menu (Resume, Save, Load, Settings, Quit to title, Quit game). Check
  flags and `--no-intro`/`--start=`/`--data=` skip the title.
- New game: archetypes in `data/archetypes.json` (Ledger, Upright, Listener, Level, Custom with a
  12-point budget, each skill 1–5); `main.begin_game(id, build)`.
- `saves.gd`: `user://saves/{auto,quick,slot_1..8}.json` with `meta` (place, latest journal
  entry, time). F5/F9 = quick slot; a location change writes `auto`.
- `settings.gd`, `user://settings.json`: master/voice/ambience/effects volume (buses Master,
  Voice, Ambience, Sfx), text speed (typewriter), auto-advance, fullscreen, mouse/pad hints.
- Inner voices: `# line:<clip>` on a skill line plays `assets/skills/<clip>.wav` on the Voice bus;
  any voice ducks the ambience 8 dB.
- GDScript pitfalls: a static `reload` shadows `Script.reload()`; headless runs never fire
  `frame_post_draw` (no screenshots); warnings are errors, so `:=` from a Variant fails.

## Chapters

`~ end_chapter("<id>")` in Ink (after the lines before it are read) fades to a chapter card from
`data/chapters.json` (title, body), then a page of the player's choices (`summary.lines`: one row
per story variable, text chosen by its value; `summary.checks` lists every roll), then the title.
The save made at the card loads to the card; the title's Continue is disabled for it.
`game.py check` validates chapter ids and row variables.

## Debug keys and flags

| Key / flag | Does |
|------------|------|
| F1 | Proxy edges, walk mesh, stand points, exits |
| F2 | Rain on/off |
| F3 | Frame-time overlay: fps, mean, 1 % low, worst, draw calls, video memory, last hitch |
| Tab | Outline every hotspot |
| `--no-intro` | Start at zoom 1 |
| `--start=<location>` | Start in another location (e.g. `cookhouse`) with its people |
| `--off=rain,flipbooks,crows,background` | Hide parts |
| `--data=<path>` | Load another scene.json |
| `--capture` | Measures the view transform against `reference.png`, frame times, saves check frames to `game/shots/` (window) |
| `--snap` | One screenshot |
| `--clip=rain1\|rain2\|intro\|interact` | Clips under Movie Maker (`--write-movie shots/clip/<n>/f.png --fixed-fps 24`) |
| `--npc-check` | Talks to the first person, saves screenshots |
| `--perf-check` | Loads four tiles and zooms onto each, for `logs/perf.csv` |
| `--playthrough-check` | The whole quest from New game to the chapter card through real clicks, doors and portals; screenshots in `game/shots/playthrough/` (also headless, 4× speed, inside `game.py check`) |
| `--release-check` | Used by `release.py check` in the exported app; `--shots-dir=<abs>` |
| `--menu-check` | Screenshots of title, new game, settings, load, pause, save (scratch saves) |
| `--ui-check` | Satchel, F1 quest panel, pad selection, a pad-highlighted dialogue, the character sheet, the journal, a conversation of skill voices and check options (screenshots) |
| `--char-check` | Figure screenshots at zoom 1 and 2 into `game/shots/chars/` |
| `--raw` | Read raw EXRs even when release data exists |
| `--release-shot=<dir>` | Frozen frames plus frame times, for comparing raw and release |

`game/logs/perf.csv` (not in git) gets one row per 5 s (mean, p99, worst, fps, 1 % low, video
MB) and one per hitch over 50 ms, blamed on the last `perf.mark(event)`. Steady state is about
57–60 fps at 1440p with vsync, video memory ~1.7 GB.

## Checks

`python3 scripts/game.py check` runs `smoke.gd` headless (90 frames) and fails on any script
error. Add a short check for each new system to the smoke test or a `--<name>-check` flag:
something that proves the core behaviour (a save/load round trip, a dialogue choice advancing),
not exhaustive coverage. `systems_check.gd` plays the skill checks and the journal on a fixture
story, `game/tests/checks.ink` (compiled to `checks.json` by `scripts/ink.py`, not part of the
game): `fixture_dialogue(main)` gives a second dialogue on it that draws in the game's column.

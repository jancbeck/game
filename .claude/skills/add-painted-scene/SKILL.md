---
name: add-painted-scene
description: >
  Add a new playable painted location to Ashen Vale (Disco Elysium-style: a
  2D painted backdrop with real-time 3D characters walking on it). Use when
  creating a new scene/area. Covers the calibration-by-screenshot loop and
  the placement decisions that cannot be derived from code — the manifest
  schema itself is documented in scripts/systems/painted_scene.gd.
---

# Adding a painted scene

A scene is one painting + one `data/scenes/<id>.json` manifest + a `.tscn`
that loads it. The manifest field schema lives in the `painted_scene.gd`
header comment — read it there, don't reproduce it. This skill is the
*workflow and the judgment calls*.

> **Pixel-picking helpers.** Every backdrop-pixel coordinate below (walk
> polygon, light `px`, occluder polygons + anchors, `spawn`, NPC `pos`) can be
> read without an external editor:
> - **Human:** open `tools/manifest_picker.html` in a browser, load the
>   backdrop PNG, and click to collect points — it draws a labelled grid + a
>   live overlay and emits a paste-ready manifest fragment.
> - **Headless / agent:** run `node tools/gridshot.mjs art/scenes/<id>.png` to
>   write `<id>_grid.png`, a copy of the backdrop with a labelled 100px
>   coordinate grid burned in; read that image to lift exact pixel coords.
>
> You still make the judgment calls (which floor is walkable, where a prop
> meets the ground); the helpers just spare you the coordinate arithmetic.
> Both are covered by `npm run test:tools` (Playwright) in CI.

## Order of operations

1. **Backdrop** — generate `art/scenes/<id>.png` (see `generate-assets`).
2. **Minimal manifest** — `id`, `backdrop`, a rough `spawn`, and an empty
   `walk_polygon`. Copy `scenes/painted/prison_yard.tscn` to
   `scenes/painted/<id>.tscn` and set `scene_id`. Root node MUST be
   `Node3D` (the script is `extends Node3D`; a `Node2D` root silently hangs
   the engine — see docs/CI.md).
3. **Calibrate the camera BY EYE, via CI screenshots.** There is no way to
   get pitch/fov/distance right analytically — you place characters, render,
   look, adjust. Add a snap of the new scene to `tools/screenshots.gd`, push,
   and read the published frame from the `ci-screenshots` branch (docs/CI.md).
   Nudge `camera.pitch`/`distance` until the ground plane matches the
   painting's perspective (characters stand flat on the flagstones, don't
   float or sink). Typical start: `pitch -42, fov 32, distance 26`.
4. **Character scale** lives in `CharacterRig` (world units), not the
   manifest — a rig is ~1.7u tall. If characters look stubby/giant after the
   camera is right, adjust the rig, not the camera.
5. **Walk polygon** — trace the walkable floor in BACKDROP PIXEL coords
   (open the PNG, read pixel positions of the floor corners). Keep it inside
   the painted ground; exclude walls and props the player shouldn't stand on.
6. **Lights on the painted fires** — one manifest light per visible flame,
   `px` at the flame, `fire: true` for embers + flicker. `px` is projected
   onto the *ground* plane, correct for ground-level fires (braziers) with an
   optional `height` lift. For a flame painted ABOVE the ground (wall torch,
   hanging lantern), add `"wall": true` + `"wall_height"` — the flame pixel is
   then read on a horizontal plane at that height so the light sits at the
   painted flame, not far up the wall. Tune `wall_height` by screenshot
   (start ~3.5). For a fully manual placement, use `"world": [x, y, z]`.
7. **Occluders** (optional) — for foreground props the player can walk
   behind. Each is a polygon of backdrop pixels around the prop plus an
   `anchor` pixel where the prop meets the ground. Pick the anchor at the
   prop's front-most contact point; characters deeper than the anchor get
   hidden. Verify with a screenshot where the character is *half* behind the
   prop — a fully-hidden or fully-visible character proves nothing.
8. **NPCs + dialogue + voice** — add NPC entries (position in backdrop
   pixels, `dialogue` id, `portrait`), author `data/dialogues/<id>.json`, and
   optionally a `voice` per node (see `generate-assets`).

## Verification (required — CI enforces it)

- Extend `test/integration/test_playthrough.gd` with a playthrough that
  walks the new dialogue's branches and asserts the resulting state.
- Extend `tools/smoke_test.gd` to boot the new scene and drive one
  conversation (this is what catches the Node2D/Node3D hang and null refs).
- Add screenshot snaps so the scene is visually reviewed every run.
- Watch CI to green; read the screenshots and tune. Do NOT claim it "looks
  right" from the manifest alone — only from a rendered frame you have read.

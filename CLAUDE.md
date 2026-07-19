# Ashen Vale — Project Instructions

Isometric 3D narrative RPG (Godot 4.5). Gothic-inspired setting, Disco
Elysium-inspired dialogue. Core mechanic: **specialization hardens you** —
every approach you take raises one attribute and permanently reduces the
flexibility of the others; hardened attributes lock dialogue options forever.

## Ground rules (learned the hard way — see docs/POSTMORTEM.md)

1. **CI is the only source of truth for status.** Never write test counts,
   "passing", or "complete" into docs from memory. If you claim it, CI must
   prove it: `gdlint`/`gdformat`, gdUnit4 suites, and the headless smoke test
   (`godot --headless -s tools/smoke_test.gd`).
2. **Everything is authored as text.** Scenes are hand-written `.tscn`,
   content is JSON in `data/`, no editor-GUI-only workflows. If an addon's
   resource format can't be hand-written, generate it via a headless
   `--script` tool run — never hand-serialize engine resources.
3. **No status dashboards, no sprint theater.** The repo state and the PR
   description are the status. Delete stale docs instead of accreting them.
4. **Fix-forward on diagnosed bugs.** A written root-cause without an
   applied fix in the same PR is not allowed.

## Architecture

- `scripts/core/store.gd` (autoload `Store`) — immutable state Dictionary;
  changes only via `dispatch(reducer)`. Never hand out or mutate `_state`.
- `scripts/core/reducers.gd` — pure static reducers + selectors
  (`requirements_met` is the single gatekeeper for option availability).
- `scripts/core/db.gd` (autoload `Db`) — loads all JSON from `data/`.
- `scripts/systems/dialogue_runner.gd` — runs one dialogue graph; applies
  option effects through the store. UI-free, fully unit-tested.
- `scripts/main.gd` — glue: world ↔ runner ↔ UI ↔ store.
- `scripts/systems/painted_scene.gd` + `scripts/world/character_rig.gd` —
  the Disco Elysium-style presentation: a 2D painted backdrop with
  real-time 3D characters walking on it. Scenes are data
  (`data/scenes/*.json`); assets live in `art/`. NPCs are procedural
  `CharacterRig`s; the player is `scripts/world/convict_rig.gd`, a wrapper
  around `art/models/convict.glb` (Blender-built, rigged, idle/walk/talk
  clips) exposing the same interface. Rebuild the GLB locally with
  `blender -b -P tools/build_convict.py` (never in CI; the .glb is
  committed).
- **Presentation is dual.** `scenes/main.tscn` is the original gray-box 3D
  world (procedural capsules, fog, torch pools); `scenes/painted/*.tscn` is
  the painted-backdrop direction new content should use. Both share the same
  store/reducers/dialogue runner. NPCs everywhere are procedural — no
  third-party models, no animation libraries, no retargeting (the pipeline
  that killed the previous prototype). The single sanctioned exception is
  the player: `art/models/convict.glb`, where ONE Blender script owns mesh,
  armature, and animations together, so mismatch is impossible by
  construction. See `docs/PIPELINE.md`.

## Pipeline knowledge (not inferable from code)

- `docs/PIPELINE.md` — why painted-backdrop + 3D actors, the pixel↔ground
  trick, occluder cards, and the known limitations (wall-fire placement,
  no music/SFX).
- `docs/CI.md` — the screenshot review loop and environment traps (proxy
  blocks, the Node2D/Node3D hang, SceneTree failsafe timers).
- Skills: `generate-assets` (backdrops/sprites/portraits/voice via OpenAI,
  with the empirical API findings) and `add-painted-scene` (the
  calibration-by-screenshot authoring workflow).

## Content format (data/)

- `data/quests/*.json`: `{id, title, summary}` — progression lives in
  dialogue effects, not in the quest file.
- `data/dialogues/*.json`: node graphs; option fields `requires` /
  `effects` / `next` / `show_locked`. Valid effect types and requires keys
  are enumerated in `test/unit/test_content_validation.gd` — extend the
  reducers, the validator, and the docs together or CI fails.
- `data/scenes/*.json`: painted-scene manifests (schema in
  `scripts/systems/painted_scene.gd`). Optional `exits`: `[{id, to,
  label, transition, requires}]` — `to` is the destination scene id,
  `requires` reuses the dialogue `requires` schema. Travel is data-driven:
  when an exit's requirements are met, the scene offers it and
  `painted_scene.travel_to` swaps in the destination — no per-scene glue.
- `data/cutscenes/*.json`: scripted set-pieces (schema in
  `scripts/systems/cutscene_runner.gd`) — `{id, scene, timeline: [...]}`.
  Steps: `wait` (seconds), `line` (speaker/text/portrait/seconds narration),
  `walk` (`actor` = `"player"` or an NPC id, `to`/`face` in backdrop pixels),
  `flag`, and `effects` (reuses the dialogue `effects` schema). The runner
  applies store steps through `dispatch`; `painted_scene.play_cutscene`
  performs the visual steps. Recognised step types are enumerated in
  `test/unit/test_content_validation.gd` — extend the runner, the validator,
  and the docs together or CI fails.
- `data/chapters.json`: the ordered act state machine —
  `{id, acts: [{id, title, summary, scene, requires}]}`. `Reducers.current_act`
  is the furthest act whose `requires` is met, scanning from act 1 and
  stopping at the first locked act (linear progression). The validator
  checks every `act.scene` and every `exit.to` resolves to a real manifest.

## Verification workflow

Before any push: `gdformat scripts/ test/ tools/ && gdlint scripts/ test/
tools/` locally (pip `gdtoolkit==4.*`). Godot cannot run in this dev
sandbox — full runtime verification (smoke test + gdUnit4) happens in CI;
watch the PR until green and fix failures immediately.
New content must extend `test/integration/test_playthrough.gd` with a
playthrough that exercises it.

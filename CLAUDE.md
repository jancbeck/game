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
- Characters are procedural primitives (no skeletal animation, no rigs,
  no imported models). Mood comes from lighting/fog, not asset fidelity.

## Content format (data/)

- `data/quests/*.json`: `{id, title, summary}` — progression lives in
  dialogue effects, not in the quest file.
- `data/dialogues/*.json`: node graphs; option fields `requires` /
  `effects` / `next` / `show_locked`. Valid effect types and requires keys
  are enumerated in `test/unit/test_content_validation.gd` — extend the
  reducers, the validator, and the docs together or CI fails.

## Verification workflow

Before any push: `gdformat scripts/ test/ tools/ && gdlint scripts/ test/
tools/` locally (pip `gdtoolkit==4.*`). Godot cannot run in this dev
sandbox — full runtime verification (smoke test + gdUnit4) happens in CI;
watch the PR until green and fix failures immediately.
New content must extend `test/integration/test_playthrough.gd` with a
playthrough that exercises it.

# CI, verification, and environment gotchas

Operational knowledge that is not visible in `.github/workflows/ci.yml` or
the source — the traps this project has already hit, and the feedback loop
that lets a headless agent actually see the game.

## The screenshot feedback loop (how the game gets "seen")

Godot cannot render in the dev sandbox, and `--headless` produces no frames.
So visual review is a CI job:

- `tools/screenshots.gd` runs under **Xvfb + Mesa/llvmpipe** (software GL) —
  `xvfb-run -a godot --rendering-driver opengl3`. This renders real frames
  with lighting/shadows/particles on a machine with no GPU.
- The job force-pushes the PNGs to a dedicated **`ci-screenshots` branch**.
  An agent then `git fetch`es that branch, `Read`s the PNGs, and judges them
  — this is the only way to review look-and-feel from here.
- The headless smoke test (`tools/smoke_test.gd`) uses plain `--headless`
  (no renderer) because it only exercises logic/scene-tree wiring, not
  pixels.

Rule: never claim a scene "looks right" from the manifest. Claim it only from
a rendered frame you have actually read.

## Traps already hit (don't repeat)

- **`gdparse`/`gdlint` do not do full type resolution.** A scene whose root
  node type mismatches its script's `extends` (e.g. a `Node2D` root with an
  `extends Node3D` script) passes every static check and then makes the
  ENGINE refuse to attach the script at runtime. Only Godot itself catches
  it. When you change a script's base class, update every `.tscn` that
  instances it.
- **A SceneTree tool script that errors mid-run hangs forever.** If `_run()`
  aborts on a script error, the main loop keeps spinning and `quit()` is
  never reached — the job wedges until its timeout (10 min wasted). Every
  `extends SceneTree` tool (`smoke_test.gd`, `screenshots.gd`) arms a
  failsafe `create_timer(...).timeout` that force-quits regardless. Keep it.
- **GitHub release binaries are blocked by the sandbox proxy** (HTTP 403 with
  a "GitHub access not enabled" JSON body). You cannot `curl` a Godot release
  zip locally — Godot is installed by the CI runner instead. PyPI and npm
  *do* bypass the proxy, so `pip install "gdtoolkit==4.*"` works locally for
  `gdparse`/`gdlint`/`gdformat`.

## What each CI stage catches

Ordered cheapest-first; a failure early skips the expensive stages.

1. **Lint & format + JSON validation** — `gdparse` (syntax), `gdlint`
   (style/order), `gdformat --check`, and a JSON well-formedness pass over
   `data/`. Catches the bulk of mistakes in seconds.
2. **Headless boot & playthrough** — boots the real scenes and drives real
   conversations through the actual UI code path. Catches null refs, the
   type-mismatch hang, broken wiring — things logic tests miss.
3. **gdUnit4 tests** — unit suites (reducers, dialogue runner, save/load) and
   the content-graph validator, plus the integration playthroughs of the
   real shipped story.
4. **Render screenshots** — the visual review artifacts described above.

## Local pre-push checklist

```sh
pip install "gdtoolkit==4.*"
gdformat scripts/ test/ tools/ && gdlint scripts/ test/ tools/
gdparse $(find scripts test tools -name '*.gd')
python3 -c "import json,pathlib; [json.loads(p.read_text()) for p in pathlib.Path('data').rglob('*.json')]"
```

Everything above the screenshot stage can be reproduced locally except the
Godot-runtime steps; push and watch CI for those.

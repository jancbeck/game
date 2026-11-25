---
name: agent-workflow
description: How to run a round on the garrison game with several agents in parallel - private git worktrees, agent briefs, the single-GPU queue (scripts/gpu.py), render tiers (check, preview, draft, final), hand-back diffs, merging, signed commits and timings. Use this whenever you start or coordinate a round, spawn an agent for scene/runtime/character work, render anything with Blender or windowed Godot, or merge an agent's diff, even if the user only says "do the next round" or "render this".
---

# Running a round

The main session coordinates. Agents work in private copies and hand back diffs; the
coordinator merges, checks and commits. One GPU: renders queue, never run in parallel.

## Start a round

1. Read `AGENTS.md` and `git log -3`.
2. Split the work into independent pieces with separate files (scene / runtime / characters /
   release are typical). Two agents must not edit the same file; name the files each may touch.
3. Make a worktree per agent and link the ignored data folders:

```bash
n=r23-scene; d=/tmp/claude-501/$n
git worktree add -q -b $n "$d" HEAD
for p in game/assets game/build scene/textures; do rm -rf "${d:?}/$p" && ln -s "$PWD/$p" "$d/$p"; done
```

   The links are shared with the main tree: agents add new files there, never overwrite.
4. Brief each agent like a peer: goal, files it owns, what to read (this skill and the topic
   skill), what done looks like, what to report. Opus for open-ended work.

## Rules for agents

- Write only in your copy. Keep to the files your task names; do not move or rename others.
- Shared helpers go in `scene/planlib.py`, `scene/kit.py` or `scene/game_frame.py`; per-place
  tables go in `locations/<name>/`.
- Run `python3 scripts/game.py check` before starting and before handing back (~1 min, no GPU).
- Hand back:

```bash
python3 scripts/game.py check
git add -A -- . ':!game/assets' ':!game/build' ':!scene/textures'; git diff --cached HEAD > renders/<task>.diff
```

  Exclude every symlinked data folder from `git add`, and join with `;`: git exits 1 on the
  "ignored path" hint and `&&` would skip the diff. `git add` in a worktree needs the sandbox off.

  Report the diff path, moved/deleted files, commands run, measurements, image paths.

## Render tiers

Pick the cheapest tier that answers the question.

| Tier | Command | Time | Use |
|------|---------|------|-----|
| check | `scripts/game.py check` | ~1 min, no GPU | Any change: builds, data valid, game runs headless |
| preview | `scripts/game.py preview [--view eye] [--percent 25]` | 1–2 min | Look at a change in EEVEE |
| draft | `scripts/game.py draft <step>` | 1.5–5 min/step | One export step at low samples into `renders/draft/` |
| final | `scripts/game.py final [step]` | up to 2 h | The real export; only stale steps run |

Every Blender step builds the scene first (~1 min). `final` runs only when the user says so,
usually overnight; agents never run it. After a merge whose export matches the sources,
`scripts/game.py adopt` marks all steps up to date.

## The GPU queue

```bash
python3 scripts/gpu.py run --name <location>/<what> -- <command ...>
python3 scripts/gpu.py status
python3 scripts/gpu.py break      # remove a stale lock by hand
```

- Jobs run one at a time in submission order; `game.py`, `iterate.sh`, `orbit.sh` already queue.
  Log: `/tmp/claude-<uid>/gpu-queue/timings.csv`.
- The lock is `/tmp/claude-<uid>/gpu.lock` (mkdir). A dead job's lock clears after its
  heartbeat stops for 2 min.
- Queue Blender renders, windowed Godot runs, MLX models (voice, sound) and anything you time.
  Headless Godot and scene builds without a render need no queue.
- Blender with Metal and windowed Godot need the sandbox disabled. Never pass `--save-blend`.
- Do not measure frame or render times while another job runs.

## Merge and commit

```bash
git apply --3way /tmp/claude-501/<task>/renders/<task>.diff
python3 scripts/game.py check
git add -A && git commit -m "<what changed, plainly>"
git worktree remove /tmp/claude-501/<task> && git branch -D <task>
```

Commits are signed via Secretive; "agent refused operation" means the Mac is locked — ask the
user to unlock, never bypass signing. No attribution lines. Never push.

## Timings

`timings.csv` logs slow steps: `game,<location>/<tier>/<step>,estimate,actual,finished`.
`game.py` appends automatically; add your own slow steps in the same format.

## End of a round

Look at the result in the game (screenshots through the queue), commit, update the project
memory, and propose what next round should do towards a Disco Elysium-sized game.

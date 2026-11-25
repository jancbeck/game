# Garrison: a pre-rendered point-and-click RPG

A rainy garrison castle at blue hour, built procedurally in Blender 5.2, rendered offline in
Cycles and played in Godot 4.7 as pre-rendered locations with live characters, light, rain and
sound on top. The long-term goal is a story-driven RPG of Disco Elysium scale and immersion
(10–20 hours): characters, dialogue and choices matter more than new tech.

This file holds the goal, the art direction, the rules and how to work. [ENGINE.md](ENGINE.md)
separates the reusable engine from the garrison content; [POSTMORTEM.md](POSTMORTEM.md) holds
the learnings of the proof of concept. Everything about *how
to do a task* is in a project skill (`.claude/skills/`, table at the end).

## The game

- **Form.** Fixed orthographic camera per location (elevation 38°, yaw 11°, 2560 × 1440 frame).
  The static set is a Cycles render split into light groups and composited live; characters,
  crows, rain, fire and smoke run in real time on top, against invisible proxy geometry and the
  frame's depth. Zoom goes from 0.5 (wide intro) to 2 (close on an object).
- **Storytelling.** Disco Elysium style: a dialogue column with a talking portrait per line
  (InfiniteTalk clips of an AI portrait with a designed or cloned voice). No 3D lip sync.
  Six skills (`game/data/skills.json`) speak as inner voices (passive checks), gate responses
  with white and red dice checks, and fill a journal; C opens the character sheet, J the journal.
  The Ink tags and externals are in `npc-pipeline`.
- **Locations.** One folder per place in `locations/<name>/`. Today: the courtyard, and the
  cookhouse interior. Later: a village, a mine, a river port.
- **Input.** Mouse, and an Xbox controller (left stick walks, the D-pad cycles interactables).

## What the place is

A garrison outpost guarding a road north, not a royal seat. Everything has a use a garrison
needs and the layout works as a working place: barracks and guardroom, stable, cookhouse with
chimney, armoury, latrine and garderobes, well, forge, stores, a gate passage that leads
somewhere, guard posts, tower doors onto the wall-walks and stairs to reach them. On the south
the rock ends in a 10 m cliff with a parapet; the commander lives in a residential stone tower
(Wohnturm) on the cliff edge at the south-west.

## Art direction

- **Time.** Post-sunset blue hour under rain clouds, not pitch-black night. The whole castle
  reads in dim sky light; fire light stays physically plausible.
- **Rain.** Everything is wet, puddles reflect the fire, rain falls.
- **Gritty and lived-in.** Weathered, washed-out stone with grime and moss; mud in the joints;
  clutter (straw, debris, tools, sacks); wear where people walk and work.
- **Photoreal.** Path-traced light, scanned materials, no painterly filter. Muted palette:
  cool blue-grey night, warm firelight pools, olive-brown mud.
- **Scale.** Every prop fits a 1.8 m person. Check new elements against a scale figure.
- **Reference.** `ref/courtyard.webp` (an AI image) is mood and style, not a blueprint. Where it
  makes no physical sense, build what a real castle would be.

## Consistency rules

Apply them to every new or moved element.

- **Light.** A flame burns only where someone is on duty or working, and only under a roof or
  an arch; nothing burns unattended in the open. Lanterns have horn panes: dim amber, 1–2 m reach.
- **Floors.** Towers have floors at 0, 3 and 6 m (wall-walk level) and a roof platform at 9 m.
  Windows sit 1.0–1.2 m above a floor; doors sit on a floor.
- **Circulation.** The wall-walk is continuous; every stair, door and latrine is reachable.
- **Use and weather.** Iron, shields and food are kept dry. Fire is kept away from straw and hay.
- **Age.** Decades of use on a small budget: weeds on wall tops, moss under spouts,
  mismatched repairs, worn thresholds.
- **One era.** Every building must read as the same century as the rest.

Standing review checks (an outside critic repeats these): exposure and value structure at the
main camera, uniform masonry, anything clean or saturated, empty areas. Features that do not
read at the main camera count as missing.

## Taste

- **No synthetic reverb** on voices, rain or effects ("a church", "a microphone in a barrel").
  The courtyard is open to the sky. At most a 0.3 s soft ambience 18 dB under a voice.
- **Portraits close on the face**: head and a little shoulder, the face filling the square.
- **No click marker** or other UI where the player clicked; a period cursor is fine.
- Sound effects come from Stable Audio 3. There is no music model in the workflow.

## How the user wants to work

- One round at a time, with everything for that round in it. Within a round, Claude drives
  autonomously and reports once at the end. Each round ends with a proposal of what to improve
  next towards the full game.
- Use agents in parallel for independent work; the main session coordinates and merges.
- Do not hold work for an answer it does not depend on.
- Final Cycles renders (up to 2 h) run only when the user says so, overnight. Use preview and
  draft tiers while working.
- Log estimate against actual time in `timings.csv`.
- Commits are signed (Secretive, Secure Enclave). If signing fails with "agent refused
  operation", the Mac is locked: ask the user to unlock it. No attribution lines. Never push.

## Quick start

```bash
python3 scripts/fetch_textures.py      # once per machine: Poly Haven scans into scene/textures/
python3 scripts/game.py check          # build, validate the game data, run the game headless (~1 min)
python3 scripts/game.py preview        # EEVEE still -> renders/preview/
/Applications/Godot.app/Contents/MacOS/Godot --path game
```

Blender (Metal) and windowed Godot do not run inside the Claude Code sandbox. Every GPU job
goes through `scripts/gpu.py run`.

## Skills

| Skill | Use it for |
|-------|------------|
| `agent-workflow` | Running a round: worktrees, briefs, GPU queue, render tiers, hand-back, merge, commit |
| `scene-build` | The Blender scene: locations, plan, props, materials, terrain, look, previews, videos |
| `game-export` | Blender → Godot export steps, `game.py` tiers and stale steps, the data contract |
| `godot-runtime` | The Godot game code: modules, debug keys and flags, checks, performance |
| `story-bible` | The world, people, arc, tone, inner voices and writing rules; read before writing any line |
| `npc-pipeline` | A new character: portrait, designed or cloned voice, lines, talking clips, dialogue |
| `sound-effects` | Stable Audio 3 sound effects, footsteps, normalisation, `sounds.json` |

## Stack

Blender 5.2 (`/Applications/Blender.app`), Godot 4.7 (`/Applications/Godot.app`), Python 3.13
venv at `.venv` via uv. `scripts/game.py` and `scripts/gpu.py` need only the standard library.
Galley v2 tools (`~/workspace/projects/galley-v2/tools`) provide voices (`say`), sound effects
(`sfx`) and audio checks (`listen`). `huggingface_hub` fails inside the sandbox (system TLS):
download with `curl` from `huggingface.co/<repo>/resolve/main/<file>` or run outside it.

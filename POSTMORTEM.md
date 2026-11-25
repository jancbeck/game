# Post-mortem: the garrison proof of concept

This proof of concept covers rounds 1–25 and the final render at commit `0ea2f11`. It asked one
question: can one person working with Claude build a pre-rendered, voiced RPG of Disco Elysium
style? The answer is yes. The pipeline from an art brief to a playable, voiced location works.
The bottlenecks are story and art direction, then voice quality and sound, and only after
those, code.

The reusable engine and the feature recipes are in [ENGINE.md](ENGINE.md). This file covers
what worked, what did not, and what to change in the next project.

## What worked

- **The pre-rendered look.** A path-traced Cycles frame, split into light groups and
  composited live with depth, gives a photoreal set at a 2D cost. Live fire light, rain, crows
  and smoke on top make the picture feel alive. Crows were the best small detail.
- **Talking portraits.** InfiniteTalk clips of a generated portrait, with a designed voice, are
  the strongest part of the conversations.
- **Designed voices.** A voice designed from a text description (Qwen3-TTS VoiceDesign) gives a
  distinct character without cloning a real person.
- **Disco Elysium systems in Ink:** passive skill voices, white and red checks, a journal, an
  inventory, chapters and a summary of choices. The story file holds the whole design, and the
  engine only reads tags.
- **Everything is data.** Locations, people, items, sounds and chapters are JSON or Ink files.
  A new person is a recipe and one command.
- **Checks that play the game.** `--playthrough-check` plays the quest through real clicks and
  doors, so a broken quest fails `game.py check`.
- **The single-GPU queue.** `scripts/gpu.py` serialised all Blender, Godot and MLX jobs, and
  timings were logged per step.

## What did not work

### Layout followed the reference image, not a plan

The courtyard grew from an AI reference image, and changes came one request at a time ("move
the palas", "a tower here"). Nobody owned the function of the place: where the stable is, what
the player sees from each spot, where the exits lead. The playtest shows the result. Marl
talks about a stable the player cannot recognise. The building at the bottom is cut off. Wall
joints stayed wrong for 20 rounds.

**Next time:** write a location brief before any geometry. It names every building, what it is
for, what the camera must show, the walk routes and the exits. Lock it, then build. A change to
the brief is a new revision of the brief, not a one-line request.

### Checks proved that code runs, not that the game is good

`game.py check` caught script errors and broken quests. It did not catch a slow frame on a 5K
screen, rain that looks like snow, a shadow that does not move with the body, or a crow sound
with a car in it. I reviewed my own renders with the eyes of their author. I fixed what you or
a reviewer named, but I did not act as the person responsible for shipping.

**Next time:**
- A written acceptance checklist per area (look, motion, sound, performance, story continuity).
  A separate QA agent runs it in a real window at the target resolution and files bugs.
- Golden screenshots per location and camera. A diff over a threshold needs a human look.
- A bug log in the repository (`BUGS.md` or issues) that rounds work through first. A round is
  not done while it has open bugs of its own.
- Performance targets on the real target screen: 60 fps at 5K fullscreen on an M1 Pro. The
  measured 57–60 fps was at 1440p windowed.

### Automatic audio picking

Stable Audio 3 made several takes per sound, and a script picked the take by loudness and
timbre statistics. Some picks are bad: the crow call has a low rumble like a passing car, and
footstep surfaces are mixed up. Generated sound effects also lack the weight of a designed
sound library.

**Next time:**
- Your ear decides on audio. I prepare a contact sheet with 3–5 takes per sound, and you pick.
- Automatic filters only reject takes: energy below 80 Hz on a bird call, broadband noise
  (spectral flatness), clipping, and a CLAP text-to-audio score under a threshold. They never
  choose a take.
- Start from a recorded library and use generation only for gaps (see "Sound sources").

### Figures

MPFB humans with CMU motion capture are good enough for a demo, not for the photograph. The
shoulders sit high, the arms swing too far forward and the hands look large, probably from the
retarget rest pose and MPFB proportions. Marl's tunic hem reads as a skirt. The live figure is
the weakest part next to the set.

## Playtest findings and their causes

Your playtest on 2026-11-25 found the following. The causes come from the code.

| Finding | Cause | Fix |
|---------|-------|-----|
| 10–15 fps fullscreen on the Studio Display | The 3D SubViewport renders at the window's pixel size: 5K is 14.7 Mpx, 4× the 1440p where 60 fps was measured. The compositor reads float textures for every pixel. | Render at a fixed internal resolution (1440p or 4K) and scale up. Test at the target screen. |
| Rain looks like snow | The fall speed is right (7–9 m/s), but at zoom 1 the drops are drawn short and the 38° camera shortens them more. | Draw each drop as a streak as long as its travel during a 1/48 s shutter. |
| Shadow does not follow the body | The floor shadow is a capsule projected from up to three lamps (`figure_shadow.gdshader`), not the skinned mesh. | Project the skinned mesh, or a few capsules per limb. |
| Shadows pass through solid objects | The shadow quad is depth-tested against the frame, so it draws on every visible floor pixel. It does not test whether a prop stands between the lamp and the floor. | Stop the shadow where a proxy hull lies between the lamp and the floor, or cast shadow maps against the proxy geometry. |
| People get a label but no outline | The outline comes from the pre-rendered id mask. Live figures are not in that mask. | Draw a screen-space outline of the figure's mesh. |
| A/B sometimes do nothing in menus | The menu relies on Godot focus, and a mouse hover moves focus (`mouse_entered → grab_focus`). When no button has focus, A has nothing to press. | When pad input arrives and nothing has focus, give focus back to the first button. Add a menu test that uses only the pad. |
| Walking into a door teleports you | A portal end leading to another location triggers on contact. | Make it a setting: walk-through or confirm. Default to confirm with A or a click. |
| The camera does not follow the player | The camera is fixed, and only an interaction zooms it. The frame is exactly the screen. | Render the frame larger than the screen and pan within it when the player nears an edge region. |
| Cookhouse smoke is cut off and does not seem to move | The smoke flipbook is clipped at its tile bounds. | Larger flipbook bounds, and a check that it animates. |
| SE wall overexposed, cookhouse corner black | The light balance was checked against the reference, not as values in the frame. | Exposure check per zone: a histogram per region with limits. |
| Zoom at 2× looks softer | Tiles stream in one layer per frame. Until all have arrived, the wide frame shows scaled up. | Preload the tiles near the player. |
| Hard to find the stable | Layout and look texts were written apart. | The location brief (see above). The playthrough check should also confirm that every place a line mentions is a visible hotspot. |
| Mostly read, few lines voiced | Only portrait lines and inner voices are voiced. Narration and the player's options are text. | A story decision, not a bug. |

## Sound sources

Recorded libraries that allow use in a commercial game:

| Source | Licence | Notes |
|--------|---------|-------|
| [Sonniss GDC Game Audio Bundle](https://sonniss.com/gameaudiogdc) | Royalty-free, commercial use, no attribution (confirm on the bundle's licence page) | Professional recordings, a new bundle each year since 2015, tens of GB each. The best free source for weather, footsteps, birds, doors and fire. |
| [Freesound](https://freesound.org) | Per sound: CC0, CC-BY or CC-BY-NC | Filter by CC0 or CC-BY, never NC. Keep a credits file. |
| [Pixabay sound effects](https://pixabay.com/sound-effects/) | Pixabay content licence: commercial use, no attribution | Variable quality. |
| [Kenney audio](https://kenney.nl/assets/category:Audio) | CC0 | UI clicks and simple game sounds. |
| BBC Sound Effects | RemArc: non-commercial only | Do not use in a game that is sold. |

Recommended split:
- Ambiences, footsteps, weather, fire, animals and doors from Sonniss and CC0 Freesound,
  layered and levelled by script.
- Stable Audio only for sounds no library has.
- Your ear picks the takes on a contact sheet.

## Orchestration: what I learned about agents

- **Parallel agents in private worktrees, each owning named files, worked.** Three or four
  agents per round (scene, runtime, characters, release) rarely blocked each other. Conflicts
  happened in shared hub files: `main.gd`, `project.godot`, `scene_data.gd`, `game.py`, and the
  Ink entry file. Give each module a registration file it owns, so agents add files instead of
  editing a hub.
- **Fresh agents with a good brief worked.** The skills carried the context: a fresh agent read
  the skill, did the work and handed back a diff, and ended. I continued an agent only for
  follow-ups on its own diff. Long-lived context belongs in the repository's documents, not in
  a session.
- **Generalists with topic skills, not fixed specialists.** One model type with the right skill
  loaded did scene, runtime or character work equally well. The skill is the specialist.
- **Strong model for open work, cheap model for housekeeping.** Opus for layout, look and
  systems; Sonnet for renames, data entry and doc sync.
- **Sequence when work shares a contract.** Export-format changes and the runtime that reads
  them had to go in order: contract first, then both sides. Parallel work on both sides of a
  contract cost a merge round each time.
- **The coordinator should not build.** When I built layout myself, I also judged it myself.
  Next time the coordinator writes briefs, merges and runs acceptance with a separate QA agent.
- **Reviewers find what builders miss.** An outside critic with a fixed checklist found wall
  joints and empty areas that three build rounds missed. Make that review a standing step in
  every round, not an occasional one.
- **One GPU queue, renders overnight.** Waiting for renders cost more time than any bug.
  Preview tiers (EEVEE, quarter resolution) answer most questions.

## A code base that follows art direction

You want to change direction ("move the stable", "make it dawn") without new bugs. The rules
for that:

1. **Direction lives in data, never in code.** A location is a brief, a plan and tables. Code
   reads them by contract. A prop that places itself from plan keys (`age_dressing`,
   `west_ditch`) breaks this: every prop takes its position from the plan.
2. **One contract file per seam**, with a validator: plan → Blender, export → Godot, story →
   engine (tags, externals), character recipe → pipeline. `game.py check` validates each one.
3. **Every location-specific branch in shared code is a bug.** `terrain.py`, `game_walk.py`
   and `orbit_audio.py` still know the courtyard.
4. **Each kind of check runs automatically:** data valid, game runs, quest plays, screenshots
   match goldens, frame time at the target resolution, every story place is a hotspot.
5. **A brief per revision.** A large change starts with an edited brief that you approve, then
   the build follows it. The brief, not the conversation, is the source of truth.

## What I would do differently from day one

1. Write the world, story outline and location briefs before geometry.
2. Set the target hardware and screen, and measure performance there from round 1.
3. Make the QA agent and its checklist part of the round from round 1.
4. Keep a bug log in the repository and work through it before new features.
5. Have you approve audio and character art; automate the rest.
6. Split engine and content from the start (see [ENGINE.md](ENGINE.md)).

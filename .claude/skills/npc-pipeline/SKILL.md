---
name: npc-pipeline
description: Create or extend a speaking character for the garrison game - gpt-image portrait framed on the face, a voice (designed from a text description with Qwen3-TTS VoiceDesign, or cloned) voiced line by line with galley-v2 tools/say, InfiniteTalk talking-head clips on RunPod's public endpoint, the listening idle loop, the voice room treatment, JPG frame sequences, the 3D figure recipe, and the Ink dialogue and data/npcs JSON. Use it whenever the user wants a new NPC, new or changed dialogue lines, a voice, a portrait, or talking clips, even if they only say "add the cook" or "Marl needs a new line".
---

# Characters

A character is a folder `characters/<id>/` (sources: portraits, `lines.txt`, voice takes,
clips, `recipe.json`) plus the game copies in `game/assets/npcs/<id>/` and the person in
`game/data/npcs/<id>.json`. Wavs and mp4s under `characters/` are not in git.

Examples: `characters/marl/` (cloned voice: Leonard from Galley v2), `characters/hedda/`
(designed voice).

## Taste

- Portraits close on the face: head and a little shoulder, the face filling most of the square.
  The portrait is stamp-sized in the dialogue column and InfiniteTalk spends its 480p on what
  is in frame.
- Voices dry. The only treatment is `scripts/voice_room.py`: a 0.3 s soft ambience 18 dB under
  the voice. No reverb.
- Give each person a voice with character: rhythm, accent, texture. Memorable beats neutral.

## One command

`characters/<id>/character.json` is the recipe (voice, line files, portrait, InfiniteTalk
prompts, face crop). After the portrait and voice exist:

```bash
python3 scripts/gpu.py run --name voice/<id> -- python3 scripts/character.py <id> voice
python3 scripts/character.py <id> pick clips game
```

`voice` renders 3 takes per line (two lines per model load, one when a pair overflows Drama 3's
context); `pick` copies the best passing take per line to `final/line_NN.wav` (or shortens long
pauses of a take that failed only on silence) and never overwrites a pick made by hand; `clips`
runs InfiniteTalk for new lines plus the idle loop; `game` writes `game/assets/npcs/<id>/`.
The steps below are what it does, for when a step needs doing by hand.

## Steps

1. **Portrait** (3 candidates, pick one):

```bash
python3 ~/.claude/skills/gpt-image/scripts/gpt_image.py generations --model gpt-image-2.5-sunburst \
  --size 1024x1024 --n 3 --prompt "<photoreal close portrait, face filling the frame, ...>" \
  --output characters/<id>/portrait-{index}.png
```

2. **Voice.** Either clone an existing voice (`say-voices.json` in galley-v2 tools), or design
   one from a description:

```bash
~/workspace/resources/voicedesign/.venv/bin/python characters/<id>/design_voice.py characters/<id>/design --takes 2
```

   `design_voice.py` (copy `characters/hedda/design_voice.py`) runs Qwen3-TTS-12Hz-1.7B
   VoiceDesign (mlx-audio, Apache 2.0) on a description per candidate and a reference
   transcript. Pick a take by ear with the user, clean it with Sidon, and register it as a
   `say` voice (reference wav + exact transcript). Run through `scripts/gpu.py run`.

3. **Lines.** `characters/<id>/lines.txt` is a `say` batch, one line per row, Drama 3 tags in
   brackets (`[dry, amused]`, `[break]`). Render 3 takes per line; `say` checks length,
   silences, words (whisper) and speaker similarity:

```bash
~/workspace/projects/galley-v2/tools/say --batch characters/<id>/lines.txt --takes 3 --out characters/<id>/voice
```

   About one take in six breaks; a line opening with a two-word sentence often stops early —
   reword it. Pick passing takes by ear into `characters/<id>/final/line_NN.wav`.

4. **Talking clips** on RunPod's public InfiniteTalk endpoint (480p, ~2 min, $0.25 per clip,
   inline data URLs; needs `RUNPOD_API_KEY`, never print it; never rent pods):

```bash
python3 scripts/infinitetalk.py <portrait.jpg> <line.wav> <clip.mp4> --prompt "<who, mood>"
python3 scripts/infinitetalk.py <portrait.jpg> <8 s silence.wav> <idle.mp4> --prompt "... listening, mouth closed, small nods ..."
```

   Make the idle loop seamless by cross-fading its last second into its start.

5. **Game copies:**

```bash
<blender python> scripts/voice_room.py characters/<id>/final/line_NN.wav game/assets/npcs/<id>/line_NN.wav
ffmpeg -i <clip.mp4> -vf "crop=<face square>,scale=320:320" -q:v 3 game/assets/npcs/<id>/line_NN/%04d.jpg
```

   Godot plays only Theora video and this ffmpeg has no Theora encoder, so clips ship as 320 px
   JPG frames at 25 fps (`idle/` for the loop) plus `portrait.jpg`. Marl's crop of the 624 px
   clip is `crop=340:340:142:40`.

6. **The person** in `game/data/npcs/<id>.json`: name, location, position/face/stand (Godot
   metres), model or palette for the 3D figure, `assets`, `portrait`, `fps`, and the dialogue
   (Ink knot or the node tree). A line binds to its clip by id (`line_NN`).

## Dialogue

The story is Ink in `game/data/story/` (`main.ink` holds variables and externals and includes
one file per person plus `quest.ink`). Entry knots: `talk_<npc id>` and `look_<hotspot id>` (runs
instead of a hotspot's static text). Tags: `# line:line_NN` plays the clip, `# speaker:<id>` or
`# speaker:narrator`. Externals: `give_item`, `take_item`, `has_item`, `set_flag`, `get_flag`,
`play_line`, `roll`, `skill_value`, `skill_add`. Items are in `game/data/items.json`. Compile after
every edit: `python3 scripts/ink.py` (inklecate from the official ink release, at
`~/.cache/inklecate/inklecate`); `game.py check` fails on a stale `main.json`.

### Skills, checks and the journal

The six skills are in `game/data/skills.json`: `perception` (Sentry's Eye), `empathy` (Folk
Sense), `authority` (Bearing), `logic` (Tally), `composure` (Backbone) and `stonework` (The Rock,
the old castle's voice). The story names a skill by its id. A check is two six-sided dice plus the
skill against a difficulty; two sixes always succeed, two ones always fail. A difficulty is a
number or a name: Trivial 6, Easy 8, Medium 10, Challenging 12, Formidable 13, Legendary 14,
Heroic 15, Godly 16, Impossible 18.

**A skill speaks** (passive check). Tags on a line of text:

```ink
The mortar here is newer than the wall around it. # skill:perception # passive:10
The wall remembers a hard winter. # skill:stonework # passive:challenging
He is not telling you everything. # skill:empathy
```

With `passive:` the line shows only when skill value + 6 reaches the number (no dice); otherwise
it is not there at all. The log reads `SENTRY'S EYE [Medium: Success] — text` in the skill's
colour (the bracket names the difficulty the number falls in). Without `passive:` the skill always
speaks. The line is unvoiced; `# line:<clip>` on it plays `game/assets/skills/<id>/<clip>.wav`.

**A choice is a check.** The check is a tag inside the choice's brackets, and the body of the choice
makes the roll with the external `roll(skill, difficulty, kind)`, which answers true or false:

```ink
+ [Press him until he gives way. #check:authority:12:white] -> press
+ [Order him to open the stores. #check:authority:13:red] -> order

=== press ===
{ roll("authority", 12, "white"): He gives way. | He does not. }
-> hub
```

`#check:<skill>:<difficulty>:<white|red>[:<flag>]`. The option shows `[Bearing · Challenging 12 · 17%]`
(white for a white check, red for a red one), the roll goes into the log (`BEARING [Challenging 12:
Failure] — Rolled 4 + 3, plus 2 = 9 against 12.`). The `roll(...)` arguments must match the tag. A
result is kept in the save under the knot of the choice, the skill, the difficulty and the kind, so
give two checks of one knot different difficulties or kinds.

- **white**: after a failure the option is locked (greyed, struck through, with the reason in its
  tag) until the skill has risen (`skill_add`) or the flag named last in the tag has been set since the
  failure (a story variable or `set_flag`); then it is rolled again.
- **red**: made once. A failure locks the option for good.
- A passed check stays passed; asking again returns the same result without dice.
- `roll` may also be called in plain text without a tagged choice; its result is kept under the
  knot, and a failed white one is retried only when the skill has risen.

`skill_value("logic")` answers the current value (for conditions); `skill_add("logic", 1)` raises a
skill and shows a notice.

**The journal.** `# journal:<task>:<text>` on a line adds the task or replaces its text, and
`# journal_done:<task>` closes it. The tag may stand on a line of its own above a text or above the
choices. A notice shows the change; the J panel lists open tasks, then done ones, each with its
latest text. The task's title is `game/data/journal.json` -> `quests.<task>.title`; without one the
task id is shown.

Never reuse words of the voice reference in a line: Drama 3 copies them. A line that opens with a
two-word sentence ("Linen. Greasy linen.") often breaks: reword it.

## 3D figure

The walking figure is an MPFB human with CMU mocap (walk, idle, talk), built from
`characters/<id>/recipe.json` (body sliders, height, skin, procedural garments and colours):

```bash
python3 scripts/fetch_character_assets.py      # once: MPFB + CC0 assets + CMU BVH into characters/vendor/
python3 scripts/make_character.py <id> [--preview]   # Blender, sandbox off -> game/assets/characters/<id>.glb
```

npc.gd picks it by `"model"`; `"idle_clip"` picks the standing clip (Hedda `stir`, Tam `sleep`), `hit_height`/`hit_half_width` size the click box (a lying figure); without a GLB the procedural figure coloured by `palette` is
used. Licences: MPFB code GPL (local tool only, not shipped); base mesh, targets, rigs, skins CC0;
CMU mocap free for commercial use — credit "The data used in this project was obtained from
mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217." Blender 5.2's glTF
exporter writes vertex colours only for the first material that uses them: keep the cloth in
material slot 0 and paint beards into the skin texture.

Recipe facts: female bodies use `macro.gender` 0, `cupsize`, `firmness` and a female CC0 skin; age
0.84 ≈ 67 years, 0.38 ≈ 19. `skin` takes `hair`, `brows`, `flush`, `beard`, `floor`, `despeckle`.
Garments: `skin.forearms`, tunic `sleeves: "elbow"`, `hem_above_ankle`, `apron`, `kerchief`,
`hair`, `cloak`; long dresses want `thigh_share` 0.7 and `side_bias` 0. Clip types: `stand`
(`amplitude`, `rate`), `walk`, `rest` (lying); extra clip names are exported. CMU clips in use:
07_01 walk, 18_08 idle/talk, 77_02 idle, 79_13 stir, 77_18 sleep. The recipe keys are in the
`characters/build_human.py` docstring.

`make_character.py <id> --sketch` gives fast Workbench stills (`--show-ao`, `--no-fit`,
`--no-ao`); `characters/posefit.py` writes the hem-fit and drape shape keys (recipe `fit`:
`mode: clear | drape`, `keys`; skirt `fold_amp`, `fold_count`). The commander has seated clips
(`sit`, `sit_talk`, CMU 86_15, seat 0.50 m) for when his room gets a chair.

## Inner voices

One designed narrator speaks every skill line (`characters/narrator/`, voice `narrator`). Tag a
skill line `# line:skill_NN`; row NN of `characters/narrator/lines.txt` is its text with a tone
tag per skill. Render with `scripts/character.py narrator voice pick`, then copy
`final/line_NN.wav` to `game/assets/skills/skill_NN.wav` (high-pass 70 Hz, loudnorm -18 LUFS, no
room treatment: it is a voice inside the head).

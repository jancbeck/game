---
name: story-bible
description: The world, people, tone and story arc of the garrison game, and the rules for writing its dialogue, inner voices, skill checks, quests and look texts in Ink. Use it before writing or changing any line of dialogue, narration, hotspot text, quest, character or item description, before inventing a new character or place, and whenever the user talks about story, plot, lore, tone or what happens next.
---

# Story bible

The game is a story-first RPG in Disco Elysium's manner: few places, dense with people who
talk, remember and contradict each other, and an inner cast of skills that comment on
everything. It should grow to 10–20 hours. This page is the canon; extend it when you invent
something, so the next writer finds it.

## The place

**Varrow Gate**, a small stone garrison on a rock spur where the north road crosses into the
border marches. A gate, a wall, four towers, eleven men, a cook, and a commander in a
residential tower on the cliff edge. Built for forty. Blue hour, rain, late autumn. The road
north "has done nothing interesting since the old king died".

The realm: the old king died two winters ago; his widow rules as regent for a boy king, through
a council in the capital. Money is short, the marches are quiet, and quiet garrisons are
expensive. The council's seal is a crown; letters under it go by the king's post. Other seals
matter: a **tower over three wavy lines** is the seal of the Wardens of the Three Waters, the
river lords downstream who collect tolls, lend money to the crown, and want the north road
cheap and unguarded.

## People (canon so far)

| Who | Where | What they want | Voice |
|-----|-------|----------------|-------|
| **Sergeant Marl** | under the gate shelter by the fire basket | Keep the gate, the men and his dignity; thirty-one winters on this rock | Leonard (cloned): dry, tired, wry |
| **Hedda**, the cook | the cookhouse, at her hearth | Feed eleven men, protect her sister's boy, be right | Designed: smoky, raspy, mocking; has cooked for three commanders and buried two |
| **Tam**, the courier | asleep in the timber watch hood of the north-west tower | Deliver his letter unopened; sleep | Not yet voiced: nineteen, earnest, scared |
| **The commander** | the chamber on the third floor of the residential tower on the south-west cliff, behind his desk | Not yet written; recalled to the capital by the letter | — |
| The smith, the gate watch, nine other men | around the yard | — | — |
| **The player** | arrived through the gate after dark | Unknown to the garrison: "either you're lost, or somebody sent you to count our spears" | Never voiced |

Keep the player's identity open. Marl's suspicion (a counter of spears, an assessor from the
capital) is the leading theory and may be true. Do not resolve it without the user.

## The commander's chamber

The third floor of the residential tower, `locations/tower/`, reached by a spiral stair of thirty-odd steps from the yard door. A soldier's
room, not a lord's, on the cliff side: a paired window over a ten metre drop into a valley with a river. The commander stands behind
the desk, and the player on the other side of it. What the room says about him, so that his lines can use it:

- The muster roll has forty lines ruled and eleven names. The stores book is thinner and soft at the corners.
- A letter with a crown seal, a month old and unanswered, lies under a river stone. The courier's letter is not here: Tam still has it.
- The map of the march: the north road in red, the river in blue, the garrison as a black tower where they nearly cross, a pin
  hole for every rider that came through. It is rubbed pale in the south, where the capital is.
- A small hearth kept low, three candles on the desk, tallow counted. A niche with a saint rubbed smooth by thumbs and an oil lamp
  that is never let go out; whose saint it is, the garrison argues about, and the commander says nothing.
- A narrow bed with a grey wool blanket, a red curtain on a rail. Boots under the edge, toes out.
- A mail shirt, oiled and mended at the left shoulder, not worn since the old king died; a sword on pegs, two boar spears, a shield.

## The arc so far

1. **The rider nobody rang for** (playable, `quest.ink`): a courier's grey mare in the stable,
   half a broken seal (tower over three waves) in the straw, the bell rope tied up with Hedda's
   kitchen linen. Hedda confesses: her nephew Tam carries a letter for the commander and begged
   her to keep the bell silent. The letter (its seal already broken before it got here) says the
   commander is recalled and the garrison cut to six men. The player chooses what Marl learns:
   `letter_outcome` = `marl` or `kept`.
2. **Open threads:** who broke the seal on the road, and why a river lords' seal sits on a
   council order; what the commander does with the recall; which six men stay; who the player is.

## Tone and writing rules

- Dry humour under weather and fatigue. People are competent, tired and specific. No villains
  who announce themselves, no modern idioms, no fantasy magic. The uncanny lives only in the
  inner voices (the rock may speak).
- Concrete garrison detail beats description: soup, boots, rope, rust, tallies, the bell's code
  (once for a rider, twice for trouble).
- Short sentences. A line a voice actor can say in one breath or two. Voiced lines stay under
  about 35 words; Drama 3 breaks on longer ones and on lines that open with a two-word sentence.
  Never reuse words from a voice's reference clip.
- Every person remembers: check variables before repeating an introduction; react to items in
  the satchel and to what the player told others.
- Hotspot look texts are narration: present tense, second person only when the player acts,
  one image per sentence, the use of the thing in a garrison.
- Choices are short. Actions are in brackets (`\[Untie it.\]`); speech is plain.

## Inner voices (skills)

Six skills speak in the player's head, Disco Elysium style. They interrupt (passive checks)
and gate options (active checks). Write them as characters with opinions:

| Skill | Speaks about | Register |
|-------|--------------|----------|
| perception | what is there: steam, smells, a glint in the straw | precise, quick |
| empathy | what people feel and hide | warm, sometimes too much |
| authority | rank, face, who gives orders | clipped, proud |
| logic | contradictions, timelines | dry, pleased with itself |
| composure | your face, your hands, keeping cool | cool, a little vain |
| stonework | the castle itself: old stone, what the walls have seen | slow, ancient, a little uncanny |

Pass and fail both deserve good text. A failed check is a story beat, not a dead end: the quest
must stay finishable on every path. Red checks are for moments that cannot be asked twice.
Runtime syntax for skills, checks and the journal is in the `godot-runtime` and `npc-pipeline`
skills.

## Workflow for new content

1. Write the beat in this page's terms (who wants what, which variable changes).
2. Write the Ink in `game/data/story/` (one file per person, quests in their own file).
3. Voiced lines: add them to `characters/<id>/lines*.txt` and run `scripts/character.py`
   (see `npc-pipeline`).
4. `python3 scripts/ink.py`, then `python3 scripts/game.py check` (it plays the quest through).
5. Add new canon to this page.

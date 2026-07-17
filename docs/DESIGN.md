# Design Notes

## Fantasy & tone

The Ashen Vale: a mining penal colony sealed under a magical barrier
(Gothic homage). The Crown tips its condemned over the wall; ore leaves,
nothing else does. The barrier is not a wall but a mouth — it is *fed*.
The story asks what you do once you know the price of safety.

## Core mechanic: hardening

- Attributes: **Might, Guile, Lore, Heart** — start at score 1,
  flexibility 10.
- An `apply_approach` effect (attached to meaningful dialogue choices)
  gives +1 score to the used attribute and −2 flexibility to each other
  attribute.
- Flexibility 0 = **hardened**: any option with `not_hardened` on that
  attribute is permanently locked. The HUD shows this openly.
- Requirements ramp across the story: camp choices need score 1 (free
  choice), the prisoner needs 2 (some investment), endings need 3 *and*
  an unhardened attribute. A pure specialist reaches the finale with
  exactly one ending available — by their own doing.

## Story beats (prototype scope)

1. **Enter the Vale** — Rurik the Gatekeeper. Tutorial for the four
   approaches; all four work, each leaves a different flag/memory.
2. **Earn Your Place** — Marda, camp leader. Free choice of approach;
   sets faction-flavored flags.
3. **The Chained Man** — Essek. Three ways to free him, one (Heart) to
   leave him chained but witnessed. All grant `knows_barrier_secret`,
   the key to the finale.
4. **The Overseer** — the confrontation. Four endings: the Honest
   Catastrophe (Might), the Quiet Ledger (Guile), the Corrected Rune
   (Lore), the Vale That Chose (Heart).

## Visual approach

Gray-box on purpose: procedural capsule characters with code-driven idle
sway and walk bob; atmosphere from fog, cold moonlight, warm torch pools,
and the fixed 45°/−50° isometric camera. No skeletal animation, no
imported models, no rig retargeting — the exact pipeline that killed the
previous prototype is out of scope by design.

## Deliberate non-goals

Combat, inventory, crafting, open world, procedural generation,
multiplayer, visual dialogue editors.

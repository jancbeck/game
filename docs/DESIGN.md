# Design Notes

## Fantasy & tone

The Ashen Vale: a mining penal colony sealed under a magical barrier
(Gothic homage). The Crown tips its condemned over the wall; ore leaves,
nothing else does. The barrier is not a wall but a mouth — it is *fed*.
The story asks what you do once you know the price of safety.

## Core mechanic: hardening

- Attributes: **Might, Guile, Lore, Heart** — each tracks a *score* and a
  *flexibility* (exact numbers live in the reducers).
- Meaningful choices apply an *approach*: the used attribute gains score,
  the others lose flexibility.
- Flexibility 0 = **hardened**: options gated on that attribute are
  permanently locked. The HUD shows this openly.
- Requirements ramp across the story so that a pure specialist reaches
  the finale with exactly one ending available — by their own doing.

## Story beats (the Ashen Vale arc)

1. **Enter the Vale** — the gatekeeper. Tutorial for the four approaches;
   all four work, each leaves a different flag/memory.
2. **Earn Your Place** — the camp leader. Free choice of approach; sets
   faction-flavored flags.
3. **The Chained Man** — three ways to free him, one (Heart) to leave him
   chained but witnessed. All grant the barrier's secret, the key to the
   finale.
4. **The Overseer** — the confrontation. Four endings, one per attribute:
   catastrophe (Might), ledger (Guile), correction (Lore), choice
   (Heart).

## Visual approach

Two coexisting modes. NPCs are procedural 3D — no third-party models, no
animation libraries, no rig retargeting (the exact pipeline that killed the
previous prototype). The single sanctioned exception is the player: the
convict from `art/sprites/convict.png`, a Blender-built skeletal model
(`art/models/convict.glb`) where ONE script owns mesh, armature, and
animations, so mismatch is impossible by construction.

- **Gray-box** (`scenes/main.tscn`): procedural capsule characters, fog,
  cold moonlight, warm torch pools, fixed isometric camera. The original
  bootstrap; still boots and is tested.
- **Painted** (`scenes/painted/*.tscn`): the Disco Elysium direction — a 2D
  painted backdrop (generated art) with real-time 3D actors walking on it
  under lights placed where the painting's fires are. This is where new
  story content goes.

The mechanics layer is identical across both; only presentation differs.
See `docs/PIPELINE.md` for the how and why.

## Two settings currently coexist

Be aware when adding content: the repo holds the start of a second story.

- **Ashen Vale** (original) — the penal-colony/barrier arc above.
- **The Myrtana retcon** (new, painted) — a *Gothic 3 retelling* that the
  painted `prison_yard` scene opens: the nameless hero arrives from Khorinis,
  is disbelieved and thrown in the royal prison (stats stripped to zero), and
  the intended arc is prison break → join the Highland rebels → retake towns
  → reach the capital to warn the King → the orc fleet arrives at the harbor.
  Only its opening is built so far. The hardening mechanic and all systems
  are shared; it is a presentation + content branch, not a fork.

Decide which setting a new scene belongs to before authoring it.

## Deliberate non-goals

Combat, crafting, open world, procedural generation, multiplayer, visual
dialogue editors. (Inventory left this list when the production character
track made items in scope. *Combat* stays: gesture and item-use
animations are presentation, not a combat system.)

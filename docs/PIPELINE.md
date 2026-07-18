# The painted-scene rendering pipeline

Why the game looks the way it does, the non-obvious ideas behind it, and the
things that are *known-wrong* so nobody re-investigates them. The HOW (node
setup, manifest fields) is in `scripts/systems/painted_scene.gd`; this is the
WHY and the limitations.

## The core idea: a painting wearing a 3D costume

Disco Elysium's world is a flat oil painting; only the characters are
real-time 3D. We copy that:

- The backdrop renders as a single unshaded quad locked to the camera's far
  plane, sized to exactly fill the frustum. So **backdrop pixels and screen
  pixels stay in 1:1 correspondence** no matter the window size.
- Characters are real-time 3D `CharacterRig` actors rendered in front of it,
  lit by lights placed where the painting's fires are.

The payoff: the world costs one image to make (not a modelled 3D set), but
characters get true dynamic lighting, depth, and animation on top of it.

## The trick that makes it work: pixels ARE ground coordinates

`px_to_world()` unprojects a backdrop pixel through the fixed camera onto the
invisible `y=0` ground plane. This is the whole illusion:

- A character placed at a "far" (higher-up) painting pixel is genuinely
  farther away in 3D, so it **foreshortens and shrinks automatically** — you
  never hand-author per-position scale. This is why walk-toward-the-back
  looks correct for free.
- Authoring is done entirely in backdrop-pixel coordinates (open the PNG,
  read positions), which is why manifests are text and need no editor.

The consequence to remember: the mapping assumes everything is on the ground
plane. Anything the painting depicts *above* the ground (wall torches,
hanging signs) is mis-placed if you feed its pixel to `px_to_world` alone.
For those, a light carries an authored height hint — `"wall": true` +
`"wall_height"` reads the flame pixel on a horizontal plane at that height
(via `px_to_world_at_height`), or `"world": [x, y, z]` sets the position
outright — so the light lands at the painted flame instead of far up the wall.

## Occlusion: cards, not a depth map

DE baked grayscale height/depth maps in Blender. We don't have Blender in the
loop, so foreground occlusion is done with **occluder cards**: a manifest
polygon cuts the prop's region out of the backdrop, and that cut-out is
mounted as a quad at the prop's true ground depth. A character standing
deeper than the card is hidden by the ordinary depth buffer.

Trade-offs (by design, so you can weigh them):
- The card is a *duplicate* of a region already in the far-plane painting.
  If the card's depth/scale is slightly off, you get a faint double-image of
  the prop. Because the card is cut from those exact pixels and the camera is
  fixed, a correctly-anchored card lands 1:1 over its source with no seam —
  the CI `06_occlusion` frame is the proof; align the anchor carefully.
- Cutting is per-pixel in GDScript at load time. Fine for a few props per
  scene; if a scene needs many/large occluders, bake the cards offline
  instead of at runtime.

## Known limitations (do not "discover" these again)

These are true of the code as merged; they are facts you cannot read off the
source, only off rendered frames:

1. **No music or designed SFX.** Ambience/crackle/clicks are procedurally
   synthesized placeholders; the asset key cannot make music or real SFX.

Resolved (kept as breadcrumbs so they aren't reopened):

- *Wall-mounted fires.* Lights now take an authored height hint
  (`"wall"`/`"wall_height"` or `"world"`) so torches painted high on a wall
  light at the flame; ground braziers still ground-project. See the mapping
  section above and `_light_position`.
- *Occlusion proven.* The `06_occlusion` frame stands a character half behind
  the low foreground prop — legs hidden, torso clear, no double-image seam.
- *`CharacterRig` proportions.* Rebalanced to a taller, smaller-headed
  silhouette with an idle weight-shift and a lean-in gesture during dialogue;
  a manifest `"build"` scalar varies height/bulk per character.

## The player model: a real rig, one script

The player is the convict from `art/sprites/convict.png` — a genuine
skeletal rig (`art/models/convict.glb`: 15 bones, puppet-style rigid
skinning, baked 30 fps `idle`/`walk`/`talk` clips), not a procedural
capsule. This does not reopen the postmortem's #6 ("AI models + third-party
animation libraries = rig mismatch hell"): `tools/build_convict.py` authors
mesh, armature, AND animations in a single Blender run, so there is nothing
to mismatch. The rule that stands is **no third-party rigs or animation
libraries**; one self-contained generator script is the loophole, and it is
the only one.

- Rebuild locally (Blender is not in CI; the .glb is a committed artifact):
  `blender -b -P tools/build_convict.py` — also writes pose renders to
  `reports/convict/` for eyeballing before you commit.
- The cloth/rag textures (`art/models/convict_cloth.png`, `convict_rag.png`)
  are one-off `tools/genart.py` edits-endpoint generations with the sprite
  as style reference, committed like all art. The rag strip is authored
  full-frame (solid at v=1, tatter tips at v=0) and alpha-blended onto the
  hem cone — that is where the silhouette's raggedness comes from.
- `scripts/world/convict_rig.gd` (`ConvictRig extends CharacterRig`) wraps
  the GLB and maps the familiar interface onto the AnimationPlayer:
  `animate(delta, speed)` crossfades idle/walk/talk, `set_speaking` picks
  the talk loop, `face_direction` is inherited (the model faces +Z in glTF,
  so the wrapper spins it π to agree with the -Z facing math). `build`
  scales the whole model; palettes are a no-op — the convict's colors are
  baked from the sprite. NPCs stay procedural `CharacterRig`s.
- CI proof: the smoke test asserts the player is a ConvictRig with all
  three clips and walks/talks/idles on command; `test/unit/test_convict_rig.gd`
  covers the state machine; `tools/screenshots.gd` frames 09–11 are a
  deterministic model sheet (clips frozen at fixed timestamps).

## Two visual modes coexist

`scenes/main.tscn` is the original gray-box 3D world (capsule characters,
fog, torch pools) and still boots/tests. `scenes/painted/*.tscn` is the
painted-backdrop direction. Both share the same store/reducers/dialogue
runner — the difference is purely presentational. New story content should
use painted scenes.

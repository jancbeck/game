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
hanging signs) is mis-placed if you feed its pixel to `px_to_world` alone —
which is why a light can carry an authored height hint instead (the fields
live in the manifest schema in `painted_scene.gd`).

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
- Cards are baked offline by `tools/bake_occluders.py` (Python + Pillow)
  from the manifest polygons and committed under `art/occluders/<scene>/`
  with a `cards.json` (anchor + bounds per card). Scene load is a plain
  texture load, no per-pixel work. Re-run the baker after changing a
  backdrop or any occluder polygon — CI's `bake_occluders.py --check`
  guards drift.

## Known limitations (do not "discover" these again)

These are true of the code as merged; they are facts you cannot read off the
source, only off rendered frames:

1. **No music or designed SFX.** Ambience/crackle/clicks are procedurally
   synthesized placeholders; the asset key cannot make music or real SFX.

Resolved (kept as breadcrumbs so they aren't reopened):

- *Wall-mounted fires.* Lights can carry an authored height hint so torches
  painted high on a wall light at the flame; ground braziers still
  ground-project.
- *Occlusion proven.* The `06_occlusion` frame stands a character half
  behind a foreground prop — legs hidden, torso clear, no double-image
  seam. It is re-staged per character: the card/spot geometry is
  height-sensitive, and a shorter actor can vanish behind a neighbouring
  card while the golden diff stays inside tolerance. Eyeball the frame
  after any player-model change.
- *`CharacterRig` proportions.* Rebalanced to a taller, smaller-headed
  silhouette; a manifest `"build"` scalar varies height/bulk per
  character.

## The player model: a real rig, one script

The player is the convict from the sprite — a genuine skeletal model, not
a procedural capsule. This does not reopen the postmortem's #6 ("AI
models + third-party animation libraries = rig mismatch hell"): the rule
that stands is **no third-party rigs or animation libraries**, and
`tools/build_convict.py` authors mesh, armature, AND animations in a
single Blender run, so there is nothing to mismatch. That self-contained
generator is the loophole, and it is the only one. NPCs stay procedural.

Non-obvious facts around it (learned from rendered frames, not from the
code):

- Blender is not in CI. The GLB is a committed build artifact;
  regenerating it is a local step (the build script also renders poses
  for eyeballing — look at them before committing).
- glTF assets face +Z; the game's facing math aims -Z. Any imported
  model needs that compensation on the Godot side or it walks backwards.
- Manifest palettes tint only procedural rigs; a GLB character's colors
  are baked into the model.
- The rag-hem texture must be authored full-frame — solid at the top,
  tatter tips at the bottom — or the hem mapping breaks. It came from
  the same reference-guided generation pass as the sprites.

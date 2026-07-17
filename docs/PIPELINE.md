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
hanging signs) will be mis-placed if you feed its pixel to `px_to_world`.

## Occlusion: cards, not a depth map

DE baked grayscale height/depth maps in Blender. We don't have Blender in the
loop, so foreground occlusion is done with **occluder cards**: a manifest
polygon cuts the prop's region out of the backdrop, and that cut-out is
mounted as a quad at the prop's true ground depth. A character standing
deeper than the card is hidden by the ordinary depth buffer.

Trade-offs (by design, so you can weigh them):
- The card is a *duplicate* of a region already in the far-plane painting.
  If the card's depth/scale is slightly off, you get a faint double-image of
  the prop. Align the anchor carefully.
- Cutting is per-pixel in GDScript at load time. Fine for a few props per
  scene; if a scene needs many/large occluders, bake the cards offline
  instead of at runtime.

## Known limitations (do not "discover" these again)

These are true of the code as merged; they are facts you cannot read off the
source, only off rendered frames:

1. **Wall-mounted fires land wrong.** Light/ember `px` is ground-projected,
   so torches painted high on a wall get their light and particles placed too
   far back. Ground-level braziers are correct. Proper fix: an authored world
   `height`/`wall` hint in the manifest instead of ground projection —
   deferred pending a call on how much fire fidelity is worth.
2. **Occlusion is implemented but not yet proven on screen.** The demo pose
   used so far leaves the character fully hidden, which doesn't demonstrate
   the effect. Needs a half-behind-the-prop pose to confirm no seams.
3. **`CharacterRig` proportions are stubby** (large head) — acceptable
   gray-box, tunable in the rig.
4. **No music or designed SFX.** Ambience/crackle/clicks are procedurally
   synthesized placeholders; the asset key cannot make music or real SFX.

## Two visual modes coexist

`scenes/main.tscn` is the original gray-box 3D world (capsule characters,
fog, torch pools) and still boots/tests. `scenes/painted/*.tscn` is the
painted-backdrop direction. Both share the same store/reducers/dialogue
runner — the difference is purely presentational. New story content should
use painted scenes.

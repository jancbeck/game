---
name: generate-assets
description: >
  Generate painted scene backdrops, transparent character sprites, dialogue
  portraits, and spoken NPC voice lines for Ashen Vale using the OpenAI
  image and TTS APIs. Use when adding or replacing any visual/audio asset
  under art/. Encodes empirical API findings that are NOT discoverable from
  the API docs. Requires OPENAI_API_KEY.
---

# Generating art & audio assets

All assets are generated ONCE, locally, and committed under `art/`. Nothing
here runs in CI. The harness is `tools/genart.py` (text prompt on stdin).

## The findings that cost iterations (use them, don't re-discover them)

- **Backdrops → `gpt-image-2`.** Best painterly / oil-painting output.
  Ask explicitly for "a playable isometric game area, fixed three-quarter
  top-down view, no characters" or you get concept art with no walkable
  floor. 1536×1024 matches the game's 3:2 window.
- **`gpt-image-2` REFUSES `background=transparent`** (HTTP 400). Characters
  and portraits therefore use **`gpt-image-1.5`**, which supports it.
- **Style coherence is not automatic — it comes from a reference image.**
  Generate sprites/portraits through the `/images/edits` endpoint with the
  master backdrop passed as the reference (form field name is literally
  `image[]`). This is what keeps every character in the scene's palette and
  light. Without it, sprites drift into a different art style.
- **Same-location consistency across scenes:** crop a region of a master
  painting (e.g. the gallows corner) and regenerate it as its own scene via
  the edits endpoint — the model reproduces the same props/materials. This
  is how one "level" painting spawns several coherent sub-scenes.
- **Voice acting lives in the `instructions` field**, not the line text.
  `gpt-4o-mini-tts`, voice `onyx` reads as a gruff older man; direct tone
  per line ("weary, threatening, a flicker of fear when he mentions the
  fleet").
- **Capability gap:** this key does images + speech only. **No music, no
  designed SFX.** Placeholder ambience/crackle/clicks are synthesized as
  raw WAVs with Python math (see `art/audio/*.wav` history); real music/SFX
  need a different provider (ElevenLabs / Suno) or CC0 packs.

## Recipes

```sh
export OPENAI_API_KEY=...

# Scene backdrop (prompt on stdin)
python3 tools/genart.py backdrop art/scenes/<id>.png <<'EOF'
Isometric oil-painting game level, Disco Elysium style, <scene description>.
Fixed three-quarter top-down view, no characters, open walkable floor,
legible silhouettes, muted palette, warm firelight vs cold dusk.
EOF

# Character sprite (transparent) — pass the scene as style reference
python3 tools/genart.py sprite art/sprites/<id>.png art/scenes/<id>.png <<'EOF'
Single full-body character sprite on a transparent background, same
elevated three-quarter angle and painterly style as the reference:
<character description>. Nothing else in frame — no ground, no shadow.
EOF

# Dialogue portrait — same call, framed as a bust
python3 tools/genart.py portrait art/sprites/<id>_portrait.png art/scenes/<id>.png <<'EOF'
Head-and-shoulders portrait, painterly, matching the reference lighting:
<character description>.
EOF

# Voice line — acting direction is the 4th arg, line text on stdin
python3 tools/genart.py voice art/audio/vo/<id>.mp3 onyx \
  "Weary medieval jailer, low and threatening, unhurried." <<'EOF'
Off the boat from Khorinis and straight into my yard...
EOF
```

## After generating

1. **Sprites:** trim to the alpha bounding box before committing (raw output
   has huge transparent margins that throw off in-game scale). Pillow:
   `Image.open(p).convert("RGBA").crop(Image.open(p).getbbox()).save(p)`.
   Note: sprites are now used as **dialogue portraits** — in-world bodies are
   the procedural 3D `CharacterRig`, not the sprite. See `add-painted-scene`.
2. **Review the actual pixels** with the Read tool before committing — the
   model occasionally adds an unwanted background or extra limbs.
3. Wire the asset into a scene manifest and verify it renders via the CI
   screenshot loop (see `docs/CI.md`).

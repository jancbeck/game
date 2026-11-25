---
name: sound-effects
description: Make, cut, level and wire sound effects for the garrison game with Stable Audio 3 (local MLX via galley-v2 tools) - prompts, footstep cutting per surface, normalisation, loops, the game.html contact sheet, and game/data/sounds.json. Use it whenever a new sound, footstep surface, ambience, door or object sound is needed, or levels or loudness feel wrong in the game.
---

# Sound effects

Stable Audio 3 (`medium` DiT + `same-l` decoder, MLX) is the sound-effect model; it runs through
`~/workspace/projects/galley-v2/tools/sfx`. MOSS-SoundEffect v2 was tried and sounded worse.
There is no music model in the workflow. Everything lives in `audio/`.

**Taste:** dry sounds. No synthetic reverb on anything ("a church", "a barrel"); the courtyard
is open to the sky. Spot effects end their prompt in "dry close-miked film sound effect, no
reverb"; beds use "wide stereo field recording".

## Make sounds

```bash
python3 audio/scripts/gen_sfx_sa3.py --list game_sfx            # outside the sandbox (Metal), through gpu.py
<sa3-venv>/bin/python audio/scripts/game_sfx.py stats
<sa3-venv>/bin/python audio/scripts/game_sfx.py steps
<sa3-venv>/bin/python audio/scripts/game_sfx.py finish audio/sfx/game/_picks.json
python3 audio/scripts/build_game_index.py                       # audio/game.html contact sheet
```

`<sa3-venv>` is `galley-v2/tools/stable-audio-3/optimized/mlx/.venv` (numpy + soundfile).

- **Settings:** 8 steps, two seeds per item (1000+, later rounds 2000+, 3000+), CFG 3.0; CFG 2.0
  for sounds that clip (crows, forge, gate, torch, stable, wind). The model peaks near 2.0 float.
- **Prompts** are in `audio/prompts.json` under `game_sfx`; each take has a JSON sidecar with its seed.
- Metal "GPU Hang" errors happen when other GPU jobs run: queue every generation.

## Process

- `stats`: loudness, true peak, clipped samples, centroid, band shares, and a sustained-tone
  check (18 dB over its neighbourhood for 140 ms flags music, voices or whistles).
- `steps`: onsets by spectral flux above 150 Hz; a step runs to the next onset (≤ 0.62 s),
  4 ms fade-in, 120 ms cosine fade-out. Rejects overlapping, clipped, truncated and off-level
  steps; keeps the 8 closest to a per-surface timbre profile, levelled to -24 dB K-weighted over
  300 ms. Stone stair: 120 Hz high-pass, -6 dB below 350 Hz; wood: 70 Hz high-pass.
- `finish`: cut, trim, 2 ms / 60 ms fades, then `postprocess.py` normalisation: ffmpeg loudnorm
  two-pass to -16 LUFS, true peak -1 dB (a 30 Hz high-pass first; sparse sounds get gain plus a
  limiter; files under 0.45 s get K-weighted gain with a -1 dBFS ceiling).
- Loops (`_loop.wav`): the last 1.5–2 s cross-fade into the start at equal power.
- `galley-v2/tools/listen` describes files to catch speech or music; its naming of sources is
  unreliable.

| Path | Content |
|------|---------|
| `audio/sfx/game/<id>_t<k>.wav` | Raw takes + sidecars, `_run_log.jsonl`, `_stats.tsv` |
| `audio/sfx/game/steps/` | Cut steps, `_steps.json` (every onset with the reason) |
| `audio/sfx/game/_picks.json` | Take and time range of every non-step sound |
| `audio/sfx/game/final/` | The game files, copied to `game/assets/audio/{steps,ui,objects,doors}` |

Audio files are not in git.

## Wire into the game

`game/data/sounds.json`: `footsteps` per surface (`cobble`, `mud`, `puddle`, `stone_stair`,
`stone_walk`, `wood`, `straw`; at least 6 variants each), `step_interval_s`, `click`,
`hotspots` (by hotspot id), `portals` (open/close per door sound), `levels_db`. All 44.1 kHz WAV.
`scripts/game.py check` fails when a walk surface has no clips or a hotspot/portal sound is
unknown. `config.json` `audio` holds the rain bed, the fire loop and the crow calls.

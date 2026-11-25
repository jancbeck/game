"""Design a voice from a text description with Qwen3-TTS VoiceDesign (mlx-audio).

The takes become the reference clip for Drama 3 (galley-v2 tools/say), which voices the lines.
Candidates and the reference text come from characters/<id>/voice_design.json:

    {"text": "<a reference passage, 15-25 s, many sounds, some feeling; no words of later lines>",
     "candidates": {"<key>": "<description of age, timbre, accent, pace, mood; end with 'Close to the microphone, dry room.'>"}}

  python3 scripts/gpu.py run --name voice/<id>-design -- \\
    ~/workspace/resources/voicedesign/.venv/bin/python scripts/design_voice.py <id> [--takes 2] [--voice key]

Writes characters/<id>/design/<key>_t<k>.wav. Pick one, cut a 15-18 s reference at sentence
boundaries, clean it with Sidon and register it in galley-v2 tools/say-voices.json (npc-pipeline skill).
"""
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from mlx_audio.tts.utils import load_model

MODEL = "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16"
ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--takes", type=int, default=2)
    ap.add_argument("--voice", action="append", help="candidate key (default: all)")
    a = ap.parse_args()
    src = ROOT / "characters" / a.id
    design = json.loads((src / "voice_design.json").read_text())
    out = src / "design"
    out.mkdir(parents=True, exist_ok=True)
    model = load_model(MODEL)
    for key in a.voice or design["candidates"]:
        for t in range(a.takes):
            chunks = [np.array(r.audio) for r in model.generate_voice_design(
                text=design["text"], language="English", instruct=design["candidates"][key], temperature=0.9)]
            audio = np.concatenate(chunks)
            path = out / f"{key}_t{t + 1}.wav"
            sf.write(path, audio, model.sample_rate)
            print(path, f"{len(audio) / model.sample_rate:.1f}s", flush=True)


if __name__ == "__main__":
    main()

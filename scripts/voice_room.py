"""Place a dry voice take a few steps away in the courtyard.

    python scripts/voice_room.py IN.wav OUT.wav [--distance 2.5] [--wet -16]

Voice takes from tools/say are dry and close-miked. In the game a person speaks a couple of
metres away, under a roof, in a stone courtyard, so the take gets:

- a gentle high cut and a little less low end, for the distance (air and a voice not aimed at a mic);
- a short, soft ambience: a dense noise impulse response that dies away in about RT60 seconds,
  with the highs fading faster, after a short pre-delay, at `--wet` dB relative to the voice
  (measured as RMS of the two signals). Just air around the voice, not a hall.

No single early reflection (at a few metres it arrives within milliseconds and colours the voice
like a comb filter), and no long synthetic reverb: the orbit soundtrack's 1.3 s courtyard
reverb makes a close voice sound metallic, like a church.

Output is 44.1 kHz 16-bit stereo, peak-normalised to the input's peak. Needs numpy (run it with
Blender's Python or `uv run --with numpy`).
"""

import argparse
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scene"))
import orbit_audio as oa  # noqa: E402

C = 343.0


def read(path):
    with wave.open(str(path)) as w:
        n, ch, rate, width = w.getnframes(), w.getnchannels(), w.getframerate(), w.getsampwidth()
        x = np.frombuffer(w.readframes(n), dtype={2: "<i2", 4: "<i4"}[width]).astype(np.float32)
    x = x.reshape(-1, ch).mean(1) / (2 ** (8 * width - 1))
    if rate != oa.RATE:
        t = np.arange(int(len(x) * oa.RATE / rate)) / oa.RATE
        x = np.interp(t, np.arange(len(x)) / rate, x).astype(np.float32)
    return x


def ambience_ir(rt60, seed=3):
    """Stereo noise IR: exponential decay to -60 dB at rt60 (highs at half that), soft onset."""
    rng = np.random.default_rng(seed)
    n = int(rt60 * 1.2 * oa.RATE)
    t = np.arange(n) / oa.RATE
    noise = rng.standard_normal((n, 2)).astype(np.float32)
    low, high = oa.bands(noise, (2500.0,))
    decay = lambda rt: np.exp(-6.91 * t / rt)[:, None]
    ir = low * decay(rt60) + high * decay(rt60 * 0.5)
    ir *= np.clip(t / 0.004, 0, 1)[:, None]
    return (ir / np.sqrt((ir ** 2).sum())).astype(np.float32)


def place(x, distance, wet_db, rt60=0.3):
    # distance: air and off-axis loss above about 8 kHz, a little less chest resonance
    near = oa.fft_filter(x, lambda f: oa.lowpass(9000, 1)(f) * oa.highpass(90, 1)(f))
    pre = int((distance / C + 0.012) * oa.RATE)        # the first wall is a few metres further
    padded = np.concatenate([np.zeros(pre, np.float32), near, np.zeros(int(rt60 * 1.2 * oa.RATE), np.float32)])
    tail = oa.fft_filter(oa.convolve(padded, ambience_ir(rt60)), oa.lowpass(5000, 1))
    dry = np.pad(near, (0, len(tail) - len(near)))
    rms = lambda v: float(np.sqrt(np.mean(v ** 2)) + 1e-12)
    tail *= rms(near) / rms(tail) * 10 ** (wet_db / 20)
    out = np.stack([dry, dry], 1) + tail
    # trim the reverb tail where it has decayed below -60 dB
    level = np.abs(out).max(1)
    last = np.nonzero(level > level.max() * 1e-3)[0][-1]
    out = out[:last + int(0.05 * oa.RATE)]
    return out * (np.abs(x).max() / np.abs(out).max())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--distance", type=float, default=2.5)
    ap.add_argument("--wet", type=float, default=-18.0, help="ambience level in dB relative to the voice")
    ap.add_argument("--rt60", type=float, default=0.3, help="ambience decay time in s")
    a = ap.parse_args()
    out = place(read(a.inp), a.distance, a.wet, a.rt60)
    oa.write_wav(a.out, out)
    print(f"{a.out}: {len(out) / oa.RATE:.2f} s")


if __name__ == "__main__":
    main()

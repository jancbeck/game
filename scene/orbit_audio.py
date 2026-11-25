"""Soundtrack of the orbit video: a distant rain bed plus sound sources placed in the courtyard.

    python3 scene/orbit_audio.py --out renders/orbit/orbit.wav [--frames 480] [--duration 20]

Pure Python and numpy; no Blender. Clips come only from audio/sfx/stable-audio-3/norm.

Listener: the orbit camera of render_orbit.py, at its real 3D position (about 28 m above the
courtyard and 35 m out from the pivot), turning with the same eased yaw, re-centring and drift.
Its right vector sets the stereo pan. Frame i of the video is time i / fps, and the camera
pose at that time is render_orbit's pose at fraction i / (frames - 1).

Rain bed: four decorrelated layers of the rain loops (time offsets, swapped channels), with
the drop transients flattened, a low-pass at 3.8 kHz plus a high-shelf cut, a wash through the
courtyard reverb and a widened side channel. It is heard from far above, not from the ground.

Point sources (`SOURCES`, positions from the courtyard's plan.json): fire basket, forge hearth and
hammer, gatehouse spouts, roof rain on the stable, shed and watch shelter, and one-shots
(`CUES`) for the horse and the crows on the gallows and the battlements. Each one is heard
from the camera with:

- inverse-distance gain, relative to its level at REF_DIST;
- propagation delay d / 343 m/s, read through a moving fractional delay, so the moving
  camera gives a small Doppler shift (below 2 %);
- air absorption in four bands (ISO 9613-1 at 10 C, 70 % humidity), more loss with distance;
- equal-power pan from the camera's right vector;
- a send to a stone-courtyard reverb (synthetic impulse response: first- and second-order wall
  reflections of the courtyard, then a diffuse tail with RT60 1.3 s low, 0.55 s high).
  The send is constant and the direct sound falls as 1/d, so the wet share rises with distance.

One-shots are timed by their arrival at the camera: each is emitted so that the middle of the
call reaches the camera a set time before or after the camera's closest pass to its source.

The mix is scaled to MIX_RMS_DB before the fades, then soft-limited, with the fades of the
camera move (1.5 s in, 2.5 s out).

API:
    listener(n, frames, duration)             -> pos (n, 3), right (n, 3)
    render_stems(frames, duration)            -> {name: (n, 2) float32 array}, unscaled
    mix_stems(stems)                          -> (n, 2) float32 mix, scaled, limited and faded
    write_mix(path, frames=480, duration=20)  -> writes 16-bit stereo WAV, returns the mix
"""

import argparse
import math
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scene"))

import location  # noqa: E402

SFX = ROOT / "audio" / "sfx" / "stable-audio-3" / "norm"
RATE = 44100
C_SOUND = 343.0         # m/s
REF_DIST = 40.0         # m: a source's `level` is its gain at this distance
MIX_RMS_DB = -22.0      # mix RMS before fades and limiter
FAR_BED = 0.28          # rain bed gain heard from 25-30 m up: under the placed sources
NEAR_BED = 1.0          # rain bed gain on the ground (descent)
NEAR_HEIGHT = (2.0, 14.0)   # m: the near rain fades in from the upper to the lower height
PRE_ROLL = 0.5          # s of source signal before t = 0, so delayed sound is present from the start

# air absorption, dB per m (ISO 9613-1, 10 C, 70 % humidity), for the bands split at BAND_EDGES:
# below 1 kHz, 1-4 kHz, 4-8 kHz, above 8 kHz
AIR_DB_PER_M = (0.002, 0.010, 0.05, 0.16)
BAND_EDGES = (1000.0, 4000.0, 8000.0)


# ---------- sources ----------
# name: clip, position (x, y, z in m, plan.json frame), level at REF_DIST, clip offset (s)
# Positions: brazier, forge, stable, shed, watch_shelter from plan.props; the gatehouse spouts
# from scene/assets/_drips_src.py (x = -5.1 and -2.5, water landing on the floor at y = 2.6).
SOURCES = {
    "fire_basket": ("brazier_t1_loop.wav", (1.0, 0.55, 0.9), 0.30, 0.0),
    "forge_hearth": ("brazier_t2_loop.wav", (2.9, -7.1, 0.9), 0.16, 4.0),
    "spout_west": ("spout_t1_loop.wav", (-5.1, 2.6, 0.1), 0.15, 0.0),
    "spout_east": ("spout_t2_loop.wav", (-2.5, 2.6, 0.1), 0.13, 6.5),
    "roof_stable": ("rain_roof_t2_loop.wav", (9.8, -6.3, 3.2), 0.14, 0.0),
    "roof_shed": ("rain_roof_t1_loop.wav", (-6.975, 0.87, 2.6), 0.11, 5.0),
    "roof_shelter": ("rain_roof_t1_loop.wav", (1.75, 2.15, 2.6), 0.09, 11.0),
}

# one-shots: name, clip, (start, length) in the clip, position, level, arrival time, gate.
# Arrival: seconds relative to the moment the camera passes closest to the source; the middle of
# the call reaches the camera then. Gate: band-pass and expand, to drop the rain baked into the
# crow clips.
CUES = [
    # the smith hammers while the camera is on the south side, rests, and starts again as it returns
    ("forge_hammer", "forge_t1.wav", (0.0, 8.0), (2.9, -7.1, 1.0), 0.20, -1.0, False),
    ("forge_hammer", "forge_t2.wav", (2.0, 6.0), (2.9, -7.1, 1.0), 0.18, 11.4, False),
    # the horse in the stable (south-east) as the camera swings past it, and a softer snort later
    ("horse", "stable_t1.wav", (3.1, 2.0), (9.8, -6.3, 1.4), 0.20, 0.0, False),
    ("horse", "stable_t1.wav", (9.4, 1.2), (9.8, -6.3, 1.4), 0.11, 3.6, False),
    # crows: on the south-east curtain's battlements, on the gallows beam, on the north-west tower,
    # and a last one answering from the west curtain
    ("crows", "crows_t1.wav", (5.0, 0.6), (7.69, -10.81, 6.3), 0.20, -1.0, True),
    ("crows", "crows_t2.wav", (0.8, 2.1), (3.82, -0.45, 4.72), 0.20, 0.2, True),
    ("crows", "crows_t1.wav", (6.25, 0.6), (-9.65, 5.5, 8.7), 0.18, 0.0, True),
    ("crows", "crows_t2.wav", (3.55, 0.45), (-11.4, -6.0, 6.3), 0.10, 0.8, True),
]

# the courtyard for the early reflections: walls (axis, coordinate, height), plan.json blocks
COURT_WALLS = [("x", -10.4, 6.0), ("x", 11.3, 6.0), ("y", 3.0, 7.5), ("y", -10.5, 1.1)]
COURT_CENTRE = (0.0, -3.5, 1.5)


# ---------- clips ----------

def read_clip(name):
    with wave.open(str(SFX / name)) as w:
        assert w.getsampwidth() == 2 and w.getframerate() == RATE and w.getnchannels() == 2, name
        a = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    return a.reshape(-1, 2).astype(np.float32) / 32768.0


def looped(clip, n, offset=0.0):
    """n samples of a loop clip, tiled, starting `offset` seconds into it."""
    i = int(offset * RATE) % len(clip)
    clip = np.concatenate([clip[i:], clip[:i]])
    return np.tile(clip, (math.ceil(n / len(clip)), 1))[:n]


def segment(clip, start, length, fade=0.04):
    seg = clip[int(start * RATE):int((start + length) * RATE)].copy()
    f = int(fade * RATE)
    ramp = np.sin(np.linspace(0, math.pi / 2, f)) ** 2
    seg[:f] *= ramp[:, None]
    seg[-f:] *= ramp[::-1, None]
    return seg


# ---------- filters (zero-phase, by FFT) ----------

def fft_filter(x, response, pad=RATE):
    """Filter x (n,) or (n, c) with a real gain response(freqs in Hz)."""
    n = len(x)
    m = 1 << int(math.ceil(math.log2(n + pad)))
    f = np.fft.rfftfreq(m, 1 / RATE)
    g = response(f)
    if x.ndim == 2:
        g = g[:, None]
    return np.fft.irfft(np.fft.rfft(x, m, axis=0) * g, m, axis=0)[:n].astype(np.float32)


def lowpass(fc, order=1):
    return lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order))


def highpass(fc, order=1):
    return lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order))


def bands(x, edges=BAND_EDGES):
    """Split x into complementary bands at `edges` (they sum back to x), lowest first."""
    below = [fft_filter(x, lowpass(fc, 2)) for fc in edges] + [x]
    return [below[0]] + [below[i] - below[i - 1] for i in range(1, len(below))]


def convolve(x, ir):
    """x (n,) convolved with a stereo ir (k, 2) -> (n, 2), cut to n."""
    n = len(x) + len(ir)
    m = 1 << int(math.ceil(math.log2(n)))
    X = np.fft.rfft(x, m)
    return np.stack([np.fft.irfft(X * np.fft.rfft(ir[:, c], m), m)[:len(x)] for c in range(2)], 1).astype(np.float32)


def envelope(x, seconds):
    """RMS envelope of a mono signal over a centred window."""
    k = max(1, int(seconds * RATE))
    c = np.concatenate([[0.0], np.cumsum(x.astype(np.float64) ** 2)])
    i = np.arange(len(x))
    lo, hi = np.clip(i - k // 2, 0, len(x)), np.clip(i + k // 2 + 1, 0, len(x))
    return np.sqrt((c[hi] - c[lo]) / (hi - lo)).astype(np.float32)


# ---------- listener ----------

def listener(n, frames=480, duration=20.0, res=None, move="orbit"):
    """Camera position (n, 3) and right vector (n, 3) at each output sample.

    Mirrors build_scene.camera_ref (the start pose) and render_orbit.Turn.pose (the turn), or
    descent.pose (the descent).
    """
    import render_orbit as ro
    trace = location.load("trace.json")["camera"]
    if res is None:
        res = location.load("layout_preview.json")["render"]["resolution"]
    if move == "descent":
        return _descent_listener(n, frames, duration, res)
    th, ps, s = math.radians(trace["elevation_deg"]), math.radians(trace["yaw_deg"]), trace["px_per_m"]
    view = np.array([math.cos(th) * math.sin(ps), math.cos(th) * math.cos(ps), -math.sin(th)])
    right = np.array([math.cos(ps), -math.sin(ps), 0.0])
    up = np.array([math.sin(th) * math.sin(ps), math.sin(th) * math.cos(ps), math.cos(th)])
    cu, cv = trace["center_px"]
    loc0 = right * ((res[0] / 2 - cu) / s) + up * ((cv - res[1] / 2) / s) - view * ro.CAM_DIST
    rot0 = np.column_stack([right, up, -view])
    pivot = np.array([ro.PIVOT[0], ro.PIVOT[1], 0.0])
    pivot_local = rot0.T @ (pivot - loc0)

    # control points at 200 Hz, then interpolated per sample
    secs = np.linspace(0, n / RATE, max(2, int(n / RATE * 200)))
    pos, rgt = [], []
    for sec in secs:
        t = min(sec * frames / (duration * (frames - 1)), 1.0)
        a = math.radians(ro.yaw_deg(t))
        rz = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
        rot = rz @ rot0
        w = math.sin(math.pi * t) ** 2
        loc = rz @ (loc0 - pivot) + pivot + rot @ np.array([pivot_local[0] * w, pivot_local[1] * w, 0.0])
        loc = loc + np.array(ro.drift(t)[:3])
        pos.append(loc)
        rgt.append(rot[:, 0])
    pos, rgt = np.array(pos), np.array(rgt)
    ts = np.arange(n) / RATE
    interp = lambda v: np.column_stack([np.interp(ts, secs, v[:, k]) for k in range(3)])
    return interp(pos), interp(rgt)


def _descent_listener(n, frames, duration, res):
    import descent
    width0 = res[0] / location.load("trace.json")["camera"]["px_per_m"]
    # the point the camera looks at, where its view meets the descent's focus path (z of the ground)
    focus = lambda loc, view: loc + view * (-loc[2] / view[2]) if view[2] < -0.2 else loc + view * 12.0
    secs = np.linspace(0, n / RATE, max(2, int(n / RATE * 200)))
    pos, rgt = [], []
    for sec in secs:
        loc, view, lens = descent.pose(min(sec * frames / (duration * (frames - 1)), 1.0), res)
        # the long lens at the start is a framing trick: hear the scene from where the frame
        # looks like it is taken, the main view's 45 m, until the real camera comes closer
        dist = float(np.linalg.norm(loc - focus(loc, view)))
        heard = min(dist, 45.0 * (dist * descent.SENSOR / lens) / width0)
        loc = loc + view * (dist - heard)
        r = np.cross(view, (0.0, 0.0, 1.0))
        pos.append(loc)
        rgt.append(r / np.linalg.norm(r))
    pos, rgt = np.array(pos), np.array(rgt)
    ts = np.arange(n) / RATE
    interp = lambda v: np.column_stack([np.interp(ts, secs, v[:, k]) for k in range(3)])
    return interp(pos), interp(rgt)


# ---------- spatialization ----------

def pan_lr(pan):
    a = (np.clip(pan, -1, 1) + 1) * math.pi / 4
    return np.stack([np.cos(a), np.sin(a)], -1) * math.sqrt(2)


def spatialize(mono, start, src, cam, right, level):
    """Hear a mono source signal from the moving camera.

    mono: the signal as emitted, its sample 0 at time `start` (s, may be negative).
    Returns (direct (n, 2), reverb send (n,)), both n = len(cam) samples long.
    """
    n = len(cam)
    rel = np.asarray(src, float) - cam
    d = np.linalg.norm(rel, axis=1)
    # the sound reaching the camera at time t left the source at t - d / c
    t_emit = np.arange(n) / RATE - d / C_SOUND
    x = np.interp((t_emit - start) * RATE, np.arange(len(mono)), mono, left=0.0, right=0.0).astype(np.float32)
    gain = level * REF_DIST / d
    direct = sum(b * (10 ** (-a * d / 20)).astype(np.float32) for b, a in zip(bands(x), AIR_DB_PER_M)) * gain
    pan = (rel * right).sum(1) / d * 0.85
    send = x * level * 0.55       # filtered to the courtyard's colour in render_stems
    return direct[:, None] * pan_lr(pan).astype(np.float32), send


def courtyard_ir(seed=5):
    """Stereo impulse response of the stone courtyard: wall reflections, then a diffuse tail."""
    rng = np.random.default_rng(seed)
    length = int(1.6 * RATE)
    ir = np.zeros((length, 2), np.float32)
    # first-order image sources off each wall, seen from the courtyard centre, then second order
    cx, cy, cz = COURT_CENTRE
    first = [(2 * abs((cx if axis == "x" else cy) - c), 0.8 * min(1.0, h / 6.0))   # a low parapet reflects less
             for axis, c, h in COURT_WALLS]
    second = [(d1 + d2 + rng.uniform(-1.5, 1.5), 0.7 * g1 * g2)
              for i, (d1, g1) in enumerate(first) for d2, g2 in first[i + 1:]]
    for dist, g in first + second + [(2 * cz, 0.6)]:     # the last one: the wet cobbles
        i = int(dist / C_SOUND * RATE)
        for ch in range(2):
            ir[i + rng.integers(0, 40), ch] += g * rng.choice([-1, 1]) * 4.0 / max(dist, 4.0)
    early = float((ir ** 2).sum())
    # diffuse tail: decorrelated noise per channel, the highs decaying faster; 3x the early energy
    t = np.arange(length) / RATE
    onset = np.clip((t - 0.03) / 0.06, 0, 1)
    tail = np.zeros((length, 2), np.float32)
    noise = rng.standard_normal((length, 2)).astype(np.float32)
    for b, rt60 in zip(bands(noise, BAND_EDGES[:2]), (1.3, 1.0, 0.55)):
        tail += b * (onset * 10 ** (-3 * t / rt60))[:, None].astype(np.float32)
    ir += tail * np.sqrt(3 * early / float((tail ** 2).sum()))
    return ir / np.sqrt((ir ** 2).sum() / 2)


def gated(seg):
    """Band-pass 400 Hz-5 kHz and a downward expander: keeps the calls, drops the rain baked into the clip."""
    seg = fft_filter(seg, lambda f: highpass(400, 2)(f) * lowpass(5000, 2)(f))
    env = envelope(seg.mean(1), 0.03)
    thr = np.percentile(env, 70)
    return seg * (np.clip(env / thr, 0, 1) ** 2)[:, None]


# ---------- rain bed ----------

def rain_bed(n, ir, near=None):
    """The rain heard from far above; with `near` (n,) in 0..1, crossfaded to rain on the ground
    around the listener: the raw loops, drops and highs kept."""
    layers = [("rain_bed_t1_loop.wav", 0.0, False, 1.0), ("rain_bed_t2_loop.wav", 7.3, True, 1.0),
              ("rain_bed_t1_loop.wav", 13.9, True, 0.8), ("rain_roof_t1_loop.wav", 3.0, False, 0.45)]
    clips = {}
    bed = np.zeros((n, 2), np.float32)
    for name, off, swap, g in layers:
        clip = clips.setdefault(name, read_clip(name))
        x = looped(clip, n, off) * g
        bed += x[:, ::-1] if swap else x
    close = bed.copy()
    # flatten the drop transients: where the 4 ms level jumps over the 120 ms level, pull it down
    for ch in range(2):
        fast, slow = envelope(bed[:, ch], 0.004), envelope(bed[:, ch], 0.12)
        bed[:, ch] *= np.clip((slow / np.maximum(fast, 1e-6)) ** 0.7, 0.3, 1.0)
    # far away: highs gone, low rumble kept but not boomy
    bed = fft_filter(bed, lambda f: lowpass(3800, 2)(f) * (0.5 + 0.5 / np.sqrt(1 + (f / 6000) ** 4))
                     * highpass(70, 2)(f))
    # wash it through the courtyard and widen it
    wet = convolve(bed.mean(1), ir)
    bed = bed * 0.75 + wet * 0.45
    mid, side = (bed[:, 0] + bed[:, 1]) / 2, (bed[:, 0] - bed[:, 1]) / 2
    far = np.stack([mid + side * 1.35, mid - side * 1.35], 1) * FAR_BED
    if near is None:
        return far
    close = close * 0.8 + convolve(close.mean(1), ir) * 0.2
    w = np.sqrt(near)[:, None]
    return far * np.sqrt(1 - near)[:, None] + close * NEAR_BED * w


# ---------- mix ----------

def render_stems(frames=480, duration=20.0, move="orbit"):
    """Every source of the mix as its own stereo track at mix gain, before scaling: {name: (n, 2)}."""
    n = int(round(duration * RATE))
    cam, right = listener(n, frames, duration, move=move)
    ir = courtyard_ir()
    # rain on the ground around the listener takes over below NEAR_HEIGHT[1] m
    lo, hi = NEAR_HEIGHT
    near = np.clip((hi - cam[:, 2]) / (hi - lo), 0, 1) if move == "descent" else None
    stems = {"rain_bed": rain_bed(n, ir, near)}
    send = np.zeros(n, np.float32)
    pre = int(PRE_ROLL * RATE)

    for name, (clip, src, level, off) in SOURCES.items():
        mono = looped(read_clip(clip), n + pre, off).mean(1)
        direct, s = spatialize(mono, -PRE_ROLL, src, cam, right, level)
        stems[name] = direct
        send += s

    for name, clip, (start, length), src, level, after_pass, gate in CUES:
        seg = segment(read_clip(clip), start, length)
        if gate:
            seg = gated(seg)
        mono = seg.mean(1)
        dist = np.linalg.norm(np.asarray(src) - cam, axis=1)
        arrive = int(np.argmin(dist)) / RATE + after_pass
        d = dist[min(max(int(arrive * RATE), 0), n - 1)]
        t0 = arrive - d / C_SOUND - length / 2
        direct, s = spatialize(mono, t0, src, cam, right, level)
        stems[name] = stems.get(name, 0) + direct
        send += s

    # the reverb arrives after a longer path than the direct sound: darker
    stems["reverb"] = convolve(fft_filter(send, lowpass(5000, 2)), ir) * 0.5
    return stems


def mix_stems(stems):
    mix = sum(stems.values()).astype(np.float32)
    mix *= 10 ** (MIX_RMS_DB / 20) / float(np.sqrt((mix ** 2).mean()))
    mix = np.tanh(mix / 0.9) * 0.9
    fi, fo = int(1.5 * RATE), int(2.5 * RATE)
    mix[:fi] *= (np.sin(np.linspace(0, math.pi / 2, fi)) ** 2)[:, None]
    mix[-fo:] *= (np.cos(np.linspace(0, math.pi / 2, fo)) ** 2)[:, None]
    return mix


def write_wav(path, mix):
    pcm = (np.clip(mix, -1, 1) * 32767).astype("<i2")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())


def write_mix(path, frames=480, duration=20.0, move="orbit"):
    mix = mix_stems(render_stems(frames, duration, move))
    write_wav(path, mix)
    print(f"ORBIT sound {duration:.1f}s -> {path}", flush=True)
    return mix


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(ROOT / "renders" / "orbit" / "orbit.wav"))
    ap.add_argument("--frames", type=int, default=480)
    ap.add_argument("--duration", type=float, default=20.0)
    ap.add_argument("--move", choices=("orbit", "descent"), default="orbit")
    args = ap.parse_args()
    write_mix(args.out, args.frames, args.duration, args.move)


if __name__ == "__main__":
    main()

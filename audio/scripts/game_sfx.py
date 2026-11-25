#!/usr/bin/env python3
"""Measure, cut and normalize the game sounds (prompts.json -> game_sfx).

Run with the Stable Audio 3 venv python (numpy + soundfile) and ffmpeg on PATH:
  <sa3-venv>/bin/python audio/scripts/game_sfx.py stats    # every take: level, clipping, spectrum
  <sa3-venv>/bin/python audio/scripts/game_sfx.py steps    # cut single steps from the walking takes
  <sa3-venv>/bin/python audio/scripts/game_sfx.py finish PICKS.json   # trim, fade, normalize picks

Input: audio/sfx/game/<id>_t<k>.wav (raw takes). Output: audio/sfx/game/steps/ (cut steps),
audio/sfx/game/final/ (game files) and TSV reports next to them.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from postprocess import ebur128  # noqa: E402

AUDIO = Path(__file__).resolve().parent.parent
GAME = AUDIO / "sfx" / "game"
SR = 44100
STEP_TARGET = -24.0     # K-weighted loudness of the first 300 ms of every step (dB)
STEP_PEAK = -1.0        # sample peak ceiling of a step (dBFS)
# EQ per surface before levelling: the stair takes carry a low boom that stone does not
# have; the wood takes carry sub-bass below the board knock
STEP_EQ = {"stone_stair": "highpass=f=120,lowshelf=f=350:g=-6",
           "wood": "highpass=f=70"}
KEEP = 8                # steps kept per surface
# target timbre per surface: spectral centroid (Hz) and energy share below 500 Hz
PROFILE = {"cobble": (1900, 0.03), "mud": (1000, 0.40), "puddle": (2200, 0.02),
           "stone_stair": (1800, 0.12), "stone_walk": (2000, 0.08), "wood": (260, 0.85),
           "straw": (3300, 0.15)}


# ---------- filters ----------

def biquad(x, b, a):
    """Direct form I biquad over a mono float64 array (no scipy in the venv)."""
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    b0, b1, b2 = b
    _, a1, a2 = a
    for i in range(len(x)):
        xi = x[i]
        yi = b0 * xi + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, xi, y1, yi
        y[i] = yi
    return y


def _k_coeffs(fs=SR):
    """ITU-R BS.1770 K-weighting biquads for sample rate fs (pre-filter shelf, RLB high-pass)."""
    f0, g, q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    k = np.tan(np.pi * f0 / fs)
    vh = 10 ** (g / 20)
    vb = vh ** 0.4996667741545416
    a0 = 1 + k / q + k * k
    shelf = ((vh + vb * k / q + k * k) / a0, 2 * (k * k - vh) / a0, (vh - vb * k / q + k * k) / a0), \
            (1.0, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0)
    f0, q = 38.13547087602444, 0.5003270373238773
    k = np.tan(np.pi * f0 / fs)
    a0 = 1 + k / q + k * k
    hp = (1.0, -2.0, 1.0), (1.0, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0)
    return shelf, hp


K_SHELF, K_HP = _k_coeffs()


def k_weight(x):
    return biquad(biquad(x, *K_SHELF), *K_HP)


def k_loud(x):
    """K-weighted mean-square loudness of a (n, ch) block, in dB (LUFS-like, no gating)."""
    ms = sum(np.mean(k_weight(x[:, c].astype(np.float64)) ** 2) for c in range(x.shape[1]))
    return -0.691 + 10 * np.log10(ms + 1e-12)


def stereo(x):
    return x[:, None] if x.ndim == 1 else x


# ---------- spectrum ----------

def spectrum_stats(x):
    """Centroid, band shares, flatness and a sustained-tone score of a (n, ch) signal."""
    m = x.mean(axis=1)
    n_fft, hop = 2048, 512
    if len(m) < n_fft:
        m = np.pad(m, (0, n_fft - len(m)))
    frames = np.lib.stride_tricks.sliding_window_view(m, n_fft)[::hop] * np.hanning(n_fft)
    mag = np.abs(np.fft.rfft(frames, axis=1))
    f = np.fft.rfftfreq(n_fft, 1 / SR)
    p = mag ** 2
    e = p.sum(axis=1)
    loud = e > e.max() * 1e-3          # frames within 30 dB of the loudest
    P = p[loud].sum(axis=0)
    tot = P.sum() + 1e-20
    cen = float((P * f).sum() / tot)
    low = float(P[f < 500].sum() / tot)
    lowmid = float(P[(f >= 150) & (f < 600)].sum() / tot)
    high = float(P[f >= 4000].sum() / tot)
    band = (f > 80) & (f < 5000)
    pl = p[loud][:, band] + 1e-20
    flat = float(np.mean(np.exp(np.mean(np.log(pl), axis=1)) / np.mean(pl, axis=1)))
    # sustained tone: a bin standing >18 dB above its neighbourhood median for >=12 frames
    # in a row (~140 ms). Music, voices and whistles light this up; impacts and noise do not.
    db = 10 * np.log10(p[:, band] + 1e-20)
    k = 15
    pad = np.pad(db, ((0, 0), (k, k)), mode="edge")
    med = np.median(np.lib.stride_tricks.sliding_window_view(pad, 2 * k + 1, axis=1), axis=2)
    peak = (db - med > 18) & loud[:, None]
    run = np.zeros(peak.shape[1], int)
    best = np.zeros(peak.shape[1], int)
    for row in peak:
        run = np.where(row, run + 1, 0)
        best = np.maximum(best, run)
    tonal_bins = int((best >= 12).sum())
    fb = f[band]
    tone_hz = sorted({int(round(fb[i] / 10) * 10) for i in np.argsort(best)[::-1][:3] if best[i] >= 12})
    return {"centroid_hz": round(cen), "below_500": round(low, 3), "150_600": round(lowmid, 3),
            "above_4k": round(high, 3), "flatness": round(flat, 3), "tonal_bins": tonal_bins,
            "tone_hz": tone_hz}


def decay_ms(x, onset=0):
    """Time from the envelope peak to 30 dB below it (ms), 5 ms RMS envelope."""
    m = np.abs(x.mean(axis=1))[onset:]
    w = int(0.005 * SR)
    env = np.sqrt(np.convolve(m ** 2, np.ones(w) / w, mode="same"))
    i = int(np.argmax(env))
    below = np.nonzero(env[i:] < env[i] * 10 ** (-30 / 20))[0]
    return round(1000 * below[0] / SR) if len(below) else None


def ffmpeg_filter(y, af):
    """Run a (n, ch) float array through an ffmpeg audio filter chain."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        a, b = Path(d) / "a.wav", Path(d) / "b.wav"
        sf.write(a, y.astype(np.float32), SR, subtype="FLOAT")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(a), "-af", af, "-c:a", "pcm_f32le",
                        str(b)], check=True)
        z, _ = sf.read(b, dtype="float64", always_2d=True)
    return z[:len(y)]


def clipped(x):
    return int((np.abs(x) >= 0.999).sum())


# ---------- onsets ----------

def onsets(x, min_gap=0.32):
    """Step onsets (samples): positive spectral flux above 150 Hz, peak-picked with an
    adaptive threshold, refined to the first 1 ms block whose envelope passes 20 % of the
    following 60 ms peak."""
    m = x.mean(axis=1)
    n_fft, hop = 1024, 256
    frames = np.lib.stride_tricks.sliding_window_view(m, n_fft)[::hop] * np.hanning(n_fft)
    mag = np.log1p(100 * np.abs(np.fft.rfft(frames, axis=1)))
    f = np.fft.rfftfreq(n_fft, 1 / SR)
    mag = mag[:, f > 150]
    flux = np.maximum(np.diff(mag, axis=0), 0).sum(axis=1)
    flux = np.concatenate([[0], flux])
    med = np.median(flux)
    mad = np.median(np.abs(flux - med)) + 1e-9
    thr = med + 6 * mad
    gap = int(min_gap * SR / hop)
    picks = []
    for i in np.argsort(flux)[::-1]:
        if flux[i] < thr:
            break
        if all(abs(i - j) >= gap for j in picks):
            picks.append(i)
    out = []
    env = np.abs(m)
    for i in sorted(picks):
        s0 = max(0, i * hop - n_fft // 2)
        s1 = min(len(m), i * hop + n_fft + int(0.06 * SR))
        seg = env[s0:s1]
        if not len(seg):
            continue
        pk = seg.max()
        blk = int(0.001 * SR)
        nb = len(seg) // blk
        bmax = seg[:nb * blk].reshape(nb, blk).max(axis=1)
        first = int(np.argmax(bmax > 0.2 * pk))
        out.append(s0 + first * blk)
    return out


# ---------- commands ----------

def items():
    return json.loads((AUDIO / "prompts.json").read_text())["game_sfx"]


def takes_of(it, current=False):
    """Raw takes of an item. current=True leaves out takes made with a superseded prompt
    (items with "takes_v1" keep their first-prompt takes as t1 and t2)."""
    t = sorted(GAME.glob(f"{it['id']}_t[0-9].wav"))
    if current and "takes_v1" in it:
        t = [w for w in t if int(w.stem.rsplit("_t", 1)[1]) > 2]
    return t


def cmd_stats():
    rows = []
    for it in items():
        for wav in takes_of(it):
            x, sr = sf.read(wav, dtype="float32", always_2d=True)
            lufs, tp = ebur128(wav)
            s = spectrum_stats(x)
            r = {"file": wav.name, "lufs": lufs, "peak_dbfs": tp, "clipped": clipped(x),
                 "decay_ms": decay_ms(x), "onsets": len(onsets(x)), **s}
            rows.append(r)
            print(json.dumps(r), flush=True)
    keys = list(rows[0])
    with (GAME / "_stats.tsv").open("w") as f:
        f.write("\t".join(keys) + "\n")
        for r in rows:
            f.write("\t".join(str(r[k]) for k in keys) + "\n")


def cut_steps(wav, max_len=0.62, pre=0.004, fade=0.12):
    """Single steps from one walking take. A step runs from its onset to the next onset
    (at most max_len s); the last `fade` s get a cosine fade so the natural tail stays."""
    x, _ = sf.read(wav, dtype="float32", always_2d=True)
    x = x.astype(np.float64)
    ons = onsets(x)
    steps = []
    for k, o in enumerate(ons):
        a = max(0, o - int(pre * SR))
        nxt = ons[k + 1] if k + 1 < len(ons) else len(x)
        b = min(a + int(max_len * SR), nxt - int(0.015 * SR))
        if o < int(0.05 * SR):
            steps.append({"onset_s": round(o / SR, 3), "reject": "starts with the take (attack may be cut)"})
            continue
        if b - a < int(0.22 * SR):
            steps.append({"onset_s": round(o / SR, 3), "reject": "next event within 220 ms"})
            continue
        y = x[a:b].copy()
        n_f = min(int(fade * SR), len(y) // 2)
        y[-n_f:] *= (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, n_f)))[:, None]
        n_in = int(pre * SR)
        y[:n_in] *= np.linspace(0, 1, n_in)[:, None]
        # overlap: energy before the onset (previous step's tail) relative to the step body
        pre_win = x[max(0, o - int(0.08 * SR)):o]
        body = y[n_in:n_in + int(0.15 * SR)]
        pre_db = 10 * np.log10(np.mean(pre_win ** 2) + 1e-12) - 10 * np.log10(np.mean(body ** 2) + 1e-12)
        # tail: level of the last 50 ms before the fade against the body
        t = y[-n_f - int(0.05 * SR):-n_f]
        tail_db = 10 * np.log10(np.mean(t ** 2) + 1e-12) - 10 * np.log10(np.mean(body ** 2) + 1e-12)
        steps.append({"onset_s": round(o / SR, 3), "len_s": round(len(y) / SR, 3),
                      "pre_db": round(float(pre_db), 1), "tail_db": round(float(tail_db), 1),
                      "peak": round(float(np.abs(y).max()), 3),
                      "loud": round(float(k_loud(y[:int(0.3 * SR)])), 1), "audio": y})
    return steps


def cmd_steps():
    out_dir = GAME / "steps"
    out_dir.mkdir(exist_ok=True)
    report = {}
    for it in items():
        if it["group"] != "steps":
            continue
        cand = []
        for wav in takes_of(it, current=True):
            for st in cut_steps(wav):
                st["take"] = wav.stem
                cand.append(st)
        ok = [c for c in cand if "reject" not in c]
        for c in ok:
            why = []
            if c["pre_db"] > -10:
                why.append(f"overlaps previous step ({c['pre_db']} dB before onset)")
            if c["tail_db"] > -6:
                why.append(f"cut while still sounding (tail {c['tail_db']} dB)")
            if c["peak"] >= 0.999:
                why.append("clipped")
            if why:
                c["reject"] = "; ".join(why)
        ok = [c for c in ok if "reject" not in c]
        # consistent level: drop the steps far from the median loudness of the surface
        if ok:
            # reference: the 75th percentile, so faint scuffs picked as onsets do not pull it down
            ref = float(np.percentile([c["loud"] for c in ok], 75))
            for c in ok:
                if c["loud"] < ref - 8:
                    c["reject"] = f"faint event, {c['loud'] - ref:+.1f} dB below the surface's steps"
                elif c["loud"] > ref + 6:
                    c["reject"] = f"stomp, {c['loud'] - ref:+.1f} dB above the surface's steps"
            ok = [c for c in ok if "reject" not in c]
        # timbre: keep the steps nearest the surface's profile, so a surface sounds like one
        # material and the surfaces stay apart (mud dull, stone crisp, wood hollow)
        surface = it["id"].removeprefix("steps_")
        tc, tl = PROFILE[surface]
        for c in ok:
            c["spec"] = spectrum_stats(c["audio"])
            c["dist"] = round(abs(np.log2(c["spec"]["centroid_hz"] / tc))
                              + 4 * abs(c["spec"]["below_500"] - tl), 3)
        ok.sort(key=lambda c: c["dist"])
        keep = sorted(ok[:KEEP], key=lambda c: (c["take"], c["onset_s"]))
        for c in cand:
            if "reject" not in c and c not in keep:
                c["reject"] = f"spare (the {KEEP} nearest the surface profile are kept)"
        for n, c in enumerate(keep, 1):
            y = c["audio"]
            if surface in STEP_EQ:
                y = ffmpeg_filter(y, STEP_EQ[surface])
                c["loud"] = round(float(k_loud(y[:int(0.3 * SR)])), 1)
            y = y * 10 ** ((STEP_TARGET - c["loud"]) / 20)
            pk = np.abs(y).max()
            ceil = 10 ** (STEP_PEAK / 20)
            if pk > ceil:
                y *= ceil / pk
            c["file"] = f"{surface}_{n:02d}.wav"
            sf.write(out_dir / c["file"], y.astype(np.float32), SR, subtype="PCM_16")
            c["spec"] = spectrum_stats(y)
            c["decay_ms"] = decay_ms(y)
        report[surface] = [{k: v for k, v in c.items() if k != "audio"} for c in cand]
        print(surface, f"{len(cand)} onsets, {len(keep)} kept", flush=True)
    (out_dir / "_steps.json").write_text(json.dumps(report, indent=1) + "\n")
    # per-surface spectral summary of the kept steps
    with (out_dir / "_surfaces.tsv").open("w") as f:
        f.write("surface\tsteps\tcentroid_hz\tbelow_500\t150_600\tabove_4k\tflatness\tdecay_ms\tlen_s\n")
        for s, cs in report.items():
            k = [c for c in cs if "file" in c]
            if not k:
                continue
            avg = lambda key: np.mean([c["spec"][key] for c in k])
            f.write(f"{s}\t{len(k)}\t{avg('centroid_hz'):.0f}\t{avg('below_500'):.3f}\t"
                    f"{avg('150_600'):.3f}\t{avg('above_4k'):.3f}\t{avg('flatness'):.3f}\t"
                    f"{np.mean([c['decay_ms'] or 0 for c in k]):.0f}\t"
                    f"{np.mean([c['len_s'] for c in k]):.2f}\n")
    print((out_dir / "_surfaces.tsv").read_text())


def trim(x, start_s, end_s, thresh_db=-50):
    """Cut to [start_s, end_s] (end None = file end), then drop leading silence and the
    tail below thresh_db, keep 5 ms before the first sound, 2 ms fade in, 60 ms fade out."""
    a = int(start_s * SR)
    b = len(x) if end_s is None else int(end_s * SR)
    y = x[a:b].copy()
    env = np.abs(y).max(axis=1)
    ref = env.max()
    on = np.nonzero(env > ref * 10 ** (thresh_db / 20))[0]
    s0 = max(0, on[0] - int(0.005 * SR))
    s1 = min(len(y), on[-1] + int(0.02 * SR))
    y = y[s0:s1]
    n_in = int(0.002 * SR)
    y[:n_in] *= np.linspace(0, 1, n_in)[:, None]
    n_out = min(int(0.06 * SR), len(y) // 4)
    y[-n_out:] *= (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, n_out)))[:, None]
    return y


def cmd_finish(picks_path):
    """PICKS.json: {"out/name.wav": {"take": "<id>_t<k>", "start": s, "end": s|null,
    "target": LUFS}}. Writes audio/sfx/game/final/<out/name.wav> normalized like
    postprocess.py (30 Hz high-pass, two-pass loudnorm, limiter fallback)."""
    from postprocess import loudnorm
    import postprocess
    picks = json.loads(Path(picks_path).read_text())
    final = GAME / "final"
    tmp = GAME / ".tmp"
    tmp.mkdir(exist_ok=True)
    rows = []
    for out, p in picks.items():
        x, _ = sf.read(GAME / f"{p['take']}.wav", dtype="float64", always_2d=True)
        y = trim(x, p.get("start", 0), p.get("end"))
        t = tmp / Path(out).name
        sf.write(t, y.astype(np.float32), SR, subtype="FLOAT")
        dst = final / out
        dst.parent.mkdir(parents=True, exist_ok=True)
        postprocess.TARGET = p.get("target", -16.0)
        if len(y) / SR < 0.45:
            # too short for loudness gating: K-weighted level plus peak ceiling
            g = postprocess.TARGET - k_loud(y)
            z = y * 10 ** (g / 20)
            pk = np.abs(z).max()
            if pk > 10 ** (-1 / 20):
                z *= 10 ** (-1 / 20) / pk
            sf.write(dst, z.astype(np.float32), SR, subtype="PCM_16")
            lufs, tp, method = round(k_loud(z), 1), round(20 * np.log10(np.abs(z).max()), 1), "k-gain"
        else:
            lufs, tp, method = loudnorm(t, dst, "highpass=f=30,")
        rows.append([out, p["take"], f"{len(y) / SR:.2f}", f"{lufs:.1f}", f"{tp:.1f}", method])
        print(*rows[-1], flush=True)
    with (final / "_levels.tsv").open("a") as f:
        for r in rows:
            f.write("\t".join(r) + "\n")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    {"stats": cmd_stats, "steps": cmd_steps}.get(cmd, lambda: cmd_finish(sys.argv[2]))()

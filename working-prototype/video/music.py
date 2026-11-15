"""A short, original, feel-good backing track, written in code so it carries no licence.

Usage: python3 music.py SECONDS OUT.wav

Four bright chords (C, G, A minor, F) at 104 beats a minute: plucked arpeggios, a warm
pad, a walking bass, a soft kick and a shaker. It opens gently and gains the drums
after eight bars, then fades out at the end.
"""

import sys
import wave

import numpy as np

SR = 48_000
BPM = 104
BEAT = 60 / BPM
BAR = 4 * BEAT
CHORDS = [  # semitones above C4 for each chord's notes; bass root in semitones above C2
    ([0, 4, 7, 12], 0),  # C
    ([-5, -1, 2, 7], 7),  # G
    ([-3, 0, 4, 9], 9),  # A minor
    ([-7, -3, 0, 5], 5),  # F
]
C4 = 261.63


def freq(semitones_from_c4: float) -> float:
    return C4 * 2 ** (semitones_from_c4 / 12)


_PLUCKS: dict[tuple[int, int], np.ndarray] = {}


def pluck(f: float, dur: float, rng: np.random.Generator) -> np.ndarray:
    """Karplus-Strong plucked string, computed once per note and length."""
    key = (round(f * 100), round(dur * 1000))
    if key not in _PLUCKS:
        _PLUCKS[key] = _pluck(f, dur, rng)
    return _PLUCKS[key]


def _pluck(f: float, dur: float, rng: np.random.Generator) -> np.ndarray:
    n = int(SR * dur)
    period = max(2, int(SR / f))
    # A softened burst: filtered noise gives a warm, nylon-like pluck instead of a click.
    buf = rng.uniform(-1, 1, period)
    for _ in range(3):
        buf = np.convolve(buf, [0.25, 0.5, 0.25], mode="same")
    buf /= np.max(np.abs(buf)) + 1e-9
    out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % period]
        buf[i % period] = 0.996 * 0.5 * (buf[i % period] + buf[(i + 1) % period])
    attack = min(n, int(SR * 0.006))
    out[:attack] *= np.linspace(0, 1, attack)
    return out * np.exp(-np.linspace(0, 3.5, n))


def pad(fs: list[float], dur: float) -> np.ndarray:
    t = np.arange(int(SR * dur)) / SR
    tone = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t + 0.3) for f in fs)
    env = np.minimum(1, t / 0.6) * np.minimum(1, (dur - t) / 0.6)
    return tone * env / len(fs)


def kick(dur: float = 0.35) -> np.ndarray:
    t = np.arange(int(SR * dur)) / SR
    return np.sin(2 * np.pi * (55 + 90 * np.exp(-t * 30)) * t) * np.exp(-t * 9)


def shaker(rng: np.random.Generator, dur: float = 0.08) -> np.ndarray:
    n = int(SR * dur)
    noise = rng.uniform(-1, 1, n)
    noise = np.convolve(noise, [0.5, 0.5], mode="same")  # take the hiss off the top
    return noise * np.exp(-np.linspace(0, 6, n))


def place(track: np.ndarray, clip: np.ndarray, at: float, gain: float) -> None:
    i = int(at * SR)
    j = min(len(track), i + len(clip))
    if i < len(track):
        track[i:j] += gain * clip[: j - i]


def main() -> None:
    seconds = float(sys.argv[1])
    out = sys.argv[2]
    rng = np.random.default_rng(7)
    n = int(SR * (seconds + 2))
    left, right = np.zeros(n), np.zeros(n)
    bars = int(seconds / BAR) + 1
    pattern = [0, 2, 1, 3, 2, 1, 3, 2]  # arpeggio order over eighth notes
    for b in range(bars):
        notes, root = CHORDS[b % 4]
        t0 = b * BAR
        p = pad([freq(x - 12) for x in notes[:3]], BAR + 0.3)
        place(left, p, t0, 0.10)
        place(right, p, t0, 0.10)
        for k, idx in enumerate(pattern):
            note = notes[idx] + (12 if b % 8 >= 4 and k % 4 == 3 else 0)
            clip = pluck(freq(note), BEAT * 1.6, rng)
            pan = 0.35 + 0.3 * (k % 2)
            place(left, clip, t0 + k * BEAT / 2, 0.22 * (1 - pan))
            place(right, clip, t0 + k * BEAT / 2, 0.22 * pan)
        for k, step in enumerate([0, 0, 7, 5]):
            bass = pluck(freq(root + step - 24), BEAT * 1.2, rng)
            place(left, bass, t0 + k * BEAT, 0.30)
            place(right, bass, t0 + k * BEAT, 0.30)
        if b >= 8:
            for k in range(4):
                if k in (0, 2):
                    place(left, kick(), t0 + k * BEAT, 0.35)
                    place(right, kick(), t0 + k * BEAT, 0.35)
            for k in range(8):
                sh = shaker(rng)
                place(left, sh, t0 + k * BEAT / 2 + 0.01, 0.05 if k % 2 else 0.03)
                place(right, sh, t0 + k * BEAT / 2, 0.03 if k % 2 else 0.05)
    stereo = np.stack([left, right], axis=1)[: int(SR * seconds)]
    fade_in, fade_out = int(SR * 2.5), int(SR * 6)
    stereo[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    stereo[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None]
    stereo /= np.max(np.abs(stereo)) + 1e-9
    pcm = (stereo * 0.8 * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"wrote {out}: {seconds:.0f} s")


if __name__ == "__main__":
    main()

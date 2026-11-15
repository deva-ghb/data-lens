"""A soft, original backing track, written in code so it carries no licence.

Usage: python3 music.py SECONDS OUT.wav

Slow and warm, for sitting under a narrator: 68 beats a minute, a felt-piano sound
playing gentle broken chords over a sustained pad, with a little room reverb. The
chords (C major 7, A minor 7, F major 7, G with a suspended fourth) move once a bar.
No drums. It fades in over four seconds and out over eight.
"""

import sys
import wave

import numpy as np

SR = 48_000
BPM = 68
BEAT = 60 / BPM
BAR = 4 * BEAT
C4 = 261.63
# Chord tones in semitones above C4, low to high.
CHORDS = [
    [-12, 0, 4, 7, 11],   # Cmaj7
    [-15, -3, 0, 4, 7],   # Am7
    [-19, -7, -3, 0, 4],  # Fmaj7
    [-17, -5, 0, 2, 7],   # Gsus4 colour
]
# A slow, rocking figure over each bar: which chord tone, on which eighth note.
FIGURE = [(1, 0), (3, 1), (2, 2), (4, 3), (3, 4), (2, 5), (3, 6), (4, 7)]


def freq(semitones: float) -> float:
    return C4 * 2 ** (semitones / 12)


_NOTES: dict[tuple[int, int], np.ndarray] = {}


def piano(f: float, dur: float) -> np.ndarray:
    """A soft, felted piano tone: a few gentle harmonics, a slow attack and a long decay."""
    key = (round(f * 100), round(dur * 1000))
    if key not in _NOTES:
        t = np.arange(int(SR * dur)) / SR
        tone = (
            np.sin(2 * np.pi * f * t)
            + 0.28 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 2.5)
            + 0.10 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t * 4.0)
        )
        env = np.minimum(1, t / 0.025) * np.exp(-t * 1.1)
        release = np.minimum(1, (dur - t) / 0.3)
        _NOTES[key] = tone * env * release
    return _NOTES[key]


def pad(fs: list[float], dur: float) -> np.ndarray:
    t = np.arange(int(SR * dur)) / SR
    tone = sum(
        np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.003 * t)  # slight chorus
        for f in fs
    )
    env = np.minimum(1, t / 1.6) * np.minimum(1, (dur - t) / 1.6)
    return tone * env / (1.5 * len(fs))


def reverb(x: np.ndarray, seconds: float = 2.2, mix: float = 0.22) -> np.ndarray:
    """A small room: convolve with a short burst of decaying, softened noise."""
    rng = np.random.default_rng(3)
    n = int(SR * seconds)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 7, n))
    ir = np.convolve(ir, np.ones(24) / 24, mode="same")  # take the hiss off
    ir /= np.sqrt(np.sum(ir**2))
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return (1 - mix) * x + mix * wet


def place(track: np.ndarray, clip: np.ndarray, at: float, gain: float) -> None:
    i = max(0, int(at * SR))
    j = min(len(track), i + len(clip))
    if i < len(track):
        track[i:j] += gain * clip[: j - i]


def main() -> None:
    seconds = float(sys.argv[1])
    out = sys.argv[2]
    n = int(SR * (seconds + 4))
    left, right = np.zeros(n), np.zeros(n)
    bars = int(seconds / BAR) + 2
    for b in range(bars):
        notes = CHORDS[b % 4]
        t0 = b * BAR
        p = pad([freq(x) for x in notes[:4]], BAR + 1.6)
        place(left, p, t0 - 0.8, 0.16)
        place(right, p, t0 - 0.8, 0.16)
        low = piano(freq(notes[0] - 12), BAR * 1.1)  # a soft low note per bar
        place(left, low, t0, 0.20)
        place(right, low, t0, 0.20)
        for idx, eighth in FIGURE:
            if b % 8 in (6, 7) and eighth % 2:  # every eighth bar, leave more space
                continue
            note = piano(freq(notes[idx]), BEAT * 3)
            pan = 0.35 + 0.3 * ((eighth + b) % 2)
            place(left, note, t0 + eighth * BEAT / 2, 0.32 * (1 - pan))
            place(right, note, t0 + eighth * BEAT / 2, 0.32 * pan)
    left, right = reverb(left), reverb(right)
    stereo = np.stack([left, right], axis=1)[: int(SR * seconds)]
    fade_in, fade_out = int(SR * 4), int(SR * 8)
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

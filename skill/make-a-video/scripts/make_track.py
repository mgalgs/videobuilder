#!/usr/bin/env python3
"""Make a simple music bed in code: a WAV whose beats sit exactly on a grid.

    python make_track.py --bpm 120 --beats 40 --out assets/music.wav

Four voices, all optional: a kick on every beat, a hat on the off-beats, a
bass note per bar and a soft chord pad, following a chord loop. The first
beat is at 0 s, so the film's `Grid(head_trim=0)` lines up with it; `--lead`
adds silence before the first beat (and prints the head_trim that skips it).
The same arguments always give the same file. Pure Python, no numpy.

The sound is a placeholder bed for timing: a film that needs real music
should use a licensed track, set its BPM and head_trim, and check it with
check.py --video.
"""
import argparse
import array
import math
import random
import wave

# Chord loops as semitones above A2 (110 Hz): root, then the pad's notes.
LOOPS = {
    'minor': [(0, (12, 15, 19)), (8, (20, 24, 27)), (3, (15, 19, 22)), (10, (22, 26, 29))],
    'major': [(3, (15, 19, 22)), (10, (22, 26, 29)), (0, (12, 15, 19)), (8, (20, 24, 27))],
    'drone': [(0, (12, 19, 24))],
}


def hz(semi):
    return 110.0 * 2 ** (semi / 12)


def synth(bpm, beats, rate=48000, lead=0.0, tail=0.0, loop='minor', voices=('kick', 'hat', 'bass', 'pad'),
          bar=4, seed=1):
    spb = 60.0 / bpm
    n = int(rate * (lead + beats * spb + tail))
    out = [0.0] * n
    rnd = random.Random(seed)
    noise = [rnd.uniform(-1, 1) for _ in range(int(rate * 0.05))]
    chords = LOOPS[loop]

    def add(start, length, fn):
        a = int(start * rate)
        for i in range(max(0, a), min(n, a + int(length * rate))):
            out[i] += fn((i - a) / rate)

    for k in range(beats):
        t = lead + k * spb
        if 'kick' in voices:
            def kick(x):  # a pitch-dropping sine thump
                f = 50 + 90 * math.exp(-x * 30)
                return 0.55 * math.exp(-x * 9) * math.sin(2 * math.pi * f * x)
            add(t, 0.35, kick)
        if 'hat' in voices:
            add(t + spb / 2, 0.05, lambda x: 0.12 * math.exp(-x * 80) * noise[int(x * rate) % len(noise)])
        root, pad = chords[(k // bar) % len(chords)]
        if 'bass' in voices and k % 2 == 0:
            f = hz(root - 12)
            add(t, spb * 1.9, lambda x, f=f: 0.18 * math.exp(-x * 2.5) * math.sin(2 * math.pi * f * x))
        if 'pad' in voices and k % bar == 0:
            fs = [hz(s) for s in pad]
            length = spb * bar
            add(t, length, lambda x, fs=fs, L=length: 0.08 * min(1, x / 0.3, (L - x) / 0.3)
                * sum(math.sin(2 * math.pi * f * x) for f in fs))
    peak = max(1e-9, max(abs(v) for v in out))
    g = min(1.0, 0.9 / peak)
    return array.array('h', (int(v * g * 32767) for v in out))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--bpm', type=float, required=True)
    p.add_argument('--beats', type=int, required=True, help="the film's length in beats (TIMELINE.end)")
    p.add_argument('--out', required=True)
    p.add_argument('--loop', choices=sorted(LOOPS), default='minor')
    p.add_argument('--voices', default='kick,hat,bass,pad', help='comma-separated: kick, hat, bass, pad')
    p.add_argument('--bar', type=int, default=4, help='beats per chord')
    p.add_argument('--lead', type=float, default=0.0, help='seconds of silence before the first beat')
    p.add_argument('--tail', type=float, default=1.0, help='seconds after the last beat (default 1)')
    p.add_argument('--fps', type=int, default=30, help='to print the head_trim for --lead')
    p.add_argument('--rate', type=int, default=48000)
    a = p.parse_args(argv)
    data = synth(a.bpm, a.beats, a.rate, a.lead, a.tail, a.loop, tuple(a.voices.split(',')), a.bar)
    with wave.open(a.out, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(a.rate)
        w.writeframes(data.tobytes())
    print(f'{a.out}: {a.beats} beats at {a.bpm:g} bpm, {len(data) / a.rate:.2f} s; '
          f'Grid(fps={a.fps}, bpm={a.bpm:g}, head_trim={round(a.lead * a.fps)})')


if __name__ == '__main__':
    main()

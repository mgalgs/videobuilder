#!/usr/bin/env python3
"""Estimate a music track's BPM and first beat, for the film's Grid.

    python tempo.py track.mp3 [--fps 30] [--bpm 120]

Prints the best tempo candidates and, for the best (or the `--bpm` you
give, if you know it), the time of the first beat and the `head_trim` that
puts it on frame 0. To start the film at a later beat (past an intro), add
that many beats: head_trim = round((first + k * 60 / bpm) * fps).

Estimates come from onsets (sudden rises in loudness), so they are good on
music with a clear pulse and unreliable on ambient pads. Check by ear, and
with check.py --video after a render. Pure Python; ffmpeg decodes the file.
"""
import argparse
import array
import math
import subprocess

RATE = 8000
HOP = RATE // 200  # 5 ms


def onsets(path, start=0.0, seconds=60.0):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(start), '-t', str(seconds), '-i', str(path),
                          '-map', '0:a:0', '-ac', '1', '-ar', str(RATE), '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    s = array.array('h')
    s.frombytes(raw[:len(raw) // 2 * 2])
    energy = [math.log(1e-3 + sum(x * x for x in s[i:i + HOP]) / HOP) for i in range(0, len(s) - HOP, HOP)]
    return [0.0] + [max(0.0, b - a) for a, b in zip(energy, energy[1:])]


def comb(onset, bpm, phase):
    """Mean onset strength on the beats of `bpm` starting at `phase` s."""
    spb = 60 / bpm
    total, k = 0.0, 0
    while True:
        i = round((phase + k * spb) * RATE / HOP)
        if i >= len(onset):
            break
        total += max(onset[max(0, i - 2):i + 3])
        k += 1
    return total / max(1, k)


def best_phase(onset, bpm):
    spb = 60 / bpm
    phases = [ms / 1000 for ms in range(0, int(spb * 1000), 5)]
    return max(((comb(onset, bpm, ph), ph) for ph in phases))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('track')
    p.add_argument('--fps', type=int, default=30)
    p.add_argument('--bpm', type=float, help='known tempo: only find the first beat')
    p.add_argument('--min', type=float, default=70)
    p.add_argument('--max', type=float, default=180)
    p.add_argument('--seconds', type=float, default=30, help='how much of the track to analyse (default 30)')
    a = p.parse_args(argv)
    onset = onsets(a.track, seconds=a.seconds)
    mean = sum(onset) / len(onset) or 1
    if a.bpm:
        bpm = a.bpm
    else:
        cands = []
        bpm = a.min
        while bpm <= a.max:
            cands.append((best_phase(onset, bpm)[0], bpm))
            bpm += 0.5
        cands.sort(reverse=True)
        print('tempo candidates (onset strength on the beat / mean):')
        shown = []
        for score, b in cands:
            if all(abs(b - s) > 2 for s in shown):
                shown.append(b)
                print(f'  {b:6.1f} bpm  {score / mean:.2f}')
            if len(shown) == 3:
                break
        bpm = shown[0]
        print('  (half or double the best is common: pick the one that matches the pulse you hear)')
    score, first = best_phase(onset, bpm)
    trim = round(first * a.fps)
    print(f'{bpm:g} bpm: first beat at {first:.3f} s (strength {score / mean:.2f}x mean)')
    print(f'Grid(fps={a.fps}, bpm={bpm:g}, head_trim={trim})   # {trim} frames = {trim / a.fps:.3f} s, '
          f'{(trim / a.fps - first) * 1000:+.0f} ms from the beat')


if __name__ == '__main__':
    main()

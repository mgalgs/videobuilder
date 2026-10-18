#!/usr/bin/env python3
"""Estimate a music track's BPM and first beat, for the film's Grid.

    python tempo.py track.mp3 [--fps 30] [--bpm 120]

A thin wrapper around `python -m videobuilder beats` (`videobuilder.beats`),
which does the finding and also prints the `beats` key for a film of clips'
timeline.json; use that where you can.

Prints the best tempo candidates and, for the best (or the `--bpm` you
give, if you know it), the time of the first beat and the `head_trim` that
puts it on frame 0. To start the film at a later beat (past an intro), add
that many beats: head_trim = round((first + k * 60 / bpm) * fps).

Estimates come from onsets (sudden rises in loudness), so they are good on
music with a clear pulse and unreliable on ambient pads. Check by ear, and
with check.py --video after a render. Pure Python; ffmpeg decodes the file.
"""
import argparse

from videobuilder import beats


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('track')
    p.add_argument('--fps', type=int, default=30)
    p.add_argument('--bpm', type=float, help='known tempo: only find the first beat')
    p.add_argument('--min', type=float, default=beats.MIN_BPM)
    p.add_argument('--max', type=float, default=beats.MAX_BPM)
    p.add_argument('--seconds', type=float, default=30, help='how much of the track to analyse (default 30)')
    a = p.parse_args(argv)
    found = beats.detect(a.track, a.bpm, a.seconds, a.min, a.max)
    if found.candidates:
        print('tempo candidates (onset strength on the beat / mean):')
        for score, b in found.candidates:
            print(f'  {b:6.1f} bpm  {score:.2f}')
        print('  (half or double the best is common: pick the one that matches the pulse you hear)')
    trim = found.first_frame(a.fps)
    print(f'{found.bpm:g} bpm: first beat at {found.first:.3f} s (strength {found.strength:.2f}x mean)')
    print(f'Grid(fps={a.fps}, bpm={found.bpm:g}, head_trim={trim})   # {trim} frames = {trim / a.fps:.3f} s, '
          f'{(trim / a.fps - found.first) * 1000:+.0f} ms from the beat')


if __name__ == '__main__':
    main()

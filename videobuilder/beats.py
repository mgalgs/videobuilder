"""A song's beats: its BPM and first beat, and a beat grid to cut a reel to.

    python -m videobuilder beats song.mp3 [--fps 30] [--bpm 120] [--seconds 30]

prints the best tempo candidates and, for the best (or the `--bpm` you give,
if you know it), the song's first beat, in seconds and in frames, and the
`beats` key for a film of clips' `timeline.json` (see films.md).

Estimates come from onsets (sudden rises in loudness), so they are good on
music with a clear pulse and unreliable on ambient pads: check by ear, and
by watching the cuts. Pure Python; ffmpeg decodes the file.

`BeatGrid` is the grid on a timeline: the frame of every beat, the nearest
beat to a frame (`snap`), and the beat n beats on from a frame (`step`).
Beat k is at `zero + round_half_up(k * frames_per_beat)`, as `vb.Grid.b`
rounds a beat, so a tempo that isn't a whole number of frames per beat stays
within half a frame of the music.
"""
import argparse
import array
import json
import math
import subprocess
from dataclasses import dataclass

from .timeline import round_half_up

RATE = 8000
HOP = RATE // 200  # 5 ms
MIN_BPM, MAX_BPM = 70.0, 180.0


def onsets(path, start=0.0, seconds=60.0):
    """Onset strength every `HOP` samples (5 ms) of `seconds` of `path`'s
    first sound stream from `start`: the rise in log energy, never negative."""
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(start), '-t', str(seconds), '-i', str(path),
                          '-map', '0:a:0', '-ac', '1', '-ar', str(RATE), '-f', 's16le', '-'],
                         capture_output=True)
    if raw.returncode:
        raise ValueError(f'{path}: ffmpeg cannot read its sound: {raw.stderr.decode(errors="replace")[-300:]}')
    s = array.array('h')
    s.frombytes(raw.stdout[:len(raw.stdout) // 2 * 2])
    energy = [math.log(1e-3 + sum(x * x for x in s[i:i + HOP]) / HOP) for i in range(0, len(s) - HOP, HOP)]
    if not energy:
        raise ValueError(f'{path}: no sound to find beats in')
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
    """(strength, phase in s) of the beats of `bpm` that best fit `onset`."""
    spb = 60 / bpm
    phases = [ms / 1000 for ms in range(0, int(spb * 1000), 5)]
    return max(((comb(onset, bpm, ph), ph) for ph in phases))


def candidates(onset, lo=MIN_BPM, hi=MAX_BPM, n=3):
    """The `n` best tempos in [lo, hi], [(strength / mean onset, bpm)], at
    least 2 bpm apart, best first."""
    mean = sum(onset) / len(onset) or 1
    scored = []
    bpm = lo
    while bpm <= hi:
        scored.append((best_phase(onset, bpm)[0], bpm))
        bpm += 0.5
    scored.sort(reverse=True)
    shown = []
    for score, b in scored:
        if all(abs(b - s) > 2 for _, s in shown):
            shown.append((score / mean, b))
        if len(shown) == n:
            break
    return shown


@dataclass(frozen=True)
class Detection:
    """A song's tempo and first beat, as found in its sound."""
    bpm: float
    first: float          # seconds from the file's start to its first beat
    strength: float       # onset strength on the beat / the mean: above ~2 is a clear pulse
    candidates: tuple = ()  # ((strength, bpm), ...): the best tempos, best first

    def first_frame(self, fps):
        """The frame of the first beat, counted from the file's start at `fps`."""
        return round(self.first * fps)


def detect(path, bpm=None, seconds=30.0, lo=MIN_BPM, hi=MAX_BPM):
    """The `Detection` of `path`'s first `seconds`: its tempo (or `bpm`, when
    you know it) and the first beat at that tempo."""
    onset = onsets(path, seconds=seconds)
    mean = sum(onset) / len(onset) or 1
    cands = () if bpm else tuple(candidates(onset, lo, hi))
    if not bpm:
        bpm = cands[0][1]
    score, first = best_phase(onset, bpm)
    return Detection(float(bpm), first, score / mean, cands)


@dataclass(frozen=True)
class BeatGrid:
    """The beats of a song on a timeline, in frames at `fps`. Beat k (k >= 0)
    is at `frame(k)`; beat 0, the song's first beat, at `zero`. Only beats
    from frame `lo` to `hi` (inclusive; None: no end) are on the grid: the
    span the song plays. Every `bar`-th beat from beat 0 is a downbeat."""
    fps: int
    bpm: float
    zero: int = 0
    lo: int = 0
    hi: int | None = None
    bar: int = 4

    @property
    def frames_per_beat(self):
        return self.fps * 60 / self.bpm

    def frame(self, k):
        """The frame of beat `k`."""
        return self.zero + round_half_up(k * self.frames_per_beat)

    def _first(self):
        """The index of the first beat on the grid."""
        k = max(0, math.ceil((self.lo - self.zero) / self.frames_per_beat) - 1)
        while self.frame(k) < self.lo:
            k += 1
        return k

    def _last(self):
        """The index of the last beat on the grid (None: no end), less than
        `_first()` when the grid holds no beat at all."""
        if self.hi is None:
            return None
        k = max(-1, math.floor((self.hi - self.zero) / self.frames_per_beat) + 1)
        while k >= 0 and self.frame(k) > self.hi:
            k -= 1
        return k

    def index(self, frame):
        """The index of the beat nearest `frame` (the later of two as near),
        or None when the grid has no beats."""
        first, last = self._first(), self._last()
        if last is not None and last < first:
            return None
        k = max(first, math.floor((frame - self.zero) / self.frames_per_beat))
        if last is not None:
            k = min(k, last)
        best = None
        for j in (k - 1, k, k + 1):
            if j < first or (last is not None and j > last):
                continue
            if best is None or abs(self.frame(j) - frame) <= abs(self.frame(best) - frame):
                best = j
        return best

    def snap(self, frame):
        """The frame of the beat nearest `frame` (`frame` itself when the
        grid has no beats)."""
        k = self.index(frame)
        return frame if k is None else self.frame(k)

    def off(self, frame):
        """Frames from the nearest beat to `frame`: 0 on a beat, negative before it."""
        return frame - self.snap(frame)

    def on_beat(self, frame):
        return self.off(frame) == 0

    def step(self, frame, n=1):
        """The frame `n` beats on from `frame` (back, for n < 0): from a frame
        on a beat, `n` beats away; from one between beats, the next (or
        previous) beat counts as the first step. Stays on the grid: at its
        ends, the end beat."""
        k = self.index(frame)
        if k is None or n == 0:
            return frame if k is None else self.frame(k)
        at = self.frame(k)
        if n > 0 and at > frame or n < 0 and at < frame:
            n -= 1 if n > 0 else -1
        k += n
        first, last = self._first(), self._last()
        k = max(first, k if last is None else min(last, k))
        return self.frame(k)

    def frames(self, lo=None, hi=None):
        """Frames of every beat from `lo` to `hi` (inclusive; default the grid's
        span; with no end, `hi` is needed)."""
        lo = self.lo if lo is None else max(lo, self.lo)
        hi = self.hi if hi is None else hi if self.hi is None else min(hi, self.hi)
        if hi is None:
            raise ValueError('a grid with no end needs hi')
        out, k = [], self._first()
        while self.frame(k) <= hi:
            if self.frame(k) >= lo:
                out.append(self.frame(k))
            k += 1
        return out

    def is_downbeat(self, frame):
        k = self.index(frame)
        return k is not None and self.frame(k) == frame and k % self.bar == 0

    def describe(self, frame):
        """`beat 17` (1-based, as counted), or `bar 5` on a downbeat."""
        k = self.index(frame)
        if k is None:
            return 'no beat'
        return f'bar {k // self.bar + 1}' if k % self.bar == 0 else f'beat {k + 1}'


def main(argv=None):
    p = argparse.ArgumentParser(prog='videobuilder beats', description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('song')
    p.add_argument('--fps', type=int, default=30)
    p.add_argument('--bpm', type=float, help='known tempo: only find the first beat')
    p.add_argument('--min', type=float, default=MIN_BPM, help=f'slowest tempo to try (default {MIN_BPM:g})')
    p.add_argument('--max', type=float, default=MAX_BPM, help=f'fastest tempo to try (default {MAX_BPM:g})')
    p.add_argument('--seconds', type=float, default=30, help='how much of the song to analyse (default 30)')
    a = p.parse_args(argv)
    try:
        found = detect(a.song, a.bpm, a.seconds, a.min, a.max)
    except ValueError as e:
        raise SystemExit(str(e)) from None
    if found.candidates:
        print('tempo candidates (onset strength on the beat / mean):')
        for score, b in found.candidates:
            print(f'  {b:6.1f} bpm  {score:.2f}')
        print('  (half or double the best is common: pick the one that matches the pulse you hear)')
    first = found.first_frame(a.fps)
    grid = BeatGrid(a.fps, found.bpm, first)
    print(f'{found.bpm:g} bpm: first beat at {found.first:.3f} s (strength {found.strength:.2f}x mean)')
    print(f'at {a.fps} fps: {grid.frames_per_beat:.3f} frames a beat, {grid.frames_per_beat * grid.bar:.3f} a bar; '
          f'first beat at frame {first} of the file')
    print('beats (frames of the file): ' + ', '.join(str(grid.frame(k)) for k in range(9)) + ', ...')
    print('timeline.json, for the song on Audio 1 as its item 1:')
    print('  "beats": ' + json.dumps({'lane': 1, 'item': 1, 'bpm': found.bpm, 'first': first}))
    print(f'Grid(fps={a.fps}, bpm={found.bpm:g}, head_trim={first})   # for a single film\'s vb.Grid')


if __name__ == '__main__':
    main()

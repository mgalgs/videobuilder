"""Swell: the music builds, quiet and thin at first, louder and fuller with
every beat, into one peak. Notes come closer together, more of them sound at
once, each a little louder than the last, over an optional riser bed that
ends on the peak; `swell_level` gives the same curve for the picture."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

ARPEGGIO = ('C4', 'E4', 'G4', 'C5', 'E5', 'G5', 'A5', 'C6')   # a climbing C major line
PEAK_CHORD = ('C4', 'G4', 'C5', 'E5', 'C6')
_PITCH = ('C', 'Cs', 'D', 'Ds', 'E', 'F', 'Fs', 'G', 'Gs', 'A', 'As', 'B')


def _midi(note):
    name = vb.sfx.note_name(note)
    return 12 * (int(name[-1]) + 1) + _PITCH.index(name[:-1])


def playable(effect, note):
    """The note of tuned `effect` to play for `note`: itself if it has it,
    else the same pitch moved by whole octaves into its range, else its
    nearest note."""
    have = {_midi(n): n for n in effect.notes}
    want = _midi(note)
    lo, hi = min(have), max(have)
    while want < lo and want + 12 <= hi:
        want += 12
    while want > hi and want - 12 >= lo:
        want -= 12
    return have.get(want) or have[min(have, key=lambda m: abs(m - want))]


def swell_level(frame, start, peak):
    """How far into the swell frame `frame` is, as loudness 0 -> 1: a slow
    ease-in from `start` that is steepest just before `peak`, then 1."""
    p = vb.clamp01((frame - start) / (peak - start))
    return p * p


def swell_schedule(start, peak, notes=ARPEGGIO, peak_chord=PEAK_CHORD, voices=3, floor_db=-26.0, top_db=-4.0,
                   accel=0.6):
    """The swell's notes as `(frame, notes, gain_db)` steps: one step per
    entry of `notes` from `start`, the gaps shrinking (`accel` < 1 speeds up
    towards the peak), each step stacking up to `voices` notes of the line
    as it gets louder, from `floor_db` up towards `top_db`; then
    `peak_chord` together at `top_db` on `peak`."""
    steps = []
    for i, note in enumerate(notes):
        p = (i / len(notes)) ** accel
        frame = round(start + p * (peak - start))
        level = swell_level(frame, start, peak)
        stack = 1 + round(level * (voices - 1))
        steps.append((frame, tuple(notes[max(0, i - stack + 1):i + 1]),
                      floor_db + (top_db - floor_db) * math.sqrt(level) - 3))
    steps.append((peak, tuple(peak_chord), top_db))
    return steps


def music_swell(start, peak, sound='pluck/kalimba', bed='riser/swell', bed_db=-16.0, fps=30, **kw):
    """A swell from frame `start` that lands on frame `peak`, as a tuple of
    `vb.sfx` sounds for a film's `sounds`: tuned `sound` notes laid out by
    `swell_schedule` (`kw` goes there; a note `sound` lacks is played as
    `playable` picks), plus the riser `bed` (None for none)
    at `bed_db`: its take nearest the swell's length, whole, its loudest
    moment on `peak`."""
    effect = vb.sfx.get(sound)
    out = [effect.sound(frame, fps, 'onset', gain, note=playable(effect, n))
           for frame, chord, gain in swell_schedule(start, peak, **kw) for n in chord]
    if bed:
        take = vb.sfx.get(bed).nearest_length((peak - start) / fps)   # whole, so its peak stays in
        out.append(take.sound(peak, fps, gain_db=bed_db))
    return tuple(out)


# ---- demo ----
START, PEAK = 6, 69
BARS = 23
# A warm tuned pluck over a riser where the pack has them; a pack without them still gets a swell of dings.
SOUNDS = ('pluck/kalimba', 'pro_notify/ding_2045')
BED = 'riser/swell'


def _in_pack(id):
    try:
        vb.sfx.get(id)
    except ValueError:
        return False
    return True


def demo_sounds():
    sound = next(s for s in SOUNDS if _in_pack(s))
    return music_swell(START, PEAK, sound=sound, bed=BED if _in_pack(BED) else None)


def _hit(n, frames):
    """A 0 -> 1 pulse that jumps on each frame in `frames` and decays after."""
    since = [n - f for f in frames if n >= f]
    return math.exp(-min(since) / 4) if since else 0.0


def draw(n, cv):
    level = swell_level(n, START, PEAK)
    hits = [f for f, _, _ in swell_schedule(START, PEAK)]
    pulse = _hit(n, hits)
    after = max(0, n - PEAK)
    bloom = math.exp(-after / 8) if n >= PEAK else 0.0
    cx, base = demo.W / 2, demo.H * 0.6
    # The bars: more of them join from the middle out as the swell fills, and they grow taller.
    reach = 1.5 + level * (BARS / 2)
    gap = 28
    for i in range(BARS):
        off = i - BARS // 2
        on = vb.clamp01(reach - abs(off))
        if on <= 0:
            continue
        wave = 0.55 + 0.45 * abs(math.sin(n * 0.37 + i * 1.7) * math.cos(n * 0.21 + i * 0.6))
        h = 10 + on * (16 + 170 * level * wave) * (1 - 0.15 * (1 - bloom) * (n >= PEAK) + 0.15 * pulse)
        color = demo.INK if bloom > 0.5 and abs(off) < 2 else demo.ACCENT
        cv.rect(cx + off * gap - 9, base - h, 18, h, color, radius=6, alpha=0.35 + 0.65 * on)
    cv.mark('bars', cx - BARS / 2 * gap, base - 230, BARS * gap, 230)
    # The crescendo hairpin underneath, opening as it goes, pp to ff.
    x0, x1, y = demo.W * 0.26, demo.W * 0.74, demo.H * 0.8
    tip = x0 + (x1 - x0) * vb.clamp01((n - START) / (PEAK - START))
    spread = 18 * (tip - x0) / (x1 - x0)
    cv.line(x0, y, tip, y - spread, demo.MUTED, width=3)
    cv.line(x0, y, tip, y + spread, demo.MUTED, width=3)
    f = demo.font(26, 800)
    demo.word(cv, 'pp', x0 - 40, y, font=f, color=demo.MUTED)
    demo.word(cv, 'ff', x1 + 40, y, font=f, color=demo.INK if n >= PEAK else demo.MUTED,
              alpha=0.35 + 0.65 * level)


CAPABILITY = Capability(
    id='music-swell',
    name='Swell',
    family='sound',
    group='Music',
    aliases=('music swell', 'crescendo', 'build'),
    definition='The music climbs from soft and sparse to loud and full, more notes stacking up '
               'as it rises into a single peak.',
    phrasings=('let the music build up to the big moment',
               'bring the score in quietly and have it grow until it hits the reveal',
               'a crescendo in the music leading into the title'),
    related=('riser', 'like-heart-burst', 'scale-pulse', 'sound-bridge', 'liquid-fill-level', 'wobble'),
    api=('videobuilder.capabilities.sound.music_swell.music_swell',
         'videobuilder.capabilities.sound.music_swell.swell_schedule',
         'videobuilder.capabilities.sound.music_swell.swell_level'),
    demo=lambda: demo.film(draw, sounds=demo_sounds()),
)

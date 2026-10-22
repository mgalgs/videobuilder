"""Equalizer Bars: a row of vertical bars that jump up and down as if they were
following the levels of a piece of music, each with a small cap that falls
back slowly after a peak."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def eq_levels(t, count=24, seed=0, bpm=120, energy=1.0):
    """Fake but musical bar heights at time `t` seconds: `count` values in
    0..1, low bars (the bass) on the left pulsing on the beat, high bars on
    the right busier and quieter. The same `t` and `seed` give the same
    heights, so any frame renders alone. `energy` scales the lot (fade a
    meter in or out with it). For real audio, pass your own levels to
    `draw_eq_bars` instead."""
    beat = (t * bpm / 60) % 1
    kick = math.exp(-beat * 6)
    out = []
    for i in range(count):
        f = i / max(1, count - 1)            # 0 = bass, 1 = treble
        s = seed * 7.31 + i * 1.7
        wobble = sum(math.sin(t * w + s * k) for w, k in ((5.3 + 9 * f, 1.0), (11.7 + 13 * f, 2.3),
                                                          (2.1, 3.7))) / 3
        v = 0.5 + 0.35 * wobble + 0.45 * kick * (1 - f) ** 1.5 - 0.22 * f
        out.append(vb.clamp01(v * energy))
    return out


def eq_peaks(t, fps=30, count=24, seed=0, hold=0.25, fall=0.9, **kw):
    """The peak cap over each bar at time `t`: the highest level of the last
    `hold` seconds, then dropping `fall` (of the full height) per second.
    Computed from `eq_levels` alone, so it needs no state between frames;
    `kw` goes to `eq_levels`."""
    peaks = [0.0] * count
    back = int((hold + 1 / fall) * fps)
    for k in range(back + 1):
        tk = t - k / fps
        if tk < 0:
            break
        drop = max(0.0, k / fps - hold) * fall
        for i, v in enumerate(eq_levels(tk, count, seed, **kw)):
            peaks[i] = max(peaks[i], v - drop)
    return peaks


def draw_eq_bars(cv, x, y, w, h, levels, peaks=None, color=demo.TEAL, hot=demo.ACCENT, gap=0.35,
                 segments=0, track=demo.LINE, alpha=1.0):
    """Draw an equalizer in the box (x, y, w, h), one bar per value of
    `levels` (0..1, rising from the box's bottom). Bars shade from `color`
    to `hot` as they get taller. `gap` is the space between bars as a
    fraction of a bar's width; `segments` > 0 splits each bar into that many
    LED blocks, lit up to its level; `track` draws the unlit part (None for
    none); `peaks`, if given, draws a thin cap at each value."""
    n = len(levels)
    slot = w / n
    bw = slot / (1 + gap)
    for i, v in enumerate(levels):
        bx = x + i * slot + (slot - bw) / 2
        if segments:
            seg = h / segments
            sh = seg * 0.72
            for s in range(segments):
                sy = y + h - (s + 1) * seg + (seg - sh) / 2
                lit = (s + 0.5) / segments <= v
                if lit:
                    cv.rect(bx, sy, bw, sh, demo.kit.mix(color, hot, s / max(1, segments - 1)),
                            radius=2, alpha=alpha)
                elif track:
                    cv.rect(bx, sy, bw, sh, track, radius=2, alpha=alpha)
        else:
            if track:
                cv.rect(bx, y, bw, h, track, radius=bw / 2, alpha=alpha * 0.6)
            bh = max(bw, v * h)
            cv.rect(bx, y + h - bh, bw, bh, demo.kit.mix(color, hot, v ** 2), radius=bw / 2, alpha=alpha)
        if peaks is not None:
            py = y + h - peaks[i] * h
            cv.rect(bx, py - 6, bw, 4, demo.INK, radius=2, alpha=alpha * 0.9)
    cv.mark('equalizer', x, y, w, h)


def draw(n, cv):
    t = n / demo.FPS
    energy = demo.phase(n, 0.0, 0.4) * (1 - 0.85 * demo.phase(n, 2.6, 3.0))
    count, bw, bh = 24, 720, 300
    x, y = (demo.W - bw) / 2, (demo.H - bh) / 2 + 20
    levels = eq_levels(t, count, seed=3, energy=energy)
    peaks = eq_peaks(t, demo.FPS, count, seed=3)
    draw_eq_bars(cv, x, y, bw, bh, levels, peaks=[min(p, 1) * energy for p in peaks], segments=16)
    demo.floor(cv, y + bh + 14, demo.MUTED)


CAPABILITY = Capability(
    id='audio-waveform-bars',
    name='Equalizer bars',
    family='ui',
    group='Feedback & status',
    aliases=('audio visualizer bars', 'spectrum bars', 'EQ meter', 'sound bars', 'music visualizer'),
    definition='A row of vertical bars that leap and drop to the beat, each one tracking how loud '
               'its slice of the sound is, like the meter on a stereo.',
    phrasings=('bars bouncing to the music like a graphic equalizer',
               'a little spectrum meter dancing while the track plays',
               'show the audio levels as jumping bars'),
    related=('copper-bars', 'refresh-bar', 'sound-reactive-radial-shape', 'vhs-tracking-bar',
             'grid-wave-loader', 'bar-grow'),
    api=('videobuilder.capabilities.ui.audio_waveform_bars.draw_eq_bars',
         'videobuilder.capabilities.ui.audio_waveform_bars.eq_levels',
         'videobuilder.capabilities.ui.audio_waveform_bars.eq_peaks'),
    demo=lambda: demo.film(draw),
)
